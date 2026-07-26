# tests/test_user_profile.py
"""
Integration tests for GET/PUT /user/profile and POST /user/reset
(routers/user_router.py). Previously the Profile screen had no backend
counterpart at all -- pure frontend mock state, Save Changes had no
handler. Same isolated in-memory SQLite pattern as the other router tests.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services import models
from services.database import Base, get_db
from routers import user_router


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield sessionmaker(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(user_router.router, prefix="/user")
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c


def seed(db_session, *objs):
    db = db_session()
    for obj in objs:
        db.add(obj)
    db.commit()
    db.close()


# ---------- /user/profile ----------

def test_get_profile_creates_default_row_on_first_read(client):
    resp = client.get("/user/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "John Doe"
    assert data["email"] == "john.doe@email.com"
    assert data["university"] == "Biruni University"


def test_update_profile_persists_name_and_email(client):
    resp = client.put("/user/profile", json={"full_name": "Jane Smith", "email": "jane@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Jane Smith"
    assert data["email"] == "jane@example.com"

    # A subsequent GET must reflect the same saved values.
    again = client.get("/user/profile").json()
    assert again["full_name"] == "Jane Smith"
    assert again["email"] == "jane@example.com"


def test_update_profile_rejects_empty_name(client):
    resp = client.put("/user/profile", json={"full_name": "   ", "email": "jane@example.com"})
    assert resp.status_code == 422


def test_update_profile_rejects_invalid_email(client):
    resp = client.put("/user/profile", json={"full_name": "Jane Smith", "email": "not-an-email"})
    assert resp.status_code == 422


def test_update_profile_does_not_touch_academic_fields(client, db_session):
    seed(db_session, models.UserProfile(user_id="demo-user", university="Custom Uni", student_id="999"))
    client.put("/user/profile", json={"full_name": "Jane Smith", "email": "jane@example.com"})
    data = client.get("/user/profile").json()
    assert data["university"] == "Custom Uni"
    assert data["student_id"] == "999"


# ---------- /user/reset ----------

def test_reset_clears_sessions_messages_answers_and_progress(client, db_session):
    seed(
        db_session,
        models.Case(id="C1", title="Test", specialty="Cardiology", narrative="N"),
        models.ChatSession(session_id="s1", case_id="C1", status="completed"),
        models.ChatMessage(session_id="s1", role="user", content="hello"),
        models.CaseAnswer(session_id="s1", case_id="C1", user_id="demo-user", selected_index=0, correct_index=0, is_correct=True),
        models.CaseProgress(case_id="C1", user_id="demo-user", status="solved"),
        models.UserStats(user_id="demo-user", total_correct=5, total_wrong=2),
    )

    resp = client.post("/user/reset")
    assert resp.status_code == 200

    db = db_session()
    assert db.query(models.ChatSession).count() == 0
    assert db.query(models.ChatMessage).count() == 0
    assert db.query(models.CaseAnswer).count() == 0
    assert db.query(models.CaseProgress).count() == 0
    stats = db.query(models.UserStats).filter_by(user_id="demo-user").first()
    assert stats.total_correct == 0
    assert stats.total_wrong == 0
    db.close()


def test_reset_does_not_touch_profile_or_cases(client, db_session):
    seed(
        db_session,
        models.Case(id="C1", title="Test", specialty="Cardiology", narrative="N"),
        models.UserProfile(user_id="demo-user", full_name="Jane Smith", email="jane@example.com"),
    )

    client.post("/user/reset")

    db = db_session()
    assert db.query(models.Case).count() == 1
    profile = db.query(models.UserProfile).filter_by(user_id="demo-user").first()
    assert profile.full_name == "Jane Smith"
    db.close()
