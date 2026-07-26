# case_selector/selector_agent.py
import json
import random
from datetime import date
from typing import Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from services import models
from .schemas import CaseOutput, CaseRubric, CaseSource


class CaseSelectorAgent:
    """
    Vaka verisini artık RAM'deki bir JSON kopyasından değil,
    doğrudan SQL (SQLite 'cases' tablosu) üzerinden çeker.
    """

    def select_random_case(self, db: Session, specialty: Optional[str] = None) -> Optional[Dict]:
        query = db.query(models.Case)
        if specialty:
            query = query.filter(models.Case.specialty == specialty)
        row = query.order_by(func.random()).first()
        if not row:
            if specialty:
                return {"error": f"'{specialty}' branşında vaka bulunamadı"}
            return {"error": "Veri yok"}
        return self._format_case(row)

    def get_case_by_id(self, db: Session, case_id: str) -> Optional[Dict]:
        row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not row:
            return None
        return self._format_case(row)

    def list_all(self, db: Session):
        return db.query(models.Case).all()

    def get_daily_case(self, db: Session, for_date: Optional[date] = None) -> Optional[Dict]:
        """
        Deterministically picks the same case for every user on the same
        calendar date (UTC) — video-roadmap item 4, "Günün Vakası". Seeding
        Python's RNG with the ISO date string means the pick is stable for
        a given day and a given case set, without needing to persist
        "today's case" anywhere: any request on the same date recomputes
        the identical answer. Deliberately picks from ALL cases, not
        specialty-scoped, matching the video's "one shared case per day".
        """
        case_ids = [row[0] for row in db.query(models.Case.id).order_by(models.Case.id).all()]
        if not case_ids:
            return None

        target_date = for_date or date.today()
        rng = random.Random(target_date.isoformat())
        daily_case_id = rng.choice(case_ids)

        return self.get_case_by_id(db, daily_case_id)

    def _format_case(self, row: models.Case) -> Dict:
        """
        SQL satırını Pydantic Schema ile doğrulayıp temizler.
        """
        assets = json.loads(row.assets_json or "{}")
        raw_rubric = json.loads(row.rubric_json or "{}")
        seed_questions = json.loads(row.seed_questions_json or "[]")

        # --- RESİM URL MANTIĞI ---
        image_url = None
        images = assets.get("images", [])

        if images:
            raw_img = images[0]

            if isinstance(raw_img, dict):
                raw_img = raw_img.get("file_path") or raw_img.get("file") or raw_img.get("url") or raw_img.get("src")

            if isinstance(raw_img, str):
                if raw_img.startswith("http"):
                    image_url = raw_img
                else:
                    image_url = f"http://127.0.0.1:8000/static/images/{raw_img}"

        source = None
        if row.license_name or row.citation_text:
            source = CaseSource(
                title=row.source_title,
                url=row.source_url,
                doi=row.source_doi,
                authors=row.source_authors,
                year=row.source_year,
                license_name=row.license_name,
                license_url=row.license_url,
                citation_text=row.citation_text,
            )

        case_obj = CaseOutput(
            id=row.id,
            title=row.title or "Unknown Case",
            specialty=row.specialty or "General",
            difficulty=row.difficulty or "Intermediate",
            narrative=row.narrative or "",
            image=image_url,
            rubric=CaseRubric(**raw_rubric),
            seed_questions=seed_questions,
            source=source,
        )

        return case_obj.model_dump()


# Singleton Instance
selector_agent = CaseSelectorAgent()
