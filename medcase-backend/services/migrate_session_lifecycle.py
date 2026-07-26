# services/migrate_session_lifecycle.py
"""
Adds `status` and `completed_at` to the existing `chat_sessions` table.
The new `case_answers` table doesn't need this — models.Base.metadata.
create_all() (already called at startup in main.py) creates missing TABLES
fine; it just never adds missing COLUMNS to a table that already exists,
which is what this handles.

Idempotent — checks PRAGMA table_info before altering, safe to call on
every startup (same pattern as services/backfill_source_metadata.py).
"""
import logging

from sqlalchemy import text

from services.database import engine

logger = logging.getLogger(__name__)

NEW_COLUMNS = {
    "status": "VARCHAR DEFAULT 'in_progress'",
    "completed_at": "DATETIME",
}


def ensure_session_lifecycle_columns():
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(chat_sessions)"))}
        for name, sql_type in NEW_COLUMNS.items():
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE chat_sessions ADD COLUMN {name} {sql_type}"))
            logger.info("Added column chat_sessions.%s", name)
        conn.commit()


if __name__ == "__main__":
    ensure_session_lifecycle_columns()
