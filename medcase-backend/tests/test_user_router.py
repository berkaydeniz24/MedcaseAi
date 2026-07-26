# tests/test_user_router.py
"""
Integration tests for routers/user_router.py (/user/stats, /user/progress,
/user/history) — pure DB read endpoints, no LLM involved, so no mocking
needed beyond the usual isolated in-memory SQLite pattern.
"""
from datetime import datetime, timedelta, timezone

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
    TestingSessionLocal = sessionmaker(bind=engine)
    yield TestingSessionLocal


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


# ---------- /user/stats ----------

def test_stats_empty_db_returns_zeros(client):
    resp = client.get("/user/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_correct"] == 0
    assert data["total_wrong"] == 0
    assert len(data["weekly_activity"]) == 7


def test_stats_reflects_user_stats_row(client, db_session):
    seed(db_session, models.UserStats(total_correct=3, total_wrong=2))
    data = client.get("/user/stats").json()
    assert data["total_correct"] == 3
    assert data["total_wrong"] == 2


def test_weekly_activity_counts_sessions_by_real_date(client, db_session):
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    eight_days_ago = today - timedelta(days=8)

    seed(
        db_session,
        models.ChatSession(session_id="s1", case_id="C1", created_at=today),
        models.ChatSession(session_id="s2", case_id="C1", created_at=today),
        # Outside the 7-day window entirely — must not be counted anywhere.
        models.ChatSession(session_id="s3", case_id="C1", created_at=eight_days_ago),
    )

    data = client.get("/user/stats").json()
    total_in_window = sum(day["count"] for day in data["weekly_activity"])
    assert total_in_window == 2
    assert data["weekly_activity"][-1]["count"] == 2  # today is the last bucket
    assert data["weekly_activity"][-1]["date"] == today.date().isoformat()


# ---------- /user/progress ----------

def test_progress_includes_most_recent_session_id(client, db_session):
    older = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    newer = datetime.now(timezone.utc).replace(tzinfo=None)

    seed(
        db_session,
        models.CaseProgress(case_id="C1", status="in_progress"),
        models.ChatSession(session_id="old-session", case_id="C1", created_at=older),
        models.ChatSession(session_id="new-session", case_id="C1", created_at=newer),
    )

    data = client.get("/user/progress").json()
    entry = next(p for p in data if p["case_id"] == "C1")
    assert entry["session_id"] == "new-session"
    assert entry["status"] == "in_progress"


def test_progress_session_id_is_none_when_no_sessions_exist(client, db_session):
    seed(db_session, models.CaseProgress(case_id="C1", status="new"))
    data = client.get("/user/progress").json()
    entry = next(p for p in data if p["case_id"] == "C1")
    assert entry["session_id"] is None


# ---------- /user/history ----------

def test_history_skips_sessions_with_no_messages(client, db_session):
    seed(
        db_session,
        models.Case(id="C1", title="Test Case", specialty="Cardiology", narrative="N"),
        models.ChatSession(session_id="s1", case_id="C1"),
    )
    data = client.get("/user/history").json()
    assert data == []


def test_history_includes_status_specialty_and_answer_fields(client, db_session):
    seed(
        db_session,
        models.Case(id="C1", title="Test Case", specialty="Cardiology", narrative="N"),
        models.ChatSession(session_id="s1", case_id="C1", status="completed", hints_used=2),
        models.ChatMessage(session_id="s1", role="user", content="What's the diagnosis?"),
        models.CaseAnswer(
            session_id="s1", case_id="C1", user_id="demo-user",
            selected_index=1, correct_index=1, is_correct=True, response_time_ms=4200,
        ),
    )

    data = client.get("/user/history").json()
    assert len(data) == 1
    entry = data[0]
    assert entry["specialty"] == "Cardiology"
    assert entry["status"] == "completed"
    assert entry["is_correct"] is True
    assert entry["hints_used"] == 2
    assert entry["response_time_ms"] == 4200


def test_history_dedupes_to_latest_session_per_case(client, db_session):
    older = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    newer = datetime.now(timezone.utc).replace(tzinfo=None)

    seed(
        db_session,
        models.Case(id="C1", title="Test Case", specialty="Cardiology", narrative="N"),
        models.ChatSession(session_id="old-session", case_id="C1", created_at=older),
        models.ChatMessage(session_id="old-session", role="user", content="old message"),
        models.ChatSession(session_id="new-session", case_id="C1", created_at=newer),
        models.ChatMessage(session_id="new-session", role="user", content="new message"),
    )

    data = client.get("/user/history").json()
    assert len(data) == 1
    assert data[0]["session_id"] == "new-session"


def test_history_incomplete_session_has_null_answer_fields(client, db_session):
    seed(
        db_session,
        models.Case(id="C1", title="Test Case", specialty="Cardiology", narrative="N"),
        models.ChatSession(session_id="s1", case_id="C1", status="in_progress"),
        models.ChatMessage(session_id="s1", role="user", content="hello"),
    )

    data = client.get("/user/history").json()
    entry = data[0]
    assert entry["status"] == "in_progress"
    assert entry["is_correct"] is None
    assert entry["response_time_ms"] is None
    assert entry["hints_used"] == 0
