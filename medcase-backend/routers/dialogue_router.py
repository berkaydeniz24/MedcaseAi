# routers/dialogue_router.py
import json
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Database Imports
from services.database import get_db
from services.db_service import DBService
from services import models

# Agents
from dialogue.dialogue_agent import DialogueAgent
from case_selector.selector_agent import selector_agent
from tutor.tutor_agent import tutor_agent
from tutor.schemas import TutorInput, CaseContext, StepContext, UserContext

# Services
from services.session_store import session_store
from services.mcq_generator import mcq_generator

router = APIRouter()
dialogue_agent = DialogueAgent()

# ---------- Request Models ----------
class DialogueRequest(BaseModel):
    message: str
    mode: Optional[str] = "hint"          # hint | explain | teach
    userLevel: Optional[str] = "beginner" # beginner | intermediate | advanced
    language: Optional[str] = "tr"        # tr | en
    session_id: Optional[str] = None      # Frontend'den gelen session_id

class AnswerRequest(BaseModel):
    selectedIndex: int = Field(ge=0)
    mode: Optional[str] = "explain"
    userLevel: Optional[str] = "beginner"
    language: Optional[str] = "en"

# ---------- 1) START: case + session + mcq (DB Persistence) ----------
@router.get("/start")
def start_simulation(db: Session = Depends(get_db)):
    """
    Yeni bir vaka simülasyonu başlatır.
    MCQ verisini JSON olarak VERİTABANINA kaydeder.
    Böylece sunucu restart olsa bile cevap anahtarı kaybolmaz.
    """
    # 1) Case seç
    case_data = selector_agent.select_random_case()
    if not case_data or ("error" in case_data):
        raise HTTPException(status_code=404, detail=case_data.get("error", "Case not found"))

    # 2) MCQ üret (Karıştırılmış şıklar burada gelir)
    try:
        mcq_full = mcq_generator.generate_mcq(case_data)
    except Exception as e:
        print(f"MCQ Error: {e}")
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    # 3) SESSION OLUŞTUR VE DB'YE YAZ
    session_id = str(uuid.uuid4())

    # A) Veritabanına Kaydet (En Güvenli Yöntem)
    # mcq_full sözlüğünü JSON string'e çevirip saklıyoruz.
    # models.py'de 'mcq_data' sütunu eklediğini varsayıyoruz.
    new_db_session = models.ChatSession(
        session_id=session_id, 
        case_id=case_data.get("id"),
        mcq_data=json.dumps(mcq_full, ensure_ascii=False) # <--- KRİTİK NOKTA: Veriyi diske yazıyoruz
    )
    db.add(new_db_session)
    
    # Vaka durumunu güncelle (in_progress)
    dbs = DBService(db)
    dbs.update_case_status(case_data.get("id"), "in_progress")
    db.commit()

    # B) RAM'e de atalım (Hız için, opsiyonel ama dursun)
    session_store._sessions[session_id] = type("SessionData", (), {
        "session_id": session_id,
        "case_id": case_data.get("id"),
        "mcq": mcq_full,
        "created_at": 0
    })

    # 4) Frontend'e PUBLIC MCQ dön
    mcq_public = {
        "question": mcq_full["question"],
        "options": mcq_full["options"],
    }

    return {
        "session_id": session_id,
        "case": case_data,
        "mcq": mcq_public
    }


# ---------- 2) CHAT: mode-based guidance ----------
@router.post("/{case_id}/chat")
async def chat_with_agent(case_id: str, req: DialogueRequest, db: Session = Depends(get_db)):
    """
    Kullanıcı ile sohbet eder.
    """
    # 1. Vakayı kontrol et
    case = selector_agent.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    dbs = DBService(db)

    # 2. Session Yönetimi
    current_session_id = req.session_id
    if current_session_id:
        existing_session = db.query(models.ChatSession).filter_by(session_id=current_session_id).first()
        if not existing_session:
            current_session_id = dbs.create_session(case_id)
    else:
        current_session_id = dbs.create_session(case_id)

    # 3. Parametreleri hazırla
    mode = req.mode if req.mode in ["hint", "explain", "teach"] else "hint"
    language = req.language if req.language in ["tr", "en"] else "tr"
    user_level = req.userLevel or "beginner"

    user_input_with_meta = (
        f"[LANG={language}][USER_LEVEL={user_level}][MODE={mode}]\n"
        f"{req.message}"
    )

    try:
        # 4. Ajan cevabı üret
        response = dialogue_agent.generate_response(
            user_input=user_input_with_meta,
            case_data=case,
            mode=mode
        )

        # 5. Cevabı Temizle
        ai_text = ""
        ai_followups = []

        if hasattr(response, "answer"):
            ai_text = response.answer
            if hasattr(response, "followups"):
                ai_followups = response.followups
        elif isinstance(response, dict):
            ai_text = response.get("answer", "")
            ai_followups = response.get("followups", [])
        else:
            ai_text = str(response)

        # 6. Loglama
        dbs.add_message(current_session_id, "user", req.message)
        dbs.add_message(current_session_id, "ai", ai_text)

        return {
            "answer": ai_text,
            "followups": ai_followups,
            "session_id": current_session_id,
            "status": "success"
        }

    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")


# ---------- 3) ANSWER: evaluate + tutor feedback (DB READ) ----------
@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
    """
    Cevabı kontrol eder.
    RAM yerine VERİTABANINDAN okuma yapar. Böylece cevaplar ASLA kaybolmaz.
    """
    dbs = DBService(db)

    # 1. Session'ı DB'den çek
    db_session = db.query(models.ChatSession).filter_by(session_id=session_id).first()
    
    if not db_session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı veya süresi dolmuş.")

    case_id = db_session.case_id
    
    # 2. MCQ Verisini DB'den Oku (JSON parse et)
    mcq_full = {}
    if db_session.mcq_data:
        try:
            mcq_full = json.loads(db_session.mcq_data)
        except Exception as e:
            print(f"MCQ Data Parse Error: {e}")
    
    # Eğer DB'de veri yoksa (eski kayıtlar vs), RAM'e bak (Yedek)
    if not mcq_full:
        ram_session = session_store.get(session_id)
        if ram_session and ram_session.mcq:
            mcq_full = ram_session.mcq

    # 3. Case verisini çek
    case = selector_agent.get_case_by_id(case_id)
    
    # 4. Doğru Cevabı ve Soruyu Belirle
    # ARTIK FALLBACK YOK. Veritabanında ne yazıyorsa o geçerli.
    # mcq_full boş gelirse hata verebiliriz veya loglarız ama "A" demeyeceğiz.
    
    correct_index = int(mcq_full.get("correctIndex", 0)) # Varsayılan 0 ama artık DB'den doğru gelecek
    question_text = mcq_full.get("question", "Soru verisi yüklenemedi.")
    options = mcq_full.get("options", [])
    
    # Eğer seçenekler DB'den gelmediyse (çok nadir durum), case içinden uydurma
    if not options:
        options = ["A", "B", "C", "D"] # Gösterimlik

    selected_index = int(req.selectedIndex)
    is_correct = (selected_index == correct_index)

    # --- DB İŞLEMLERİ ---
    dbs.update_stats(is_correct)
    new_status = "solved" if is_correct else "in_progress"
    dbs.update_case_status(case_id, new_status)
    # ---------------------

    # Tutor Agent Çağrısı
    try:
        step_ctx = StepContext(
            question=question_text,
            options=options,
            correct=correct_index
        )
        case_ctx = CaseContext(
            id=case.get("id", "") if case else "",
            title=case.get("title", "") if case else "",
            summary=case.get("narrative", "")[:180] if case else "",
            narrative=case.get("narrative", "") if case else "",
            step=step_ctx
        )
        user_ctx = UserContext(selectedIndex=selected_index, ask="")

        tutor_inp = TutorInput(
            case=case_ctx,
            user=user_ctx,
            mode=req.mode,
            language=req.language,
            userLevel=req.userLevel or "beginner"
        )

        tutor_out = tutor_agent.run(tutor_inp)
    except Exception as e:
        print(f"Tutor Error: {e}")
        msg = "Tebrikler, doğru cevap!" if is_correct else "Maalesef yanlış cevap."
        tutor_out = {"answer": f"{msg}"}

    return {
        "session_id": session_id,
        "case_id": case_id,
        "selectedIndex": selected_index,
        "correctIndex": correct_index,
        "isCorrect": is_correct,
        "tutor": tutor_out 
    }