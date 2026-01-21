# routers/dialogue_router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid

# Database Imports
from sqlalchemy.orm import Session
from services.database import get_db
from services.db_service import DBService

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
    session_id: Optional[str] = None      # <--- EKLENDİ (Sohbet takibi için)

class AnswerRequest(BaseModel):
    selectedIndex: int = Field(ge=0)
    mode: Optional[str] = "explain"       # hint | explain | teach
    userLevel: Optional[str] = "beginner" # beginner | intermediate | advanced
    language: Optional[str] = "en"        # tr | en

# ---------- 1) START: case + session + mcq ----------
@router.get("/start")
def start_simulation(db: Session = Depends(get_db)):
    """
    Yeni bir vaka simülasyonu başlatır.
    Hem RAM'e (MCQ verisi için) hem de DB'ye (Loglar için) kayıt açar.
    """
    # 1) Case seç
    case_data = selector_agent.select_random_case()
    if not case_data or ("error" in case_data):
        raise HTTPException(status_code=404, detail=case_data.get("error", "Case not found"))

    # 2) MCQ üret
    try:
        mcq_full = mcq_generator.generate_mcq(case_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    # 3) ORTAK SESSION ID OLUŞTUR
    session_id = str(uuid.uuid4())

    # A) In-Memory Store'a kaydet (MCQ verisi burada duracak)
    session_store._sessions[session_id] = type("SessionData", (), {
        "session_id": session_id,
        "case_id": case_data.get("id"),
        "mcq": mcq_full,
        "created_at": 0 
    })

    # B) Veritabanına Kaydet (Geçmiş ve İstatistik için)
    # Session ID ile veritabanında oturum açıyoruz
    from services import models
    new_db_session = models.ChatSession(session_id=session_id, case_id=case_data.get("id"))
    db.add(new_db_session)
    
    # Vaka durumunu güncelle (in_progress)
    dbs = DBService(db)
    dbs.update_case_status(case_data.get("id"), "in_progress")
    db.commit()

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
    Kullanıcı ile sohbet eder ve mesajları veritabanına kaydeder.
    """
    case = selector_agent.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    dbs = DBService(db)

    # Parametreleri hazırla
    mode = req.mode if req.mode in ["hint", "explain", "teach"] else "hint"
    language = req.language if req.language in ["tr", "en"] else "tr"
    user_level = req.userLevel or "beginner"

    user_input_with_meta = (
        f"[LANG={language}][USER_LEVEL={user_level}][MODE={mode}]\n"
        f"{req.message}"
    )

    try:
        # Ajan cevabı üret
        response = dialogue_agent.generate_response(
            user_input=user_input_with_meta,
            case_data=case,
            mode=mode
        )
        
        # --- VERİTABANI KAYDI (ARTIK AKTİF) ---
        # Frontend session_id yollamazsa 'general_log' altına kaydederiz.
        sid = req.session_id if req.session_id else "general_log"
        
        # Loglama
        dbs.add_message(sid, "user", req.message)
        dbs.add_message(sid, "ai", str(response.get("answer", "")))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 3) ANSWER: evaluate + tutor feedback ----------
@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
    """
    Cevabı kontrol eder, İSTATİSTİKLERİ GÜNCELLER ve sonucu döner.
    """
    # 1) RAM'den MCQ verisini çek
    session_data = session_store.get(session_id)
    
    if not session_data:
         raise HTTPException(status_code=404, detail="Session expired or not found. Please restart the case.")

    dbs = DBService(db)
    
    # Case verisini çek
    case = selector_agent.get_case_by_id(session_data.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Doğru/Yanlış Kontrolü
    mcq_full: Dict[str, Any] = session_data.mcq
    correct_index = int(mcq_full["correctIndex"])
    selected_index = int(req.selectedIndex)

    if selected_index < 0 or selected_index >= len(mcq_full["options"]):
        raise HTTPException(status_code=400, detail="selectedIndex out of range")

    is_correct = (selected_index == correct_index)

    # --- DB İŞLEMLERİ (İSTATİSTİK & DURUM) ---
    # 1. Kullanıcı istatistiklerini güncelle
    dbs.update_stats(is_correct)

    # 2. Vaka durumunu güncelle
    new_status = "solved" if is_correct else "in_progress"
    dbs.update_case_status(session_data.case_id, new_status)
    # -----------------------------------------

    # Tutor Agent Çağrısı
    step_ctx = StepContext(
        question=mcq_full["question"],
        options=mcq_full["options"],
        correct=correct_index
    )

    case_ctx = CaseContext(
        id=case.get("id", ""),
        title=case.get("title", ""),
        summary=case.get("narrative", "")[:180],
        narrative=case.get("narrative", ""),
        step=step_ctx
    )

    user_ctx = UserContext(selectedIndex=selected_index, ask="")

    tutor_inp = TutorInput(
        case=case_ctx,
        user=user_ctx,
        mode=req.mode if req.mode in ["hint", "explain", "teach"] else "explain",
        language=req.language if req.language in ["tr", "en"] else "en",
        userLevel=req.userLevel or "beginner"
    )

    tutor_out = tutor_agent.run(tutor_inp)

    return {
        "session_id": session_id,
        "case_id": session_data.case_id,
        "selectedIndex": selected_index,
        "correctIndex": correct_index,
        "isCorrect": is_correct,
        "tutor": tutor_out
    }