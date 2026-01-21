# services/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from .database import Base

# 1. Kullanıcı İstatistikleri (Doğru/Yanlış Sayısı)
class UserStats(Base):
    __tablename__ = "user_stats"
    id = Column(Integer, primary_key=True, index=True)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)

# 2. Vaka İlerleme Durumu (Çözüldü/Devam Ediyor/Çözülecek)
class CaseProgress(Base):
    __tablename__ = "case_progress"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True) # JSON'daki "case_id"
    status = Column(String, default="new") # new, in_progress, solved
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())

# 3. Chat Oturumu (Hangi vaka konuşuluyor?)
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String, primary_key=True, index=True) # UUID
    case_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 4. Chat Mesajları (Geçmişi tutmak için)
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String) # "user" veya "ai"
    content = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())