"""Explicit environment-based PostgreSQL configuration, separate from local demo guards."""
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

SCHEMA = "csci341_part1"
OWNER_MARKER = "DBS CSCI341 Assignment 3 Part 1 owned schema v1"
SQL_DIRECTORY = Path(__file__).resolve().parents[1] / "sql"


def environment_engine():
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise ValueError("DATABASE_URL is required; configure it through the environment.")
    try:
        url = make_url(raw)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        if url.drivername != "postgresql+psycopg" or not all((url.host, url.database, url.username, url.password)):
            raise ValueError
    except Exception:
        raise ValueError("DATABASE_URL must be a PostgreSQL URL with host, database, user, and password.") from None
    return create_engine(url, hide_parameters=True, pool_pre_ping=True, pool_size=5, max_overflow=5,
                         connect_args={"options": "-c search_path=csci341_part1,pg_catalog -c timezone=UTC", "connect_timeout": 5})


def schema_marker(connection):
    return connection.execute(text("""
        SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace
        WHERE nspname = :schema
    """), {"schema": SCHEMA}).first()


def check_schema(connection):
    row = schema_marker(connection)
    if row is None or row[0] != OWNER_MARKER:
        raise RuntimeError("The assignment schema is not initialized or has an unexpected ownership marker.")
    # Verifies both original tables and the Part 2 view without exposing data.
    for name in ("app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
                 "conference", "conference_host", "conference_reviewer", "track", "conference_session",
                 "paper", "paper_keyword", "paper_author", "paper_version", "review", "accepted_paper_schedule"):
        connection.execute(text(f'SELECT 1 FROM csci341_part1."{name}" LIMIT 0'))
