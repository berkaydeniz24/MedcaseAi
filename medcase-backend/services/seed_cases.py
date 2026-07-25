# services/seed_cases.py
import json
import os

from sqlalchemy.orm import Session

from . import models


def seed_cases_if_empty(db: Session) -> None:
    """
    data/cases_subset.json içeriğini 'cases' tablosuna aktarır.
    Tablo zaten doluysa hiçbir şey yapmaz (idempotent seed).
    """
    if db.query(models.Case).first() is not None:
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(base_dir, "data", "cases_subset.json")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_cases = json.load(f)
    except Exception as e:
        print(f"❌ Case Seed Hatası: {e}")
        return

    for raw in raw_cases:
        db.add(models.Case(
            id=raw.get("id"),
            title=raw.get("title", "Unknown Case"),
            specialty=raw.get("specialty", "General"),
            difficulty=raw.get("difficulty", "Intermediate"),
            narrative=raw.get("narrative", ""),
            assets_json=json.dumps(raw.get("assets", {}), ensure_ascii=False),
            rubric_json=json.dumps(raw.get("rubric", {}), ensure_ascii=False),
            seed_questions_json=json.dumps(raw.get("seed_questions", []), ensure_ascii=False),
        ))

    db.commit()
    print(f"📚 Case Seed: {len(raw_cases)} vaka SQL veritabanına yüklendi.")
