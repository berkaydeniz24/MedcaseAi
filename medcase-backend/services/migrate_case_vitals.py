# services/migrate_case_vitals.py
"""
Adds `vitals_json` to the existing `cases` table (video-roadmap "vitals
kartı"). Same idempotent PRAGMA-table_info pattern as
migrate_session_lifecycle.py / migrate_user_scoping.py, safe to call on
every startup.
"""
import logging

from sqlalchemy import text

from services.database import engine

logger = logging.getLogger(__name__)


def ensure_case_vitals_column():
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(cases)"))}
        if "vitals_json" not in existing:
            conn.execute(text("ALTER TABLE cases ADD COLUMN vitals_json TEXT DEFAULT '{}'"))
            conn.execute(text("UPDATE cases SET vitals_json = '{}' WHERE vitals_json IS NULL"))
            logger.info("Added column cases.vitals_json")
        conn.commit()


if __name__ == "__main__":
    ensure_case_vitals_column()
