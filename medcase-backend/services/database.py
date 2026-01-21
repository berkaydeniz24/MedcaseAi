# services/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Veritabanı dosyasının adı. Proje klasöründe "medcase.db" olarak oluşacak.
SQLALCHEMY_DATABASE_URL = "sqlite:///./medcase.db"

# SQLite için thread check iptali gerekiyor
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency (Routerlarda kullanmak için)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()