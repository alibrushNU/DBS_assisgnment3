"""Task 8 view installation; also runnable alone after a Part 1 reset."""
from pathlib import Path

from sqlalchemy import text

from part1.db import make_engine
from .state import verify_owned_schema

VIEW_SQL = (Path(__file__).resolve().parents[1] / "sql/accepted_paper_schedule.sql").read_text(encoding="utf-8")


def create_view(connection, reporter=None):
    verify_owned_schema(connection)
    if reporter is None:
        connection.execute(text(VIEW_SQL))
    else:
        reporter.execute(connection, VIEW_SQL, caption="Create or replace the live schedule view")


def main():
    engine = make_engine()
    try:
        with engine.begin() as connection:
            create_view(connection)
        print("Task 8: csci341_part1.accepted_paper_schedule created; table data unchanged.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
