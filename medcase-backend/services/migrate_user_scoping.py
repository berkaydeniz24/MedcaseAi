# services/migrate_user_scoping.py
"""
Adds `user_id` to the existing `user_stats` and `case_progress` tables.
Previously both were single-global-row(s)-for-everyone tables with no user
scoping at all — `CaseAnswer.user_id` already defaulted to "demo-user" (no
real auth yet), but `UserStats`/`CaseProgress` didn't, so every user shared
one stats row and one progress row per case.

Idempotent, same pattern as migrate_session_lifecycle.py: checks
PRAGMA table_info before altering, safe to call on every startup.

`case_progress` additionally had a UNIQUE index on `case_id` alone
(`ix_case_progress_case_id`) — that would block a second user from ever
having their own progress row for a case already seen by demo-user. This
drops that old index and replaces it with a composite UNIQUE on
(user_id, case_id), matching services/models.py's current
`UniqueConstraint`.
"""
import logging

from sqlalchemy import text

from services.database import engine

logger = logging.getLogger(__name__)

DEMO_USER_ID = "demo-user"


def _add_user_id_column(conn, table: str):
    existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
    if "user_id" in existing:
        return False
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR"))
    conn.execute(text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"), {"uid": DEMO_USER_ID})
    logger.info("Added column %s.user_id (backfilled existing rows to %r)", table, DEMO_USER_ID)
    return True


def ensure_user_scoping_columns():
    with engine.connect() as conn:
        _add_user_id_column(conn, "user_stats")
        case_progress_changed = _add_user_id_column(conn, "case_progress")

        indexes = {row[1] for row in conn.execute(text("PRAGMA index_list(case_progress)"))}
        if "ix_case_progress_case_id" in indexes:
            conn.execute(text("DROP INDEX ix_case_progress_case_id"))
            logger.info("Dropped old single-column unique index ix_case_progress_case_id")
            case_progress_changed = True

        if case_progress_changed:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_case_progress_user_case "
                "ON case_progress (user_id, case_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_case_progress_case_id ON case_progress (case_id)"
            ))
            logger.info("Ensured composite unique index on case_progress(user_id, case_id)")

        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_stats_user_id ON user_stats (user_id)"
        ))

        conn.commit()


if __name__ == "__main__":
    ensure_user_scoping_columns()
