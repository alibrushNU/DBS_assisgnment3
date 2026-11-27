import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError


@pytest.mark.parametrize("statement, sqlstate", [
    ("UPDATE app_user SET email = 'arman.armanov@example.com' WHERE user_id = 2", "23505"),
    ("UPDATE app_user SET given_name = NULL WHERE user_id = 1", "23502"),
    ("UPDATE paper SET status = 'pending' WHERE paper_id = 2", "23514"),
    ("UPDATE paper SET status = NULL WHERE paper_id = 2", "23502"),
    ("UPDATE review SET overall_score = 0 WHERE review_id = 1", "23514"),
    ("UPDATE review SET overall_score = 6 WHERE review_id = 1", "23514"),
    ("UPDATE review SET overall_score = NULL WHERE review_id = 1", "23502"),
    ("UPDATE review SET recommendation = 'maybe' WHERE review_id = 1", "23514"),
    ("UPDATE review SET recommendation = NULL WHERE review_id = 1", "23502"),
    ("UPDATE review SET review_submission_date = NULL WHERE review_id = 1", "23502"),
    ("UPDATE review SET comments_for_authors = NULL WHERE review_id = 1", "23502"),
    ("UPDATE review SET comments_for_authors = '   ' WHERE review_id = 1", "23514"),
    ("UPDATE review SET reviewer_id = 9 WHERE review_id = 2", "23505"),
    ("UPDATE paper_author SET author_position = 0 WHERE paper_id = 1 AND author_id = 3", "23514"),
    ("UPDATE paper_author SET author_position = -1 WHERE paper_id = 1 AND author_id = 3", "23514"),
    ("UPDATE paper_author SET author_position = 1 WHERE paper_id = 1 AND author_id = 3", "23505"),
    ("UPDATE paper_author SET is_corresponding = true WHERE paper_id = 1 AND author_id = 3", "23505"),
    ("UPDATE paper_version SET version_no = 0 WHERE paper_id = 1 AND version_no = 3", "23514"),
    ("UPDATE paper_version SET version_no = -1 WHERE paper_id = 1 AND version_no = 3", "23514"),
    ("UPDATE paper_version SET version_no = 1 WHERE paper_id = 1 AND version_no = 3", "23505"),
    ("UPDATE reviewer SET years_experience = -1 WHERE reviewer_id = 9", "23514"),
    ("UPDATE conference SET end_date = start_date - 1 WHERE conference_id = 1", "23514"),
    ("UPDATE conference_session SET end_time = start_time WHERE session_id = 1", "23514"),
    ("UPDATE conference_session SET end_time = start_time - interval '1 hour' WHERE session_id = 1", "23514"),
    ("UPDATE paper SET track_id = 999 WHERE paper_id = 1", "23503"),
    ("UPDATE paper SET session_id = 999 WHERE paper_id = 1", "23503"),
    ("UPDATE paper_author SET author_id = 9 WHERE paper_id = 2", "23503"),
    ("UPDATE review SET reviewer_id = 1 WHERE review_id = 1", "23503"),
    ("UPDATE paper_version SET paper_id = 999 WHERE paper_id = 2", "23503"),
    ("UPDATE track SET coordinator_id = 2 WHERE track_id = 1", "23503"),
    ("UPDATE conference_session SET chair_id = 2 WHERE session_id = 1", "23503"),
    ("DELETE FROM conference_reviewer WHERE conference_id = 1 AND reviewer_id = 9", "23503"),
    ("DELETE FROM track WHERE track_id = 1", "23503"),
    ("DELETE FROM reviewer WHERE reviewer_id = 9", "23503"),
    ("DELETE FROM author WHERE author_id = 1", "23503"),
])
def test_database_rejects_invalid_rows(conn, statement, sqlstate):
    with pytest.raises(IntegrityError) as caught:
        with conn.begin_nested():
            conn.execute(text(statement))
    assert caught.value.orig.sqlstate == sqlstate


def test_declared_types_nullability_and_keys(conn):
    inspector = inspect(conn)
    assert inspector.get_pk_constraint("paper_version")["constrained_columns"] == ["paper_id", "version_no"]
    assert inspector.get_pk_constraint("paper_author")["constrained_columns"] == ["paper_id", "author_id"]
    nullable = {"author": {"orcid"}, "paper": {"session_id"}, "paper_version": {"change_note"}, "review": {"confidential_comments"}}
    for table in inspector.get_table_names(schema="csci341_part1"):
        assert {c["name"] for c in inspector.get_columns(table) if c["nullable"]} == nullable.get(table, set())
    for table, column in [("review", "overall_score"), ("reviewer", "years_experience"), ("paper_author", "author_position"), ("paper_version", "version_no")]:
        assert str(next(c["type"] for c in inspector.get_columns(table) if c["name"] == column)) == "INTEGER"
    assert len(inspector.get_table_names(schema="csci341_part1")) == 15  # The Part 2 view adds no table.


def test_all_reference_foreign_keys_exist(conn):
    expected = {
        "author": [("author_id", "app_user", "user_id")],
        "reviewer": [("reviewer_id", "app_user", "user_id")],
        "author_research_area": [("author_id", "author", "author_id")],
        "reviewer_expertise": [("reviewer_id", "reviewer", "reviewer_id")],
        "conference_host": [("conference_id", "conference", "conference_id")],
        "conference_reviewer": [("conference_id", "conference", "conference_id"), ("reviewer_id", "reviewer", "reviewer_id")],
        "track": [("conference_id", "conference", "conference_id"), ("coordinator_id", "reviewer", "reviewer_id")],
        "conference_session": [("conference_id", "conference", "conference_id"), ("chair_id", "reviewer", "reviewer_id")],
        "paper": [("track_id", "track", "track_id"), ("session_id", "conference_session", "session_id")],
        "paper_keyword": [("paper_id", "paper", "paper_id")],
        "paper_author": [("paper_id", "paper", "paper_id"), ("author_id", "author", "author_id")],
        "paper_version": [("paper_id", "paper", "paper_id")],
        "review": [("paper_id", "paper", "paper_id"), ("reviewer_id", "reviewer", "reviewer_id")],
    }
    for table, keys in expected.items():
        actual = {(f["constrained_columns"][0], f["referred_table"], f["referred_columns"][0]) for f in inspect(conn).get_foreign_keys(table) if len(f["constrained_columns"]) == 1}
        assert set(keys) <= actual


@pytest.mark.parametrize("paper_id", [1, 6, 7])
def test_paper_delete_cascades_and_preserves_parents(conn, paper_id):
    conn.execute(text("DELETE FROM paper WHERE paper_id = :id"), {"id": paper_id})
    for table in ("paper_author", "paper_keyword", "paper_version", "review"):
        assert conn.execute(text(f"SELECT count(*) FROM {table} WHERE paper_id = :id"), {"id": paper_id}).scalar_one() == 0
    for table, expected in [("paper", 9), ("app_user", 10), ("author", 8), ("reviewer", 3), ("track", 3), ("conference", 3)]:
        assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == expected


def test_session_delete_unassigns_without_deleting_paper(conn):
    conn.execute(text("DELETE FROM conference_session WHERE session_id = 1"))
    assert conn.execute(text("SELECT session_id FROM paper WHERE paper_id = 1")).scalar_one() is None
    assert conn.execute(text("SELECT count(*) FROM paper")).scalar_one() == 10


def test_remove_empty_conference_keeps_independent_reviewers(conn):
    conn.execute(text("DELETE FROM track WHERE track_id = 3"))
    conn.execute(text("DELETE FROM conference WHERE conference_id = 3"))
    assert conn.execute(text("SELECT count(*) FROM conference_host WHERE conference_id = 3")).scalar_one() == 0
    assert conn.execute(text("SELECT count(*) FROM conference_reviewer WHERE conference_id = 3")).scalar_one() == 0
    assert conn.execute(text("SELECT count(*) FROM reviewer")).scalar_one() == 3
    assert conn.execute(text("SELECT count(*) FROM app_user")).scalar_one() == 10


def test_valid_boundaries_and_optional_nulls(conn):
    conn.execute(text("UPDATE conference SET end_date = start_date WHERE conference_id = 1"))
    conn.execute(text("UPDATE reviewer SET years_experience = 0 WHERE reviewer_id = 9"))
    conn.execute(text("UPDATE review SET overall_score = 1, confidential_comments = NULL WHERE review_id = 1"))
    conn.execute(text("UPDATE review SET overall_score = 5 WHERE review_id = 2"))
    conn.execute(text("INSERT INTO paper_version VALUES (1, 9, 'papers/1/v9.pdf', '2026-09-20 09:00+00', NULL)"))
    assert conn.execute(text("SELECT max(version_no) FROM paper_version WHERE paper_id = 1")).scalar_one() == 9
