# routers/user_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.database import get_db
from services.db_service import DBService

router = APIRouter()

@router.get("/stats")
def get_user_stats(db: Session = Depends(get_db)):
    """Telefonda göstermek için istatistikleri çeker"""
    dbs = DBService(db)
    # Şimdilik tüm kullanıcıların toplamını veya tekil istatistiği döner
    return dbs.get_stats()

@router.get("/progress")
def get_case_progress(db: Session = Depends(get_db)):
    """Hangi vakalar çözüldü listesini döner"""
    dbs = DBService(db)
    return dbs.get_all_case_statuses()