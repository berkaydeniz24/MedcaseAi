# routers/dialogue_router.py
import json
import logging
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Database Imports
from services.database import get_db
from services.db_service import DBService
from services import models

# Agents
from dialogue.dialogue_agent import DialogueAgent
from case_selector.selector_agent import selector_agent
from tutor.tutor_agent import tutor_agent
from tutor.schemas import TutorInput, CaseContext, StepContext, UserContext
from mcq.mcq_agent import mcq_agent

logger = logging.getLogger(__name__)

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
    """
    # 1) Case seç
    case_data = selector_agent.select_random_case(db)
    if not case_data or ("error" in case_data):
        raise HTTPException(status_code=404, detail=case_data.get("error", "Case not found"))

    # 2) MCQ üret
    try:
        mcq_full = mcq_agent.generate_mcq(case_data)
    except Exception as e:
        logger.error("start_simulation: MCQ generation failed for case_id=%s: %s", case_data.get("id"), e)
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    # 3) SESSION OLUŞTUR VE DB'YE YAZ (tek kaynak: SQLite — RAM fallback yok)
    session_id = str(uuid.uuid4())

    new_db_session = models.ChatSession(
        session_id=session_id,
        case_id=case_data.get("id"),
        mcq_data=json.dumps(mcq_full, ensure_ascii=False)
    )
    db.add(new_db_session)

    # Vaka durumunu güncelle
    dbs = DBService(db)
    dbs.update_case_status(case_data.get("id"), "in_progress")
    db.commit()
    logger.info("start_simulation: created session_id=%s for case_id=%s", session_id, case_data.get("id"))

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
    Ajan stateless'tır, ancak geçmiş (history) parametre olarak verilir.
    """
    # 1. Vakayı kontrol et
    case = selector_agent.get_case_by_id(db, case_id)
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

    try:
        # 4. GEÇMİŞİ ÇEK (Bağlamı korumak için)
        history_objs = dbs.get_chat_history(current_session_id)
        chat_history = [{"role": h.role, "content": h.content} for h in history_objs]

        # 5. Ajan cevabı üret (Geçmiş parametre olarak gidiyor)
        response = dialogue_agent.generate_response(
            user_input=req.message, # Ham mesaj yeterli, prompt içinde birleşecek
            case_data=case,
            mode=mode,
            language=language,
            user_level=user_level,
            chat_history=chat_history # 👈 İşte sihir burada
        )

        # 6. Cevabı Temizle
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

        # 7. Loglama
        dbs.add_message(current_session_id, "user", req.message)
        dbs.add_message(current_session_id, "ai", ai_text)

        return {
            "answer": ai_text,
            "followups": ai_followups,
            "session_id": current_session_id,
            "status": "success"
        }

    except Exception as e:
        logger.error("chat_with_agent: failed for session_id=%s: %s", current_session_id, e)
        raise HTTPException(status_code=500, detail=f"Internal Error: {str(e)}")


# ---------- 3) ANSWER: evaluate + tutor feedback (DB READ) ----------
@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest, db: Session = Depends(get_db)):
    """
    Cevabı kontrol eder.
    RAM yerine VERİTABANINDAN okuma yapar.
    """
    dbs = DBService(db)

    # 1. Session'ı DB'den çek
    db_session = db.query(models.ChatSession).filter_by(session_id=session_id).first()
    
    if not db_session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")

    case_id = db_session.case_id
    
    # 2. MCQ Verisini DB'den Oku (tek kaynak: SQLite ChatSession.mcq_data)
    mcq_full = {}
    if db_session.mcq_data:
        try:
            mcq_full = json.loads(db_session.mcq_data)
        except Exception as e:
            logger.error("submit_answer: MCQ data parse failed for session_id=%s: %s", session_id, e)

    # 3. Case verisini çek
    case = selector_agent.get_case_by_id(db, case_id)
    
    # 4. Doğru Cevabı Belirle
    correct_index = int(mcq_full.get("correctIndex", 0)) 
    question_text = mcq_full.get("question", "Soru verisi yüklenemedi.")
    options = mcq_full.get("options", [])
    
    if not options:
        options = ["A", "B", "C", "D"] 

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
        logger.error("submit_answer: TutorAgent failed for session_id=%s: %s", session_id, e)
        msg = "Tebrikler!" if is_correct else "Yanlış cevap."
        tutor_out = {"answer": f"{msg}"}

    return {
        "session_id": session_id,
        "case_id": case_id,
        "selectedIndex": selected_index,
        "correctIndex": correct_index,
        "isCorrect": is_correct,
        "tutor": tutor_out 
    }


# ---------- 4) SOHBET GEÇMİŞİNİ GETİR ----------
@router.get("/history/{session_id}")
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """
    Belirli bir oturuma ait tüm mesajları getirir.
    """
    messages = db.query(models.ChatMessage)\
        .filter(models.ChatMessage.session_id == session_id)\
        .order_by(desc(models.ChatMessage.timestamp))\
        .all()
    
    return messages