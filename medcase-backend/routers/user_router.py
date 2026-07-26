from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, field_validator

from services.database import get_db
from services import models
from services.db_service import DEMO_USER_ID
from case_selector.selector_agent import selector_agent

router = APIRouter()

# --- Response Modelleri ---
class DailyActivity(BaseModel):
    date: str
    day_label: str
    count: int

class ChatHistoryItem(BaseModel):
    session_id: str
    case_id: str
    case_title: str
    specialty: str
    last_message: str
    date: str
    status: str
    is_correct: Optional[bool] = None
    hints_used: int = 0
    response_time_ms: Optional[int] = None
    completed_at: Optional[str] = None

class UserStatsResponse(BaseModel):
    total_correct: int
    total_wrong: int
    weekly_activity: List[DailyActivity] = []

class CaseProgressItem(BaseModel):
    case_id: str
    status: str
    session_id: Optional[str] = None

class UserProfileResponse(BaseModel):
    full_name: str
    email: str
    university: str
    department: str
    student_id: str

class UserProfileUpdate(BaseModel):
    # Only full_name/email are user-editable — university/department/
    # student_id stay server-set, read-only in the UI (app/profile.js).
    full_name: str
    email: str

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be empty")
        return v

    @field_validator("email")
    @classmethod
    def email_looks_valid(cls, v):
        v = v.strip()
        if "@" not in v or "." not in v.split("@")[-1] or v.startswith("@") or v.endswith("@"):
            raise ValueError("email does not look valid")
        return v

# --- 1. İSTATİSTİKLER ---
@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(db: Session = Depends(get_db)):
    stats = db.query(models.UserStats).filter_by(user_id=DEMO_USER_ID).first()

    # Son 7 gün, bugün dahil, en eskiden en yeniye — gerçek ChatSession.created_at
    # üzerinden. Önceden frontend'de sabit/uydurma bir dizi vardı ("Simulated"
    # etiketiyle) — artık gerçek vaka başlatma aktivitesini gösteriyor.
    today = datetime.now(timezone.utc).date()
    day_start = today - timedelta(days=6)
    # SQLite stores ChatSession.created_at as a naive UTC string
    # (CURRENT_TIMESTAMP default) — filtering with a naive datetime here
    # keeps the comparison a plain string comparison SQLite can do directly,
    # rather than risking a tz-aware value that serializes differently.
    range_start = datetime.combine(day_start, datetime.min.time())
    sessions_in_range = db.query(models.ChatSession).filter(
        models.ChatSession.created_at >= range_start
    ).all()

    counts_by_date = {}
    for sess in sessions_in_range:
        if not sess.created_at:
            continue
        d = sess.created_at.date()
        counts_by_date[d] = counts_by_date.get(d, 0) + 1

    weekly_activity = []
    for i in range(7):
        d = day_start + timedelta(days=i)
        weekly_activity.append({
            "date": d.isoformat(),
            "day_label": d.strftime("%a")[:1],
            "count": counts_by_date.get(d, 0),
        })

    return {
        "total_correct": stats.total_correct if stats else 0,
        "total_wrong": stats.total_wrong if stats else 0,
        "weekly_activity": weekly_activity,
    }

# --- 2. VAKA İLERLEME ---
@router.get("/progress", response_model=List[CaseProgressItem])
def get_case_progress(db: Session = Depends(get_db)):
    progress_list = db.query(models.CaseProgress).filter_by(user_id=DEMO_USER_ID).all()

    # Her case_id için EN SON oturumun session_id'sini bulmak amacıyla,
    # oturumları en yeniden en eskiye çekip ilk görüleni (= en yenisini)
    # sözlükte tutuyoruz — get_user_chat_history'deki dedup mantığıyla aynı
    # idiom, N+1 sorgu yerine tek sorgu.
    all_sessions = db.query(models.ChatSession).order_by(desc(models.ChatSession.created_at)).all()
    latest_session_by_case = {}
    for sess in all_sessions:
        if sess.case_id not in latest_session_by_case:
            latest_session_by_case[sess.case_id] = sess.session_id

    result = []
    for p in progress_list:
        result.append({
            "case_id": p.case_id,
            "status": p.status,
            "session_id": latest_session_by_case.get(p.case_id),
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

    # İlgili session_id'lerin CaseAnswer kayıtlarını tek sorguda çekip
    # session_id -> CaseAnswer sözlüğüne çeviriyoruz (N+1 sorgu yerine).
    relevant_session_ids = [sess.session_id for sess in filtered_sessions]
    answers_by_session = {
        a.session_id: a
        for a in db.query(models.CaseAnswer)
            .filter(models.CaseAnswer.session_id.in_(relevant_session_ids))
            .all()
    } if relevant_session_ids else {}

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

        # Vaka başlığını/branşını bul
        case_info = selector_agent.get_case_by_id(db, sess.case_id)
        title = case_info.get("title", f"Vaka #{sess.case_id}") if case_info else f"Vaka #{sess.case_id}"
        specialty = case_info.get("specialty", "General") if case_info else "General"

        answer = answers_by_session.get(sess.session_id)

        history_list.append({
            "session_id": sess.session_id,
            "case_id": sess.case_id,
            "case_title": title,
            "specialty": specialty,
            # Mesaj önizlemesi
            "last_message": first_msg.content[:80] + "..." if len(first_msg.content) > 80 else first_msg.content,
            "date": sess.created_at.strftime("%d.%m.%Y %H:%M") if sess.created_at else "",
            "status": sess.status or "in_progress",
            "is_correct": answer.is_correct if answer else None,
            "hints_used": sess.hints_used or 0,
            "response_time_ms": answer.response_time_ms if answer else None,
            "completed_at": sess.completed_at.strftime("%d.%m.%Y %H:%M") if sess.completed_at else None,
        })

    return history_list

def _get_or_create_profile(db: Session) -> models.UserProfile:
    profile = db.query(models.UserProfile).filter_by(user_id=DEMO_USER_ID).first()
    if not profile:
        profile = models.UserProfile(user_id=DEMO_USER_ID)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

# --- 4. PROFİL ---
@router.get("/profile", response_model=UserProfileResponse)
def get_user_profile(db: Session = Depends(get_db)):
    return _get_or_create_profile(db)

@router.put("/profile", response_model=UserProfileResponse)
def update_user_profile(payload: UserProfileUpdate, db: Session = Depends(get_db)):
    profile = _get_or_create_profile(db)
    profile.full_name = payload.full_name
    profile.email = payload.email
    db.commit()
    db.refresh(profile)
    return profile

# --- 5. VERİLERİ SIFIRLA ---
@router.post("/reset")
def reset_user_data(db: Session = Depends(get_db)):
    """
    demo-user'ın tüm pratik geçmişini (oturumlar, mesajlar, cevaplar, vaka
    ilerlemesi, istatistikler) temiz kuruluma döndürür. Profil bilgileri
    (isim/email) ve Case tablosu (vaka içeriği) etkilenmez.

    NOT: ChatSession/ChatMessage tablolarında henüz user_id yok (gerçek auth
    yok — bkz. docs/architecture.md), yani bu pratikte TÜM oturumları siler,
    sadece demo-user'ınkini değil. Şu an demo-user tek kullanıcı olduğu için
    bu eşdeğer, ama gerçek auth eklendiğinde burası user_id'ye göre
    filtrelenecek şekilde güncellenmeli.
    """
    db.query(models.ChatMessage).delete()
    db.query(models.CaseAnswer).filter_by(user_id=DEMO_USER_ID).delete()
    db.query(models.ChatSession).delete()
    db.query(models.CaseProgress).filter_by(user_id=DEMO_USER_ID).delete()

    stats = db.query(models.UserStats).filter_by(user_id=DEMO_USER_ID).first()
    if stats:
        stats.total_correct = 0
        stats.total_wrong = 0

    db.commit()
    return {"status": "ok"}