# services/backfill_source_metadata.py
"""
One-off migration + backfill: adds source/license columns to the existing
`cases` table (SQLAlchemy's create_all() only creates missing TABLES, not
missing COLUMNS on a table that already exists) and populates them from
docs/dataset_source_metadata.json (built from docs/dataset_license_audit.json
+ NCBI's esummary API — see docs/dataset.md for how that file was produced).

Idempotent: ALTER TABLE ADD COLUMN is skipped for columns that already
exist; the backfill UPDATE always re-applies (safe to re-run).

Usage:
    cd medcase-backend
    python3 -m services.backfill_source_metadata
"""
import json
import logging
import os

from sqlalchemy import text

from services.database import SessionLocal, engine
from services.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

METADATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs", "dataset_source_metadata.json")
)

NEW_COLUMNS = {
    "source_title": "VARCHAR",
    "source_url": "VARCHAR",
    "source_doi": "VARCHAR",
    "source_authors": "TEXT",
    "source_year": "INTEGER",
    "license_name": "VARCHAR",
    "license_url": "VARCHAR",
    "citation_text": "TEXT",
}


def ensure_columns():
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(cases)"))}
        for name, sql_type in NEW_COLUMNS.items():
            if name in existing:
                continue
            conn.execute(text(f"ALTER TABLE cases ADD COLUMN {name} {sql_type}"))
            logger.info("Added column cases.%s", name)
        conn.commit()


def backfill():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    db = SessionLocal()
    updated = 0
    missing = []
    try:
        for r in records:
            result = db.execute(
                text("""
                    UPDATE cases SET
                        source_title = :source_title,
                        source_url = :source_url,
                        source_doi = :source_doi,
                        source_authors = :source_authors,
                        source_year = :source_year,
                        license_name = :license_name,
                        license_url = :license_url,
                        citation_text = :citation_text
                    WHERE id = :case_id
                """),
                {
                    "source_title": r["source_title"],
                    "source_url": r["source_url"],
                    "source_doi": r["source_doi"],
                    "source_authors": r["source_authors"],
                    "source_year": r["source_year"],
                    "license_name": r["license_name"],
                    "license_url": r["license_url"],
                    "citation_text": r["citation_text"],
                    "case_id": r["case_id"],
                },
            )
            if result.rowcount == 0:
                missing.append(r["case_id"])
            else:
                updated += 1
        db.commit()
    finally:
        db.close()

    logger.info("Backfilled source/license metadata for %d cases.", updated)
    if missing:
        logger.warning("No matching case row for %d case_ids: %s", len(missing), missing[:10])


if __name__ == "__main__":
    ensure_columns()
    backfill()
