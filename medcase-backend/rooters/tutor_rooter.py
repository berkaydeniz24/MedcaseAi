from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Sizde tutor agent kodu nerede ise import path'i ona göre düzeltin:
# Örn: from tutor.tutor_agent import TutorAgent
from tutor.tutor_agent import TutorAgent

# Sizde case_service nerede ise import path'i ona göre düzeltin:
# Örn: from services.case_service import case_service
from services.case_service import case_service


router = APIRouter()


# ---- Request/Response Schemas ----

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
def tutor(req: TutorRequest) -> TutorResponse:
    # 1) Case'i dataset'ten çek
    case = case_service.get_case_by_id(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {req.case_id}")

    # 2) TutorAgent'e gidecek minimal context'i çıkar
    # Dataset örneğiniz: id, specialty, narrative, assets.images[] ...  [oai_citation:1‡cases_subset (1).json](sediment://file_00000000c18471f49a9ab22d587b3d0e)
    case_context = {
        "id": case.get("id"),
        "specialty": case.get("specialty"),
        "narrative": case.get("narrative"),
        "title": case.get("title"),
        "difficulty": case.get("difficulty"),
        "assets": case.get("assets", {}),
        "rubric": case.get("rubric", {}),
        "seed_questions": case.get("seed_questions", []),
    }

    step_context = {
        "question": (req.step.question if req.step else None),
        "options": (req.step.options if req.step else []),
        "selected_option": (req.step.selected_option if req.step else None),
    }

    # 3) TutorAgent çağır
    agent = TutorAgent()  # TutorAgent init'inizde model vs. env'den okunuyorsa bu yeterli
    out = agent.run(
        mode=req.mode,
        message=req.message,
        case=case_context,
        step=step_context,
    )

    # out dict ise aşağıdaki gibi normalize edin
    return TutorResponse(
        answer=out.get("answer", ""),
        followups=out.get("followups", []),
        safety=out.get("safety", {}),
        meta=out.get("meta", {}),
    )