"""Connections are deliberately restricted to this project's local database."""
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

SCHEMA = "csci341_part1"
OWNER_MARKER = "DBS CSCI341 Assignment 3 Part 1 owned schema v1"
_local = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
DEFAULT_URL = URL.create(
    "postgresql+psycopg", username="csci341_part1",
    password=os.environ.get("PART1_DB_PASSWORD", _local.get("PART1_DB_PASSWORD")),
    host="127.0.0.1", port=55431, database="csci341_a3_part1",
).render_as_string(hide_password=False)


def make_engine(url=None):
    target = make_url(url or os.environ.get("PART1_DATABASE_URL", DEFAULT_URL))
    if not (
        target.drivername == "postgresql+psycopg"
        and target.host in {"127.0.0.1", "localhost"}
        and target.port == 55431
        and target.database == "csci341_a3_part1"
        and target.username == "csci341_part1"
        and not target.query
    ):
        raise ValueError("Refusing a database outside the dedicated Part 1 local target.")
    if not target.password:
        raise ValueError("Set PART1_DB_PASSWORD in your local .env or environment, or provide PART1_DATABASE_URL.")
    return create_engine(
        target,
        connect_args={
            "options": "-c search_path=csci341_part1,pg_catalog -c timezone=UTC",
            "connect_timeout": 5,
        },
    )


def verify_target(connection):
    actual = connection.execute(text("SELECT current_database(), current_user")).one()
    if tuple(actual) != ("csci341_a3_part1", "csci341_part1"):
        raise ValueError("Refusing to change an unexpected database or role.")
