# tests/test_answer_api.py
"""
Integration tests for the answer/session-safety fixes in
routers/dialogue_router.py (docs/architecture.md §6, item 11). Uses an
isolated in-memory SQLite DB and mocks the Tutor/Dialogue LLM calls — these
tests exercise real HTTP + real SQL, but must never make real Gemini calls
(slow, costs money, and isn't what's being tested here: the persistence/
validation logic is pure Python+SQL).
"""
import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services import models
from services.database import Base, get_db
from routers import dialogue_router

TEST_CASE_ID = "TEST_CASE_1"
OTHER_CASE_ID = "TEST_CASE_2"


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    # case_answers/chat_sessions get their columns from the model definitions
    # directly here (fresh in-memory DB), so no manual ALTER TABLE needed —
    # that migration path is only for upgrading an existing production file.

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(dialogue_router.router, prefix="/dialogue")
    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    for cid in (TEST_CASE_ID, OTHER_CASE_ID):
        db.add(models.Case(id=cid, title="Test Case", specialty="Cardiology", narrative="Test narrative."))
    db.add(models.ChatSession(
        session_id="session-1", case_id=TEST_CASE_ID,
        mcq_data=json.dumps({
            "question": "What is the diagnosis?",
            "options": ["A", "B", "C", "D"],
            "correctIndex": 1,
            "rationale": "Because of the findings.",
        }),
        status="in_progress",
    ))
    db.commit()
    db.close()

    with patch("routers.dialogue_router.tutor_agent") as mock_tutor, \
         patch("routers.dialogue_router.dialogue_agent") as mock_dialogue:
        mock_tutor.run.return_value = type("T", (), {
            "answer": "mocked tutor feedback", "followups": [],
            "safety": {"medical": "educational_only", "note": "Not medical advice."},
            "meta": {},
        })()
        mock_dialogue.generate_response.return_value = type("D", (), {
            "answer": "mocked hint", "followups": [],
        })()
        with TestClient(app) as c:
            yield c


def test_submit_answer_persists_and_returns_result(client):
    resp = client.post("/dialogue/session-1/answer", json={"selectedIndex": 1, "mode": "explain"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["isCorrect"] is True
    assert data["correctIndex"] == 1
    assert data.get("already_answered") is None


def test_duplicate_submission_is_idempotent(client):
    first = client.post("/dialogue/session-1/answer", json={"selectedIndex": 1, "mode": "explain"})
    assert first.status_code == 200

    # Different selectedIndex on the "retry" — must NOT overwrite the stored answer.
    second = client.post("/dialogue/session-1/answer", json={"selectedIndex": 2, "mode": "explain"})
    assert second.status_code == 200
    data = second.json()
    assert data["already_answered"] is True
    assert data["selectedIndex"] == 1  # the ORIGINAL answer, not the resubmitted 2


def test_selected_index_out_of_range_is_rejected(client):
    resp = client.post("/dialogue/session-1/answer", json={"selectedIndex": 4, "mode": "explain"})
    assert resp.status_code == 422


def test_selected_index_negative_is_rejected(client):
    resp = client.post("/dialogue/session-1/answer", json={"selectedIndex": -1, "mode": "explain"})
    assert resp.status_code == 422


def test_missing_session_returns_404(client):
    resp = client.post("/dialogue/does-not-exist/answer", json={"selectedIndex": 0, "mode": "explain"})
    assert resp.status_code == 404


def test_corrupted_mcq_data_returns_422_not_silent_zero():
    """A session whose mcq_data is missing correctIndex entirely must be
    rejected with a controlled error, not silently graded against index 0.
    Seeded against its own isolated DB (separate from the `client` fixture's
    session-1) since the broken session needs to exist before the app is built."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(dialogue_router.router, prefix="/dialogue")
    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    db.add(models.Case(id=TEST_CASE_ID, title="Test", specialty="Cardiology", narrative="Narrative."))
    db.add(models.ChatSession(
        session_id="broken-session", case_id=TEST_CASE_ID,
        mcq_data=json.dumps({"question": "Q?", "options": ["A", "B", "C", "D"]}),  # no correctIndex
        status="in_progress",
    ))
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post("/dialogue/broken-session/answer", json={"selectedIndex": 0, "mode": "explain"})
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "MCQ_DATA_INVALID"


def test_session_case_mismatch_returns_409(client):
    resp = client.post(f"/dialogue/{OTHER_CASE_ID}/chat", json={
        "message": "hello", "mode": "hint", "session_id": "session-1",
    })
    assert resp.status_code == 409
    assert resp.json()["detail"]["error_code"] == "SESSION_CASE_MISMATCH"


def test_chat_with_matching_case_succeeds(client):
    resp = client.post(f"/dialogue/{TEST_CASE_ID}/chat", json={
        "message": "hello", "mode": "hint", "session_id": "session-1",
    })
    assert resp.status_code == 200
    assert resp.json()["answer"] == "mocked hint"


def test_tutor_agent_failure_falls_back_instead_of_500(client):
    """If TutorAgent.run() raises (e.g. the Gemini call itself fails),
    submit_answer must still grade the answer and return a graceful
    fallback message — not a 500, and not lose the already-computed
    isCorrect/correctIndex result."""
    with patch("routers.dialogue_router.tutor_agent") as mock_tutor:
        mock_tutor.run.side_effect = RuntimeError("Gemini call failed")
        resp = client.post("/dialogue/session-1/answer", json={"selectedIndex": 1, "mode": "explain"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["isCorrect"] is True
    assert "answer" in data["tutor"]
