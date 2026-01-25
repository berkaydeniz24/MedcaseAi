# main.py
import sys
import os

# --- SİGORTA KODU ---
# Python'un klasörleri bulmasını garantiye alır
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv() # .env dosyasını yükle

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# --- DATABASE SETUP (EKLENDİ) ---
# Tabloları oluştur (varsa dokunmaz)
from services import models
from services.database import engine
models.Base.metadata.create_all(bind=engine)

# --- YENİ MİMARİ: Case Service yerine Selector Agent ---
from case_selector.selector_agent import selector_agent

# --- ROUTER IMPORTLARI ---
tutor_router = None
dialogue_router = None
user_router = None  # <--- EKLENDİ

try:
    from routers import tutor_router
    from routers import dialogue_router
    from routers import user_router # <--- EKLENDİ
    HAS_ROUTERS = True
except ImportError as e:
    HAS_ROUTERS = False
    print(f"⚠️ UYARI: Routerlar yüklenemedi. Sebebi: {e}")

app = FastAPI()

# --- 1. STATİK DOSYALAR (RESİMLER İÇİN) ---
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "data")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- 2. ROUTERLARI BAĞLAMA ---
if dialogue_router:
    app.include_router(dialogue_router.router, prefix="/dialogue", tags=["Dialogue"])

if tutor_router:
    app.include_router(tutor_router.router, prefix="/tutor", tags=["tutor"])

if user_router:  # <--- EKLENDİ (İstatistik Endpointleri)
    app.include_router(user_router.router, prefix="/user", tags=["User"])

# --- 3. CORS AYARLARI (Mobil Uygulama İçin) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Modeli
class QueryRequest(BaseModel):
    question: str

# --- 4. VAKA LİSTELEME ---
@app.get("/cases")
def list_cases():
    cases = selector_agent.cases
    return [
        {
            "id": c.get("id"),
            "title": c.get("title", "Başlıksız Vaka"),
            "specialty": c.get("specialty", "Genel"),
            "difficulty": c.get("difficulty", "Orta"),
            "summary": c.get("narrative", "")[:120] + "...",
            "has_image": len(c.get("assets", {}).get("images", [])) > 0
        } 
        for c in cases
    ]

# --- 5. TEK VAKA DETAYI ---
@app.get("/cases/{case_id}")
def get_case(case_id: str):
    case = selector_agent.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# --- 6. ESKİ SOHBET ENDPOINTİ (Legacy Support) ---
@app.post("/cases/{case_id}/query")
async def query_case(case_id: str, req: QueryRequest):
    case_data = selector_agent.get_case_by_id(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail="Vaka bulunamadı")
    
    try:
        from dialogue.dialogue_agent import DialogueAgent
        temp_agent = DialogueAgent()
        
        response = temp_agent.generate_response(
            user_input=req.message if hasattr(req, 'message') else req.question,
            case_data=case_data,
            mode="explain"
        )
        return response
    except Exception as e:
        print(f"Hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Sunucu Python üzerinden başlatılıyor...")
    uvicorn.run(app, host="127.0.0.1", port=8000)