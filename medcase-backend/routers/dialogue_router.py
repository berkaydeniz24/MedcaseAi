# routers/dialogue_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from dialogue.dialogue_agent import DialogueAgent
from case_selector.selector_agent import selector_agent

# Step 1 servisleri
from services.session_store import session_store
from services.mcq_generator import mcq_generator

# Tutor
from tutor.tutor_agent import tutor_agent
from tutor.schemas import TutorInput, CaseContext, StepContext, UserContext

router = APIRouter()
dialogue_agent = DialogueAgent()


# ---------- Request Models ----------
class DialogueRequest(BaseModel):
    message: str
    mode: Optional[str] = "hint"          # hint | explain | teach
    userLevel: Optional[str] = "beginner" # beginner | intermediate | advanced
    language: Optional[str] = "tr"        # tr | en


class AnswerRequest(BaseModel):
    selectedIndex: int = Field(ge=0)
    mode: Optional[str] = "explain"       # hint | explain | teach
    userLevel: Optional[str] = "beginner" # beginner | intermediate | advanced
    language: Optional[str] = "en"        # tr | en


# ---------- 1) START: case + session + mcq ----------
@router.get("/start")
def start_simulation():
    # 1) Case seç
    case_data = selector_agent.select_random_case()
    if not case_data or ("error" in case_data):
        raise HTTPException(status_code=404, detail=case_data.get("error", "Case not found"))

    # 2) MCQ üret (FULL = correctIndex + rationale dahil)
    try:
        mcq_full = mcq_generator.generate_mcq(case_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {e}")

    # 3) Session yarat ve MCQ'yu session'a koy (ground truth içeride kalsın)
    session = session_store.create_session(case_id=case_data.get("id"), mcq=mcq_full)

    # 4) Frontend'e PUBLIC MCQ dön (correctIndex/rationale göndermiyoruz)
    mcq_public = {
        "question": mcq_full["question"],
        "options": mcq_full["options"],
    }

    return {
        "session_id": session.session_id,
        "case": case_data,
        "mcq": mcq_public
    }


# ---------- 2) CHAT: mode-based guidance ----------
@router.post("/{case_id}/chat")
async def chat_with_agent(case_id: str, req: DialogueRequest):
    case = selector_agent.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    mode = req.mode if req.mode in ["hint", "explain", "teach"] else "hint"
    language = req.language if req.language in ["tr", "en"] else "tr"
    user_level = req.userLevel or "beginner"

    # ✅ DialogueAgent şu an language/user_level parametrelerini kabul etmiyor olabilir.
    # Bu yüzden en güvenlisi: kullanıcı mesajına meta ekleyip agent'a tek parametre ile geçirmek.
    # (Bir sonraki adımda DialogueAgent'i de update edeceğiz.)
    user_input_with_meta = (
        f"[LANG={language}][USER_LEVEL={user_level}][MODE={mode}]\n"
        f"{req.message}"
    )

    try:
        response = dialogue_agent.generate_response(
            user_input=user_input_with_meta,
            case_data=case,
            mode=mode
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 3) ANSWER: evaluate + tutor feedback ----------
@router.post("/{session_id}/answer")
def submit_answer(session_id: str, req: AnswerRequest):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    case = selector_agent.get_case_by_id(session.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    mcq_full: Dict[str, Any] = session.mcq
    correct_index = int(mcq_full["correctIndex"])
    selected_index = int(req.selectedIndex)

    # Basic validation
    if selected_index < 0 or selected_index >= len(mcq_full["options"]):
        raise HTTPException(status_code=400, detail="selectedIndex out of range")

    is_correct = (selected_index == correct_index)

    # TutorInput hazırlığı (Tutor şemanız: step.correct var)
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

    # TutorAgent native olarak step.correct + user.selectedIndex kullanacak.
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
        "case_id": session.case_id,
        "selectedIndex": selected_index,
        "correctIndex": correct_index,  # debug için açık; prod'da kapatabiliriz
        "isCorrect": is_correct,
        "tutor": tutor_out
    }
