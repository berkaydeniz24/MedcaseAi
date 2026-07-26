# tests/test_case_selector.py
"""
Unit tests for case_selector/selector_agent.py — the service layer that
GET /cases and GET /cases/{case_id} (main.py) delegate to. main.py's routes
aren't tested directly at the HTTP layer: main.py isn't a clean APIRouter,
importing it runs real module-level side effects (DB engine creation bound
to the real medcase.db, migrations, seeding, real agent instantiation) that
would couple this test suite to on-disk state rather than an isolated DB.
Testing CaseSelectorAgent directly covers the actual logic those routes run
without any of that.
"""
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services import models
from services.database import Base
from case_selector.selector_agent import CaseSelectorAgent


def make_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_get_case_by_id_returns_formatted_case():
    db = make_session()
    db.add(models.Case(id="C1", title="Test Case", specialty="Cardiology", narrative="Chest pain."))
    db.commit()

    agent = CaseSelectorAgent()
    case = agent.get_case_by_id(db, "C1")

    assert case["id"] == "C1"
    assert case["specialty"] == "Cardiology"
    assert case["narrative"] == "Chest pain."
    # Defaults from CaseOutput/CaseRubric should be present, not missing keys.
    assert case["rubric"]["chief_complaint"] == ""
    assert case["seed_questions"] == []


def test_get_case_by_id_missing_returns_none():
    db = make_session()
    agent = CaseSelectorAgent()
    assert agent.get_case_by_id(db, "does-not-exist") is None


def test_select_random_case_filters_by_specialty():
    db = make_session()
    db.add(models.Case(id="C1", title="Cardio Case", specialty="Cardiology", narrative="N1"))
    db.add(models.Case(id="C2", title="Derm Case", specialty="Dermatology", narrative="N2"))
    db.commit()

    agent = CaseSelectorAgent()
    result = agent.select_random_case(db, specialty="Dermatology")

    assert result["id"] == "C2"


def test_select_random_case_no_match_returns_error():
    db = make_session()
    db.add(models.Case(id="C1", title="Cardio Case", specialty="Cardiology", narrative="N1"))
    db.commit()

    agent = CaseSelectorAgent()
    result = agent.select_random_case(db, specialty="Neurology")

    assert "error" in result


def test_select_random_case_no_cases_at_all_returns_error():
    db = make_session()
    agent = CaseSelectorAgent()
    result = agent.select_random_case(db)
    assert "error" in result


def test_image_url_resolves_from_relative_path():
    db = make_session()
    db.add(models.Case(
        id="C1", title="Test", specialty="Cardiology", narrative="N",
        assets_json='{"images": [{"file_path": "scan.jpg"}]}',
    ))
    db.commit()

    agent = CaseSelectorAgent()
    case = agent.get_case_by_id(db, "C1")

    assert case["image"] == "http://127.0.0.1:8000/static/images/scan.jpg"


def test_daily_case_is_deterministic_for_same_date():
    db = make_session()
    for i in range(5):
        db.add(models.Case(id=f"C{i}", title=f"Case {i}", specialty="Cardiology", narrative=f"N{i}"))
    db.commit()

    agent = CaseSelectorAgent()
    d = date(2026, 7, 27)
    first = agent.get_daily_case(db, for_date=d)
    second = agent.get_daily_case(db, for_date=d)

    assert first["id"] == second["id"]


def test_daily_case_differs_across_dates_for_a_varied_set():
    # Not a strict guarantee for every possible pair of dates, but with 30
    # cases and 10 distinct dates it would be a real bug (not bad luck) if
    # every single date landed on the same case.
    db = make_session()
    for i in range(30):
        db.add(models.Case(id=f"C{i}", title=f"Case {i}", specialty="Cardiology", narrative=f"N{i}"))
    db.commit()

    agent = CaseSelectorAgent()
    picks = {agent.get_daily_case(db, for_date=date(2026, 7, d))["id"] for d in range(1, 11)}

    assert len(picks) > 1


def test_daily_case_no_cases_returns_none():
    db = make_session()
    agent = CaseSelectorAgent()
    assert agent.get_daily_case(db, for_date=date(2026, 7, 27)) is None


def test_source_populated_when_license_present():
    db = make_session()
    db.add(models.Case(
        id="C1", title="Test", specialty="Cardiology", narrative="N",
        license_name="CC BY", citation_text="Some Author. Some Title.",
    ))
    db.commit()

    agent = CaseSelectorAgent()
    case = agent.get_case_by_id(db, "C1")

    assert case["source"]["license_name"] == "CC BY"
    assert case["source"]["citation_text"] == "Some Author. Some Title."
