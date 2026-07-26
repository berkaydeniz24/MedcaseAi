# routers/dialogue_router.py
import json
import logging
import uuid
from datetime import datetime, timezone
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
from mcq.mcq_agent import is_fallback_mcq, mcq_agent

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
    # ge=0/le=3 — 4 seçenekli bir MCQ'da geçerli tek aralık. Önceden yalnızca
    # ge=0 vardı; hiçbir üst sınır yoktu (bkz. docs/architecture.md §6, madde 11).
    selectedIndex: int = Field(ge=0, le=3)
    mode: Optional[str] = "explain"
    userLevel: Optional[str] = "beginner"
    language: Optional[str] = "en"

# ---------- 1) START: case + session + mcq (DB Persistence) ----------
@router.get("/start")
def start_simulation(specialty: Optional[str] = None, case_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Yeni bir vaka simülasyonu başlatır.
    MCQ verisini JSON olarak VERİTABANINA kaydeder.
    `case_id` verilirse (ör. "Günün Vakası" kartından), o spesifik vaka
    kullanılır — specialty filtresi bu durumda yok sayılır. Aksi halde
    `specialty` verilirse (ör. "Cardiology") yalnızca o branştan rastgele
    bir vaka seçilir; ikisi de verilmezse tüm branşlardan rastgele seçilir.
    """
    # 1) Case seç
    if case_id:
        case_data = selector_agent.get_case_by_id(db, case_id)
        if not case_data:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    else:
        specialty_filter = specialty if specialty and specialty != "All" else None
        case_data = selector_agent.select_random_case(db, specialty=specialty_filter)
        if not case_data or ("error" in case_data):
            raise HTTPException(status_code=404, detail=case_data.get("error", "Case not found"))

    # 2) MCQ üret
    try:
        mcq_full = mcq_agent.generate_mcq(case_data)
    except Exception as e:
        logger.error("start_simulation: MCQ generation failed for case_id=%s: %s", case_data.get("id"), e)
        raise HTTPException(status_code=503, detail={"error_code": "MCQ_GENERATION_FAILED", "message": str(e)})

    # MCQAgent silently returns a placeholder on total failure instead of
    # raising (see mcq/mcq_agent.py) — that's fine for the evaluation harness,
    # which specifically checks for this, but a real student must never see
    # a fake "Seçenek A/B/C/D" question and have it graded as answerable.
    if is_fallback_mcq(mcq_full):
        logger.error("start_simulation: fallback MCQ for case_id=%s, refusing to create session", case_data.get("id"))
        raise HTTPException(status_code=503, detail={
            "error_code": "MCQ_GENERATION_FAILED",
            "message": "Could not generate a valid question for this case. Please try again.",
        })

    # 3) SESSION OLUŞTUR VE DB'YE YAZ (tek kaynak: SQLite — RAM fallback yok)
    session_id = str(uuid.uuid4())

    new_db_session = models.ChatSession(
        session_id=session_id,
        case_id=case_data.get("id"),
        mcq_data=json.dumps(mcq_full, ensure_ascii=False),
        status="in_progress",
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
        elif existing_session.case_id != case_id:
            # Bu session başka bir vakaya ait — mesajların yanlış oturuma
            # yazılmasını engelle (bkz. docs/architecture.md §6, madde 11).
            logger.warning(
                "chat_with_agent: session/case mismatch session_id=%s session.case_id=%s requested_case_id=%s",
                current_session_id, existing_session.case_id, case_id,
            )
            raise HTTPException(status_code=409, detail={
                "error_code": "SESSION_CASE_MISMATCH",
                "message": "This session belongs to a different case.",
            })
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
        if mode == "hint":
            dbs.increment_hint_count(current_session_id)

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
    Cevabı kontrol eder ve CaseAnswer olarak kalıcı biçimde kaydeder.
    Bir session için yalnızca İLK gönderim istatistikleri etkiler ve Tutor
    Agent'ı çağırır; aynı session'a yapılan sonraki gönderimler DB'de zaten
    var olan cevabı idempotent şekilde döndürür (stats tekrar artmaz, LLM
    tekrar çağrılmaz) — bkz. docs/architecture.md §6, madde 11.
    """
    dbs = DBService(db)

    # 1. Session'ı DB'den çek
    db_session = db.query(models.ChatSession).filter_by(session_id=session_id).first()

    if not db_session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")

    case_id = db_session.case_id

    # 2. Zaten cevaplanmış mı? — idempotent kısayol.
    existing_answer = dbs.get_existing_answer(session_id)
    if existing_answer:
        logger.info("submit_answer: session_id=%s already answered, returning stored result", session_id)
        return {
            "session_id": session_id,
            "case_id": case_id,
            "selectedIndex": existing_answer.selected_index,
            "correctIndex": existing_answer.correct_index,
            "isCorrect": existing_answer.is_correct,
            "already_answered": True,
            "tutor": {
                "answer": "You've already submitted an answer for this question.",
                "followups": [],
                "safety": {"medical": "educational_only", "note": "Not medical advice."},
                "meta": {"already_answered": True},
            },
        }

    # 3. MCQ Verisini DB'den Oku (tek kaynak: SQLite ChatSession.mcq_data)
    mcq_full = {}
    if db_session.mcq_data:
        try:
            mcq_full = json.loads(db_session.mcq_data)
        except Exception as e:
            logger.error("submit_answer: MCQ data parse failed for session_id=%s: %s", session_id, e)

    # Önceden bozuk/eksik MCQ verisinde doğru cevap sessizce 0 kabul
    # ediliyordu — artık kontrollü bir hata dönülüyor (bkz. §6, madde 11).
    options = mcq_full.get("options", [])
    if not mcq_full or "correctIndex" not in mcq_full or len(options) != 4:
        logger.error("submit_answer: invalid/missing MCQ data for session_id=%s", session_id)
        raise HTTPException(status_code=422, detail={
            "error_code": "MCQ_DATA_INVALID",
            "message": "This session's question data is missing or corrupted and cannot be graded.",
        })

    # 4. Case verisini çek
    case = selector_agent.get_case_by_id(db, case_id)

    # 5. Doğru Cevabı Belirle
    correct_index = int(mcq_full["correctIndex"])
    question_text = mcq_full.get("question", "Soru verisi yüklenemedi.")
    selected_index = int(req.selectedIndex)
    is_correct = (selected_index == correct_index)

    # 6. Yanıt süresi — oturum başlangıcından (MCQ'nun gösterildiği an) bu
    #    isteğe kadar geçen süre. Öğrencinin case/chat ekranında geçirdiği
    #    süreyi de içerir (soruya "aktif düşünme" süresinin kesin bir ölçüsü
    #    değil), ama ek bir "soru gösterildi" zaman damgası olmadan elde
    #    edilebilecek en iyi yaklaşık değer budur.
    response_time_ms = None
    if db_session.created_at:
        started = db_session.created_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        response_time_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

    # --- DB İŞLEMLERİ (yalnızca ilk gönderimde) ---
    dbs.record_answer(
        session_id=session_id, case_id=case_id, selected_index=selected_index,
        correct_index=correct_index, is_correct=is_correct, response_time_ms=response_time_ms,
    )
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