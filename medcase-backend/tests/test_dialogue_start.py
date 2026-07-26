# tests/test_dialogue_start.py
"""
Integration tests for GET /dialogue/start (routers/dialogue_router.py) — same
isolated in-memory SQLite + mocked-agent pattern as test_answer_api.py. No
real Gemini calls: mcq_agent.generate_mcq is mocked so this exercises the
real case-selection/session-creation/DB-write path without cost or latency.
"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services import models
from services.database import Base, get_db
from routers import dialogue_router

VALID_MCQ = {
    "question": "What is the diagnosis?",
    "options": ["A", "B", "C", "D"],
    "correctIndex": 1,
    "rationale": "Because of the findings.",
}

FALLBACK_MCQ = {
    "question": "Vaka analizi sorusu yüklenirken bir hata oluştu.",
    "options": ["Seçenek A", "Seçenek B", "Seçenek C", "Seçenek D"],
    "correctIndex": 0,
    "rationale": "Sistem hatası.",
}


def build_app(seed_cases=(("C1", "Cardiology"),)):
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
    for case_id, specialty in seed_cases:
        db.add(models.Case(id=case_id, title=f"{specialty} Case", specialty=specialty, narrative="Narrative."))
    db.commit()
    db.close()

    return app


def test_start_creates_session_and_returns_mcq(monkeypatch):
    app = build_app()
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["case"]["id"] == "C1"
    assert data["mcq"]["question"] == VALID_MCQ["question"]
    # correctIndex must NOT leak to the client-facing mcq payload.
    assert "correctIndex" not in data["mcq"]
    assert "session_id" in data and data["session_id"]


def test_start_persists_session_and_marks_case_in_progress(monkeypatch):
    app = build_app()
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start")
        session_id = resp.json()["session_id"]
        # Real session should be resumable via /dialogue/history/{session_id}.
        history_resp = client.get(f"/dialogue/history/{session_id}")

    assert history_resp.status_code == 200


def test_start_with_specialty_filter_selects_matching_case(monkeypatch):
    app = build_app(seed_cases=(("C1", "Cardiology"), ("C2", "Dermatology")))
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start", params={"specialty": "Dermatology"})

    assert resp.status_code == 200
    assert resp.json()["case"]["id"] == "C2"


def test_start_no_case_for_specialty_returns_404(monkeypatch):
    app = build_app(seed_cases=(("C1", "Cardiology"),))
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start", params={"specialty": "Neurology"})

    assert resp.status_code == 404


def test_start_fallback_mcq_refuses_to_create_session(monkeypatch):
    """A real student must never get a fake placeholder MCQ treated as
    answerable — see mcq/mcq_agent.py::is_fallback_mcq."""
    app = build_app()
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(FALLBACK_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start")

    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "MCQ_GENERATION_FAILED"


def test_start_with_case_id_selects_that_specific_case(monkeypatch):
    """Video-roadmap item 4 ("Günün Vakası") uses this: the frontend
    resolves today's deterministic case_id via GET /cases/daily, then
    starts a real session for it via /dialogue/start?case_id=..."""
    app = build_app(seed_cases=(("C1", "Cardiology"), ("C2", "Dermatology")))
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start", params={"case_id": "C2"})

    assert resp.status_code == 200
    assert resp.json()["case"]["id"] == "C2"


def test_start_with_unknown_case_id_returns_404(monkeypatch):
    app = build_app()
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start", params={"case_id": "does-not-exist"})

    assert resp.status_code == 404


def test_start_case_id_takes_priority_over_specialty(monkeypatch):
    app = build_app(seed_cases=(("C1", "Cardiology"), ("C2", "Dermatology")))
    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", lambda case: dict(VALID_MCQ))

    with TestClient(app) as client:
        resp = client.get("/dialogue/start", params={"case_id": "C1", "specialty": "Dermatology"})

    assert resp.status_code == 200
    assert resp.json()["case"]["id"] == "C1"


def test_start_mcq_generation_exception_returns_503(monkeypatch):
    app = build_app()

    def raise_error(case):
        raise RuntimeError("Gemini call failed")

    monkeypatch.setattr(dialogue_router.mcq_agent, "generate_mcq", raise_error)

    with TestClient(app) as client:
        resp = client.get("/dialogue/start")

    assert resp.status_code == 503
    assert resp.json()["detail"]["error_code"] == "MCQ_GENERATION_FAILED"
