from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from part1.integrity import (
    ValidationError, replace_paper_authors, save_paper, save_review, save_session, save_track,
)


def complete_review(**overrides):
    return dict(
        review_id=90, paper_id=5, reviewer_id=9, overall_score=4,
        recommendation="accept", comments_for_authors="A complete validation review.",
        review_submission_date=date(2026, 10, 20), **overrides,
    )


def test_valid_review_insert_and_update(conn):
    assert save_review(conn, **complete_review()) == 90
    save_review(conn, review_id=90, overall_score=5, confidential_comments="A useful result.")
    assert conn.execute(text("SELECT overall_score FROM review WHERE review_id = 90")).scalar_one() == 5


@pytest.mark.parametrize("change", [
    {"review_id": 90, "paper_id": 6, "reviewer_id": 2, "overall_score": 2, "recommendation": "reject", "comments_for_authors": "Self-review attempt", "review_submission_date": date(2026, 10, 20)},
    {"review_id": 6, "reviewer_id": 2},
    {"review_id": 2, "paper_id": 6},
])
def test_self_review_rejected_on_insert_and_both_update_directions(conn, change):
    before = list(conn.execute(text("SELECT * FROM review ORDER BY review_id")))
    with pytest.raises(ValidationError, match="authored"):
        save_review(conn, **change)
    assert list(conn.execute(text("SELECT * FROM review ORDER BY review_id"))) == before


def test_authorship_change_cannot_create_self_review(conn):
    before = list(conn.execute(text("SELECT * FROM paper_author WHERE paper_id = 1 ORDER BY author_position")))
    with pytest.raises(ValidationError, match="self-review"):
        replace_paper_authors(conn, 1, [
            {"author_id": 1, "author_position": 1, "is_corresponding": True},
            {"author_id": 2, "author_position": 2, "is_corresponding": False},
        ])
    assert list(conn.execute(text("SELECT * FROM paper_author WHERE paper_id = 1 ORDER BY author_position"))) == before


@pytest.mark.parametrize("authors", [
    [],
    [{"author_id": 1, "author_position": 1, "is_corresponding": False}],
    [{"author_id": 1, "author_position": 1, "is_corresponding": True}, {"author_id": 3, "author_position": 2, "is_corresponding": True}],
])
def test_optional_exactly_one_corresponding_author_rule(conn, authors):
    with pytest.raises(ValidationError, match="exactly one"):
        replace_paper_authors(conn, 1, authors)


def test_valid_authorship_replacement(conn):
    replace_paper_authors(conn, 1, [
        {"author_id": 3, "author_position": 1, "is_corresponding": True},
        {"author_id": 1, "author_position": 2, "is_corresponding": False},
    ])
    assert conn.execute(text("SELECT author_id FROM paper_author WHERE paper_id = 1 AND is_corresponding")).scalar_one() == 3


def test_failed_authorship_replacement_rolls_back_deleted_authors(conn):
    before = list(conn.execute(text("SELECT * FROM paper_author WHERE paper_id = 1 ORDER BY author_position")))
    with pytest.raises(IntegrityError):
        replace_paper_authors(conn, 1, [
            {"author_id": 1, "author_position": 1, "is_corresponding": True},
            {"author_id": 3, "author_position": 1, "is_corresponding": False},
        ])
    assert list(conn.execute(text("SELECT * FROM paper_author WHERE paper_id = 1 ORDER BY author_position"))) == before


@pytest.mark.parametrize("values", [
    {"paper_id": 3, "session_id": 1},  # Rejected paper.
    {"paper_id": 4, "session_id": 1},  # Under review.
    {"paper_id": 5, "session_id": 1},  # Submitted.
    {"paper_id": 6, "session_id": 1},  # Withdrawn.
    {"paper_id": 8, "session_id": 1},  # Accepted, different conference.
    {"paper_id": 1, "status": "withdrawn"},  # Scheduled paper changes status.
    {"paper_id": 1, "track_id": 2},  # Scheduled paper changes track.
    {"paper_id": 1, "session_id": 999},
    {"paper_id": 1, "track_id": 999},
    {"paper_id": 90, "track_id": 1, "status": "submitted", "session_id": 1, "title": "Invalid", "abstract": "Invalid assignment", "submission_date": date(2026, 9, 1)},
])
def test_invalid_paper_assignments_and_relevant_edits(conn, values):
    before = list(conn.execute(text("SELECT * FROM paper ORDER BY paper_id")))
    with pytest.raises(ValidationError):
        save_paper(conn, **values)
    assert list(conn.execute(text("SELECT * FROM paper ORDER BY paper_id"))) == before


def test_session_conference_change_cannot_invalidate_assigned_papers(conn):
    with pytest.raises(ValidationError, match="assigned paper"):
        save_session(conn, session_id=1, conference_id=2, chair_id=2)
    assert conn.execute(text("SELECT conference_id FROM conference_session WHERE session_id = 1")).scalar_one() == 1


def test_track_conference_change_cannot_invalidate_assigned_papers(conn):
    with pytest.raises(ValidationError, match="assigned paper"):
        save_track(conn, track_id=1, conference_id=2, coordinator_id=2)
    assert conn.execute(text("SELECT conference_id FROM track WHERE track_id = 1")).scalar_one() == 1


def test_valid_assignment_unassignment_and_empty_parent_moves(conn):
    save_paper(conn, paper_id=2, session_id=1)
    assert conn.execute(text("SELECT session_id FROM paper WHERE paper_id = 2")).scalar_one() == 1
    save_paper(conn, paper_id=1, session_id=2)
    save_paper(conn, paper_id=1, session_id=None, status="withdrawn", track_id=2)
    assert conn.execute(text("SELECT session_id FROM paper WHERE paper_id = 1")).scalar_one() is None
    save_session(conn, session_id=2, conference_id=2, chair_id=2)
    save_track(conn, track_id=3, conference_id=2, coordinator_id=2)


def test_related_changes_roll_back_together(conn):
    with pytest.raises(ValidationError):
        with conn.begin_nested():
            save_paper(conn, paper_id=2, title="Temporary change")
            save_paper(conn, paper_id=3, session_id=1)
    assert conn.execute(text("SELECT title FROM paper WHERE paper_id = 2")).scalar_one() == "Reliable Indexes"
