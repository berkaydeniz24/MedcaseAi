from dotenv import load_dotenv
load_dotenv() # .env dosyasını en başta yükle

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Servisler ve Agentlar
from services.case_service import case_service

# Arkadaşının yazdığı router (Dosya varsa hata vermez, yoksa burayı yorum satırı yap)
try:
    from rooters import tutor_rooter as tutor_router
    HAS_TUTOR_ROUTER = True
except ImportError:
    HAS_TUTOR_ROUTER = False
    print("⚠️ UYARI: 'rooters.tutor_rooter' bulunamadı, tutor endpointleri devre dışı.")

app = FastAPI()

# Eğer tutor router varsa ekle
if HAS_TUTOR_ROUTER:
    app.include_router(tutor_router.router, prefix="/tutor", tags=["tutor"])

# CORS Ayarları (Frontend erişimi için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Modeli
class QueryRequest(BaseModel):
    question: str

# --- 1. TÜM VAKALARI LİSTELEME ---
@app.get("/cases")
def list_cases():
    cases = case_service.cases
    # Yeni JSON formatına göre listeleme yapıyoruz
    return [
        {
            "id": c.get("id"),
            # Yeni JSON'da 'title' hazır geliyor, birleştirmeye gerek yok
            "title": c.get("title", "Başlıksız Vaka"),
            # Frontend'de filtreleme yapmak için bu alanları ekliyoruz
            "specialty": c.get("specialty", "Genel"),
            "difficulty": c.get("difficulty", "Orta"),
            # Narrative'den kısa bir özet
            "summary": c.get("narrative", "")[:120] + "...",
            # Frontend'e resim olup olmadığı bilgisini gönderelim (ikon göstermek için)
            "has_image": len(c.get("assets", {}).get("images", [])) > 0
        } 
        for c in cases
    ]

# --- 2. TEK VAKA DETAYI ---
@app.get("/cases/{case_id}")
def get_case(case_id: str):
    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# --- 3. DİYALOG AJANI İLE KONUŞMA ---
@app.post("/cases/{case_id}/query")
async def query_case(case_id: str, req: QueryRequest):
    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Dialogue Agent'a gönderiyoruz. 
    # Not: DialogueAgent kodunu da yeni JSON yapısındaki 'rubric' ve 'narrative'i
    # anlayacak şekilde güncellediğinden emin olmalısın.
    response = await dialogue_agent.handle_response(req.question, case)
    return response

if __name__ == "__main__":
    print("🚀 Sunucu başlatılıyor...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)