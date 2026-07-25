from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from pydantic import BaseModel

from services.database import get_db
from services import models
from case_selector.selector_agent import selector_agent

router = APIRouter()

# --- Response Modelleri ---
class ChatHistoryItem(BaseModel):
    session_id: str
    case_id: str
    case_title: str
    last_message: str
    date: str

class UserStatsResponse(BaseModel):
    total_correct: int
    total_wrong: int

class CaseProgressItem(BaseModel):
    case_id: str
    status: str

# --- 1. İSTATİSTİKLER ---
@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(db: Session = Depends(get_db)):
    stats = db.query(models.UserStats).first()
    if not stats:
        return {"total_correct": 0, "total_wrong": 0}
    return {
        "total_correct": stats.total_correct,
        "total_wrong": stats.total_wrong
    }

# --- 2. VAKA İLERLEME ---
@router.get("/progress", response_model=List[CaseProgressItem])
def get_case_progress(db: Session = Depends(get_db)):
    progress_list = db.query(models.CaseProgress).all()
    result = []
    for p in progress_list:
        result.append({
            "case_id": p.case_id,
            "status": p.status
        })
    return result

# --- 3. SOHBET GEÇMİŞİ (DÜZELTİLDİ) ---
@router.get("/history", response_model=List[ChatHistoryItem])
def get_user_chat_history(db: Session = Depends(get_db)):
    """
    Kullanıcının sohbet geçmişini temiz bir şekilde listeler.
    1. Aynı vaka için birden fazla oturum varsa sadece EN SONUNCUSU gelir.
    2. Önizleme olarak son mesaj değil, kullanıcının İLK MESAJI gösterilir.
    """
    # Tüm oturumları en yeni en üstte olacak şekilde çek
    all_sessions = db.query(models.ChatSession).order_by(desc(models.ChatSession.created_at)).all()
    
    # --- GRUPLAMA VE TEKİLLEŞTİRME ---
    # Case ID'ye göre filtrele: Her vaka için sadece en güncel oturumu al.
    unique_sessions_map = {}
    for sess in all_sessions:
        if sess.case_id not in unique_sessions_map:
            unique_sessions_map[sess.case_id] = sess
    
    # Sözlükten listeye çevir (Tarih sırasını koruyarak)
    filtered_sessions = sorted(unique_sessions_map.values(), key=lambda x: x.created_at, reverse=True)
    
    history_list = []
    
    for sess in filtered_sessions:
        # --- İLK MESAJI BULMA ---
        # Kullanıcının ("user") attığı İLK mesajı ("asc") bul.
        first_msg = db.query(models.ChatMessage)\
            .filter(models.ChatMessage.session_id == sess.session_id)\
            .filter(models.ChatMessage.role == "user")\
            .order_by(models.ChatMessage.timestamp.asc())\
            .first()
            
        # Eğer kullanıcı hiç yazmamışsa (sadece sistem mesajı varsa), sistemin ilk mesajını al
        if not first_msg:
             first_msg = db.query(models.ChatMessage)\
                .filter(models.ChatMessage.session_id == sess.session_id)\
                .order_by(models.ChatMessage.timestamp.asc())\
                .first()
        
        # Hala mesaj yoksa bu boş oturumu listeye ekleme
        if not first_msg:
            continue

        # Vaka başlığını bul
        case_info = selector_agent.get_case_by_id(db, sess.case_id)
        title = case_info.get("title", f"Vaka #{sess.case_id}") if case_info else f"Vaka #{sess.case_id}"

        history_list.append({
            "session_id": sess.session_id,
            "case_id": sess.case_id,
            "case_title": title,
            # Mesaj önizlemesi
            "last_message": first_msg.content[:80] + "..." if len(first_msg.content) > 80 else first_msg.content,
            "date": sess.created_at.strftime("%d.%m.%Y %H:%M") if sess.created_at else ""
        })
        
    return history_list