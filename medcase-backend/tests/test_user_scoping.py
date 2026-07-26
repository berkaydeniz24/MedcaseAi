# tests/test_user_scoping.py
"""
Unit tests for the user_id scoping added to UserStats/CaseProgress
(services/db_service.py, services/models.py). Previously both tables had
no user_id at all -- a single global UserStats row and one CaseProgress
row per case_id shared by everyone. These tests lock in that two different
user_ids now get independent stats and independent per-case progress,
rather than silently colliding or violating the new unique constraints.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.database import Base
from services.db_service import DBService


def make_dbs():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    return DBService(db)


def test_update_stats_creates_separate_rows_per_user():
    dbs = make_dbs()
    dbs.update_stats(is_correct=True, user_id="alice")
    dbs.update_stats(is_correct=False, user_id="bob")
    dbs.update_stats(is_correct=True, user_id="alice")

    alice = dbs.get_stats(user_id="alice")
    bob = dbs.get_stats(user_id="bob")

    assert alice.total_correct == 2
    assert alice.total_wrong == 0
    assert bob.total_correct == 0
    assert bob.total_wrong == 1


def test_get_stats_defaults_to_demo_user():
    dbs = make_dbs()
    dbs.update_stats(is_correct=True)  # no user_id passed -> DEMO_USER_ID
    stats = dbs.get_stats()
    assert stats.total_correct == 1


def test_case_progress_is_independent_per_user_for_same_case():
    dbs = make_dbs()
    dbs.update_case_status("CASE_1", "solved", user_id="alice")
    dbs.update_case_status("CASE_1", "in_progress", user_id="bob")

    alice_progress = {p.case_id: p.status for p in dbs.get_all_case_statuses(user_id="alice")}
    bob_progress = {p.case_id: p.status for p in dbs.get_all_case_statuses(user_id="bob")}

    assert alice_progress == {"CASE_1": "solved"}
    assert bob_progress == {"CASE_1": "in_progress"}


def test_case_progress_does_not_downgrade_from_solved():
    dbs = make_dbs()
    dbs.update_case_status("CASE_1", "solved", user_id="alice")
    dbs.update_case_status("CASE_1", "in_progress", user_id="alice")  # e.g. re-opening the case

    progress = dbs.get_all_case_statuses(user_id="alice")
    assert progress[0].status == "solved"


def test_create_session_scopes_case_status_to_user():
    dbs = make_dbs()
    dbs.create_session("CASE_1", user_id="alice")

    alice_progress = dbs.get_all_case_statuses(user_id="alice")
    bob_progress = dbs.get_all_case_statuses(user_id="bob")

    assert len(alice_progress) == 1
    assert alice_progress[0].status == "in_progress"
    assert len(bob_progress) == 0
