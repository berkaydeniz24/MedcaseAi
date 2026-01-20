# routers/tutor_router.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from services.case_service import case_service

# Sende nasıl tanımlıysa:
# - Eğer tutor_agent bir instance ise: from tutor.tutor_agent import tutor_agent
# - Eğer class ise: from tutor.tutor_agent import TutorAgent
from tutor.tutor_agent import TutorAgent

from tutor.schemas import (
    TutorInput,
    TutorOutput,
    CaseContext,
    StepContext,
    UserContext,
)

router = APIRouter(tags=["tutor"])


# -------- Request models (FastAPI) --------
class StepPayload(BaseModel):
    question: str = Field(min_length=1)
    options: List[str] = Field(default_factory=list)
    correct: Optional[int] = None
    selectedIndex: Optional[int] = None


class TutorRequest(BaseModel):
    mode: Literal["hint", "explain", "teach"] = "hint"
    case_id: str
    message: str
    step: Optional[StepPayload] = None


@router.post("", response_model=TutorOutput)
async def tutor(req: TutorRequest) -> TutorOutput:
    # 1) Case çek
    case = case_service.get_case_by_id(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {req.case_id}")

    # 2) StepContext (zorunluysa requestte step şart yap, değilse default üret)
    # Senin StepContext şeman question/options min_length istiyor; o yüzden step yoksa
    # case içinden seed_questions veya narrative'den default üretmek gerekiyor.
    if req.step is None:
        # Minimum çalışsın diye basit default:
        seed_q = (case.get("seed_questions") or ["Bu vakada ilk yaklaşımın nedir?"])[0]
        step_ctx = StepContext(
            question=seed_q,
            options=["Devam et", "İpucu ver"],  # en az 2 seçenek şartsa
            correct=0,  # correct zorunluysa 0 veriyoruz (teach modda kullanılabilir)
        )
        user_ctx = UserContext(selectedIndex=None, ask=req.message)
    else:
        step_ctx = StepContext(
            question=req.step.question,
            options=req.step.options or ["Devam et", "İpucu ver"],
            correct=req.step.correct if req.step.correct is not None else 0,
        )
        user_ctx = UserContext(
            selectedIndex=req.step.selectedIndex,
            ask=req.message,
        )

    # 3) CaseContext
    # DİKKAT: senin CaseContext şeman hangi alanları istiyorsa ona göre doldur.
    case_ctx = CaseContext(
        id=case.get("id", req.case_id),
        title=case.get("title", ""),
        summary=case.get("summary", ""),   # yoksa boş
        step=step_ctx,
    )

    # 4) TutorInput
    inp = TutorInput(
        mode=req.mode,
        case_id=req.case_id,
        message=req.message,
        case=case_ctx,
        user=user_ctx,
    )

    # 5) Agent çağır (tek parametre)
    agent = TutorAgent()
    out = agent.run(inp)
    return out