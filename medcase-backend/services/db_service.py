# services/db_service.py
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from . import models
import uuid

DEMO_USER_ID = "demo-user"  # no real auth yet — see docs/architecture.md

class DBService:
    def __init__(self, db: Session):
        self.db = db

    # --- İSTATİSTİK İŞLEMLERİ ---
    def update_stats(self, is_correct: bool):
        stats = self.db.query(models.UserStats).first()
        if not stats:
            stats = models.UserStats(total_correct=0, total_wrong=0)
            self.db.add(stats)
        
        if is_correct:
            stats.total_correct += 1
        else:
            stats.total_wrong += 1
        self.db.commit()
        return stats

    def get_stats(self):
        stats = self.db.query(models.UserStats).first()
        if not stats:
            return {"total_correct": 0, "total_wrong": 0}
        return stats

    # --- VAKA DURUMU İŞLEMLERİ ---
    def update_case_status(self, case_id: str, status: str):
        # status: 'new', 'in_progress', 'solved'
        progress = self.db.query(models.CaseProgress).filter_by(case_id=case_id).first()
        if not progress:
            progress = models.CaseProgress(case_id=case_id, status=status)
            self.db.add(progress)
        else:
            # Eğer zaten çözüldüyse, tekrar 'in_progress' yapma (isteğe bağlı)
            if progress.status != "solved": 
                progress.status = status
            # Eğer 'solved' geldiyse zorla güncelle
            if status == "solved":
                progress.status = "solved"
                
        self.db.commit()

    def get_all_case_statuses(self):
        return self.db.query(models.CaseProgress).all()

    # --- CHAT OTURUMU İŞLEMLERİ ---
    def create_session(self, case_id: str):
        session_id = str(uuid.uuid4())
        new_session = models.ChatSession(session_id=session_id, case_id=case_id)
        self.db.add(new_session)
        
        # Oturum açılınca vaka durumu "in_progress" olsun
        self.update_case_status(case_id, "in_progress")
        
        self.db.commit()
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        msg = models.ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        self.db.commit()

    def get_chat_history(self, session_id: str):
        return self.db.query(models.ChatMessage).filter_by(session_id=session_id).order_by(models.ChatMessage.timestamp).all()

    # --- CEVAP KAYITLARI (CaseAnswer) ---
    def get_existing_answer(self, session_id: str):
        return self.db.query(models.CaseAnswer).filter_by(session_id=session_id).first()

    def record_answer(
        self, session_id: str, case_id: str, selected_index: int,
        correct_index: int, is_correct: bool, response_time_ms: int | None,
        user_id: str = DEMO_USER_ID,
    ) -> models.CaseAnswer:
        """
        Persists exactly one CaseAnswer per session_id (unique constraint on
        the column enforces this at the DB level too). Callers MUST check
        get_existing_answer() first — this does not itself guard against a
        second insert; a second call on an already-answered session will
        raise an IntegrityError, by design, rather than silently duplicating
        or overwriting the first answer.
        """
        answer = models.CaseAnswer(
            session_id=session_id, case_id=case_id, user_id=user_id,
            selected_index=selected_index, correct_index=correct_index,
            is_correct=is_correct, response_time_ms=response_time_ms,
        )
        self.db.add(answer)

        session = self.db.query(models.ChatSession).filter_by(session_id=session_id).first()
        if session:
            session.status = "completed"
            session.completed_at = func.now()

        self.db.commit()
        self.db.refresh(answer)
        return answer