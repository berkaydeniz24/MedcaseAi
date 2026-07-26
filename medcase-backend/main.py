# main.py
import sys
import os

# --- SİGORTA KODU ---
# Python'un klasörleri bulmasını garantiye alır
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv() # .env dosyasını yükle

import json
import logging

from services.logging_config import configure_logging
configure_logging()
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uvicorn

# --- DATABASE SETUP (EKLENDİ) ---
# Tabloları oluştur (varsa dokunmaz) — yeni tablolar (ör. case_answers) burada
# oluşur, ama var olan tablolara yeni SÜTUN eklemez (bkz. aşağıdaki migration).
from services import models
from services.database import engine, get_db, SessionLocal
models.Base.metadata.create_all(bind=engine)

from services.migrate_session_lifecycle import ensure_session_lifecycle_columns
ensure_session_lifecycle_columns()

# --- Vaka verisini (ilk kurulumda) SQL'e yükle ---
from services.seed_cases import seed_cases_if_empty
from services.backfill_source_metadata import backfill_if_needed
_seed_db = SessionLocal()
try:
    seed_cases_if_empty(_seed_db)
    backfill_if_needed(_seed_db)
finally:
    _seed_db.close()

# --- YENİ MİMARİ: Case Service yerine Selector Agent (artık SQL üzerinden çalışıyor) ---
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
    logger.warning("Routerlar yüklenemedi. Sebebi: %s", e)

APP_NAME = os.getenv("APP_NAME", "MedCase AI API")
APP_VERSION = os.getenv("APP_VERSION", "0.2.0")
APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI(title=APP_NAME, version=APP_VERSION)

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
# .env üzerinden daraltılabilir (virgülle ayrılmış origin listesi); yoksa
# mevcut davranış (herkese açık) korunur — Expo web/simulator farklı
# origin'lerden istek atabildiği için varsayılanı sıkılaştırmak riskli.
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = ["*"] if _cors_origins_env.strip() == "*" else [
    o.strip() for o in _cors_origins_env.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HEALTH CHECK ---
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "environment": APP_ENV,
    }

# Request Modeli
class QueryRequest(BaseModel):
    question: str

# --- 4. VAKA LİSTELEME (SQL üzerinden) ---
@app.get("/cases")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(models.Case).all()
    result = []
    for c in cases:
        assets = json.loads(c.assets_json or "{}")
        result.append({
            "id": c.id,
            "title": c.title or "Başlıksız Vaka",
            "specialty": c.specialty or "Genel",
            "difficulty": c.difficulty or "Orta",
            "summary": (c.narrative or "")[:120] + "...",
            "has_image": len(assets.get("images", [])) > 0
        })
    return result

# --- 5. TEK VAKA DETAYI ---
@app.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = selector_agent.get_case_by_id(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# --- 6. ESKİ SOHBET ENDPOINTİ (Legacy Support) ---
@app.post("/cases/{case_id}/query")
async def query_case(case_id: str, req: QueryRequest, db: Session = Depends(get_db)):
    case_data = selector_agent.get_case_by_id(db, case_id)
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
        logger.error("query_case failed for case_id=%s: %s", case_id, e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("Sunucu Python üzerinden başlatılıyor...")
    uvicorn.run(app, host="127.0.0.1", port=8000)