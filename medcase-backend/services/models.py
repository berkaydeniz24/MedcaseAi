# services/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class UserStats(Base):
    __tablename__ = "user_stats"
    id = Column(Integer, primary_key=True, index=True)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)

class CaseProgress(Base):
    __tablename__ = "case_progress"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    status = Column(String, default="new")
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String, primary_key=True, index=True)
    case_id = Column(String)
    # 👇 YENİ EKLENEN SATIR: MCQ verisini JSON string olarak burada saklayacağız
    mcq_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Session lifecycle (2026-07-26 — services/migrate_answers_and_sessions.py):
    # "in_progress" -> "completed" when an answer is submitted. Separate from
    # CaseProgress.status, which tracks per-CASE mastery, not per-SESSION state.
    status = Column(String, default="in_progress")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    hints_used = Column(Integer, default=0)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class CaseAnswer(Base):
    """
    One row per submitted MCQ answer — previously there was no persisted
    record of individual attempts at all, only aggregate UserStats/
    CaseProgress counters that got incremented on every POST regardless of
    whether the same session had already answered. A unique constraint on
    session_id enforces "one final answer per session" at the DB level;
    routers/dialogue_router.py checks for an existing row before doing
    anything else and returns the stored result idempotently on a repeat.
    """
    __tablename__ = "case_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), unique=True, index=True)
    case_id = Column(String, index=True)
    user_id = Column(String, default="demo-user", index=True)  # no real auth yet — see docs/architecture.md
    selected_index = Column(Integer)
    correct_index = Column(Integer)
    is_correct = Column(Boolean)
    response_time_ms = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="Unknown Case")
    specialty = Column(String, default="General")
    difficulty = Column(String, default="Intermediate")
    narrative = Column(Text, default="")
    # Ham iç içe yapılar (assets/rubric/seed_questions) JSON string olarak saklanır.
    assets_json = Column(Text, default="{}")
    rubric_json = Column(Text, default="{}")
    seed_questions_json = Column(Text, default="[]")

    # Kaynak/lisans metadata (docs/dataset.md — MultiCaRe/PMC kaynaklı vakalar
    # için atıf zorunluluğu var). services/backfill_source_metadata.py ile
    # docs/dataset_source_metadata.json'dan doldurulur.
    source_title = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    source_doi = Column(String, nullable=True)
    source_authors = Column(Text, nullable=True)
    source_year = Column(Integer, nullable=True)
    license_name = Column(String, nullable=True)
    license_url = Column(String, nullable=True)
    citation_text = Column(Text, nullable=True)