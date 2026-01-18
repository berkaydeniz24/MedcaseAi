# routers/dialogue_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# --- YENİ BAĞLANTILAR ---
from dialogue.dialogue_agent import DialogueAgent
from case_selector.selector_agent import selector_agent # <-- Yeni eklediğimiz ajan

router = APIRouter()
dialogue_agent = DialogueAgent()

# Modeller
class DialogueRequest(BaseModel):
    message: str

# 1. Simülasyon Başlat (Rastgele Vaka)
@router.get("/start")
def start_simulation():
    # Case Selector ajanı devreye giriyor
    case_data = selector_agent.select_random_case()
    if "error" in case_data:
        raise HTTPException(status_code=404, detail=case_data["error"])
    return case_data

# 2. Sohbet Etme
@router.post("/{case_id}/chat")
async def chat_with_agent(case_id: str, req: DialogueRequest):
    # Vakayı bul
    case = selector_agent.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        # Dialogue Agent cevap üretiyor
        response = dialogue_agent.generate_response(
            user_input=req.message,
            case_data=case,
            mode="hint"
        )
        return response
    except Exception as e:
        print(f"Hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))