"""Read-only checks protecting the existing Part 1 database during demonstrations."""
from sqlalchemy import text

from part1.db import OWNER_MARKER, verify_target
from part1.setup import TABLES

SEQUENCES = (
    "app_user_user_id_seq", "conference_conference_id_seq", "track_track_id_seq",
    "conference_session_session_id_seq", "paper_paper_id_seq", "review_review_id_seq",
)


def verify_owned_schema(connection):
    verify_target(connection)
    marker = connection.execute(text("""
        SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace
        WHERE nspname = 'csci341_part1'
    """)).scalar_one_or_none()
    if marker != OWNER_MARKER:
        raise ValueError("Expected the owned Part 1 schema. Initialize it with python -m part1.setup.")


def snapshot(connection):
    # Identifiers come only from the existing Part 1 table list and fixed sequences.
    return {
        "tables": {
            name: [tuple(row) for row in connection.execute(text(
                f'SELECT * FROM csci341_part1."{name}" ORDER BY 1, 2'
            ))] for name in TABLES
        },
        "sequences": {
            name: tuple(connection.execute(text(
                f'SELECT last_value, is_called FROM csci341_part1."{name}"'
            )).one()) for name in SEQUENCES
        },
    }


def table_counts(connection, reporter, *, caption="Row counts for every table"):
    sql = "\nUNION ALL\n".join(
        f'SELECT :table_{i} AS table_name, count(*) AS row_count FROM csci341_part1."{name}"'
        for i, name in enumerate(TABLES)
    )
    return reporter.execute(connection, sql, {f"table_{i}": name for i, name in enumerate(TABLES)}, caption=caption)
