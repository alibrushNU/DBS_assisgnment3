from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from part1 import setup
from part1.db import DEFAULT_URL, OWNER_MARKER, make_engine


def snapshot(engine):
    with engine.connect() as connection:
        return {
            table: list(connection.execute(text(f'SELECT * FROM "{table}" ORDER BY 1, 2')))
            for table in setup.TABLES
        }


def test_repeatable_setup_and_owned_schema_scope(engine):
    setup.initialize(engine, reset=True)
    original = snapshot(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE public.part1_reset_probe (value integer)"))
        connection.execute(text("INSERT INTO public.part1_reset_probe VALUES (17)"))
    try:
        setup.initialize(engine, reset=True)
        assert snapshot(engine) == original
        with engine.connect() as connection:
            assert connection.execute(text("SELECT value FROM public.part1_reset_probe")).scalar_one() == 17
            assert connection.execute(text("SELECT last_value FROM app_user_user_id_seq")).scalar_one() == 10
            assert connection.execute(text("SELECT last_value FROM paper_paper_id_seq")).scalar_one() == 10
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE public.part1_reset_probe"))


def test_existing_schema_requires_explicit_reset(engine):
    with pytest.raises(ValueError, match="--reset"):
        setup.initialize(engine)


def test_unmarked_schema_cannot_be_reset(engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("COMMENT ON SCHEMA csci341_part1 IS NULL")
    try:
        with pytest.raises(ValueError, match="ownership marker"):
            setup.initialize(engine, reset=True)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"COMMENT ON SCHEMA csci341_part1 IS '{OWNER_MARKER}'")


def test_failed_seed_rolls_back_schema_reset(engine, tmp_path, monkeypatch):
    original = snapshot(engine)
    sql = tmp_path / "sql"
    sql.mkdir()
    (sql / "schema.sql").write_text((setup.ROOT / "sql/schema.sql").read_text(encoding="utf-8"), encoding="utf-8")
    (sql / "seed.sql").write_text("INSERT INTO nonexistent_part1_table VALUES (1);", encoding="utf-8")
    monkeypatch.setattr(setup, "ROOT", Path(tmp_path))
    with pytest.raises(ProgrammingError):
        setup.initialize(engine, reset=True)
    assert snapshot(engine) == original


@pytest.mark.parametrize("target", [
    DEFAULT_URL.replace("55431", "5432"),
    DEFAULT_URL.replace("127.0.0.1", "remote.example.com"),
    DEFAULT_URL.replace("/csci341_a3_part1", "/postgres"),
    DEFAULT_URL.replace("//csci341_part1:", "//postgres:"),
    DEFAULT_URL + "?host=remote.example.com",
    "sqlite:///unrelated.db",
])
def test_refuse_other_targets_without_connecting(target):
    with pytest.raises(ValueError, match="dedicated"):
        make_engine(target)


def test_identity_sequences_allow_new_rows(conn):
    user_id = conn.execute(text("""
        INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
        VALUES ('Test', 'Identity', 'identity@example.com', 'Test Institute', 'Kazakhstan', '+77019999999')
        RETURNING user_id
    """)).scalar_one()
    assert user_id > 10
    review_id = conn.execute(text("""
        INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, review_submission_date)
        VALUES (5, 9, 3, 'accept', 'A complete review.', '2026-10-20') RETURNING review_id
    """)).scalar_one()
    assert review_id > 10
