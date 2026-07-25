# case_selector/selector_agent.py
import json
from typing import Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from services import models
from .schemas import CaseOutput, CaseRubric


class CaseSelectorAgent:
    """
    Vaka verisini artık RAM'deki bir JSON kopyasından değil,
    doğrudan SQL (SQLite 'cases' tablosu) üzerinden çeker.
    """

    def select_random_case(self, db: Session) -> Optional[Dict]:
        row = db.query(models.Case).order_by(func.random()).first()
        if not row:
            return {"error": "Veri yok"}
        return self._format_case(row)

    def get_case_by_id(self, db: Session, case_id: str) -> Optional[Dict]:
        row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not row:
            return None
        return self._format_case(row)

    def list_all(self, db: Session):
        return db.query(models.Case).all()

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

        case_obj = CaseOutput(
            id=row.id,
            title=row.title or "Unknown Case",
            specialty=row.specialty or "General",
            difficulty=row.difficulty or "Intermediate",
            narrative=row.narrative or "",
            image=image_url,
            rubric=CaseRubric(**raw_rubric),
            seed_questions=seed_questions,
        )

        return case_obj.model_dump()


# Singleton Instance
selector_agent = CaseSelectorAgent()
