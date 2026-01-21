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

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())