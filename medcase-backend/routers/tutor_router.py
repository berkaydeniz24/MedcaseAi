# routers/tutor_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

# Import yollarını senin proje yapına göre güncelledim
from agents.tutor_agent import tutor_agent
from services.case_service import case_service

router = APIRouter()

# ---- Modeller ----
class StepPayload(BaseModel):
    question: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    selected_option: Optional[str] = None

class TutorRequest(BaseModel):
    mode: Literal["hint", "explain", "teach"] = "hint"
    case_id: str
    message: str
    step: Optional[StepPayload] = None

class TutorResponse(BaseModel):
    answer: str
    followups: List[str] = Field(default_factory=list)
    safety: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)

# ---- Endpoint ----
@router.post("", response_model=TutorResponse)
async def tutor(req: TutorRequest) -> TutorResponse:
    # 1. Vakayı bul
    case = case_service.get_case_by_id(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {req.case_id}")

    # 2. Agent için veriyi hazırla
    # Hata almamak için .get ile güvenli çekim yapıyoruz
    case_context = {
        "id": case.get("id"),
        "narrative": case.get("narrative"),
        "specialty": case.get("specialty"),
        "rubric": case.get("rubric", {}), # Doğru cevap burada
    }

    step_context = {
        "options": (req.step.options if req.step else []),
    }

    # 3. Agent'ı çalıştır
    # Senin tutor_agent.py yapına uygun çağrı:
    result = tutor_agent.run(
        mode=req.mode,
        message=req.message,
        case=case_context,
        step=step_context
    )

    return TutorResponse(
        answer=result.get("answer", ""),
        followups=result.get("followups", []),
        safety=result.get("safety", {}),
        meta=result.get("meta", {})
    )