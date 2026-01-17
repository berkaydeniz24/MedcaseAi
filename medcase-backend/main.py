from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.case_service import case_service
from agents.dialogue_agent import dialogue_agent
import uvicorn  # <--- Bunu ekledik

app = FastAPI()

# CORS Ayarları (Rehber Sayfa 8)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Modeli (Rehber Sayfa 9)
class QueryRequest(BaseModel):
    question: str

# 1. Tüm Vakaları Listeleme (Rehber Sayfa 8)
@app.get("/cases")
def list_cases():
    # Sadece ID ve Özet bilgisi dönüyoruz
    cases = case_service.cases
    return [
        {
            "id": c.get("id"), 
            "title": f"{c.get('demographics', 'Hasta')} - {c.get('specialty', 'Genel')}",
            "summary": c.get("narrative", "")[:100] + "..."
        } 
        for c in cases
    ]

# 2. Tek Vaka Detayı (Rehber Sayfa 8)
@app.get("/cases/{case_id}")
def get_case(case_id: str):
    # 'get_case_by_id' fonksiyonunun case_service.py içinde olduğundan emin olmalısın
    case = case_service.get_case_by_id(case_id) 
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

# 3. Soru Sorma (Rehber Sayfa 9)
@app.post("/cases/{case_id}/query")
async def query_case(case_id: str, req: QueryRequest):
    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Diyalog ajanını çağır
    response = await dialogue_agent.handle_response(req.question, case)
    return response

if __name__ == "__main__":
    # Sunucuyu 8000 portunda başlatır
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)