"""Run with python -m part1.setup [--reset]. No Part 2 demonstrations."""
import argparse
from pathlib import Path

from sqlalchemy import text

from .db import OWNER_MARKER, make_engine, verify_target

ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    "app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
    "conference", "conference_host", "conference_reviewer", "track",
    "conference_session", "paper", "paper_keyword", "paper_author", "paper_version", "review",
)


def initialize(engine, *, reset=False):
    """Atomically create/reseed only our marked schema in our dedicated database."""
    with engine.begin() as connection:
        verify_target(connection)
        existing = connection.execute(text("""
            SELECT obj_description(oid, 'pg_namespace') AS marker
            FROM pg_namespace WHERE nspname = 'csci341_part1'
        """)).first()
        if existing is not None:
            if existing.marker != OWNER_MARKER:
                raise ValueError("Existing schema lacks this project's ownership marker; reset refused.")
            if not reset:
                raise ValueError("Schema already exists. Use --reset to restore the original seed.")
            connection.exec_driver_sql("DROP SCHEMA csci341_part1 CASCADE")
        for filename in ("schema.sql", "seed.sql"):
            connection.exec_driver_sql((ROOT / "sql" / filename).read_text(encoding="utf-8"))
        return {
            table: connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one()
            for table in TABLES  # Fixed table names, never user-provided identifiers.
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Restore this project's owned schema and seed.")
    args = parser.parse_args()
    engine = make_engine()
    try:
        counts = initialize(engine, reset=args.reset)
        for table, count in counts.items():
            print(f"{table:24} {count:3}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
