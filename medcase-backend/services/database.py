# services/database.py
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

# .env üzerinden değiştirilebilir (ör. ileride Postgres'e geçiş için);
# yoksa mevcut varsayılan: proje klasöründe "medcase.db".
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./medcase.db")

# "check_same_thread" yalnızca SQLite'a özgü bir ayar; başka bir backend'e
# geçilirse (ör. Postgres) bu kwarg'ı göndermemek gerekir.
_connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency (Routerlarda kullanmak için)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()