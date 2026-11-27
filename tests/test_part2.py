"""Run the real Part 2 SQL against PostgreSQL, with independent expected results."""
from datetime import date, datetime, time, timezone
from decimal import Decimal
from io import StringIO

import pytest
from sqlalchemy import text

from part1.integrity import replace_paper_authors, save_paper, save_review, save_session
from part1.setup import ROOT, TABLES
from part2 import demo
from part2.operations import BY_NUMBER, OPERATIONS, SCHEDULE_QUERY
from part2.reporting import Reporter
from part2.state import snapshot
from part2.view import create_view

COUNTS = dict(zip(TABLES, [10, 8, 8, 3, 3, 3, 3, 3, 3, 2, 10, 10, 11, 11, 10]))


def execute(conn, number, **parameters):
    operation = BY_NUMBER[number]
    return [dict(row) for row in conn.execute(text(operation.sql), operation.parameters | parameters).mappings()]


def values(rows, *columns):
    return [tuple(row[column] for column in columns) for row in rows]


def counts(rows):
    return {r["table_name"]: r["row_count"] for r in rows}


def engine_snapshot(engine):
    with engine.connect() as connection:
        return snapshot(connection)


def object_ids(engine):
    with engine.connect() as conn:
        return list(conn.execute(text("""
            SELECT c.relname, c.oid FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'csci341_part1' ORDER BY c.relname
        """)))


def test_tasks_1_2_create_insert_counts_and_preserve_original_objects(engine):
    before, oids = engine_snapshot(engine), object_ids(engine)
    reports = demo.demonstrate_setup(engine, Reporter(StringIO()))
    assert counts(reports["1"]) == {name: 0 for name in TABLES}
    assert counts(reports["2"]) == COUNTS
    assert engine_snapshot(engine) == before
    assert object_ids(engine) == oids


def test_tasks_1_2_mismatched_seed_rolls_back_everything(engine, tmp_path, monkeypatch):
    before, oids = engine_snapshot(engine), object_ids(engine)
    sql = tmp_path / "sql"
    sql.mkdir()
    (sql / "schema.sql").write_text((ROOT / "sql/schema.sql").read_text(encoding="utf-8"), encoding="utf-8")
    (sql / "seed.sql").write_text((ROOT / "sql/seed.sql").read_text(encoding="utf-8") + "\nUPDATE app_user SET phone_number = 'different' WHERE user_id = 1;", encoding="utf-8")
    monkeypatch.setattr(demo, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="differ from the original seed"):
        demo.demonstrate_setup(engine, Reporter(StringIO()))
    assert engine_snapshot(engine) == before
    assert object_ids(engine) == oids


@pytest.mark.parametrize("number", ["3.1", "3.2", "4.1", "4.2"])
def test_each_mutation_before_after_expected_rows_and_rollback(engine, number):
    original = engine_snapshot(engine)
    output = StringIO()
    report = demo.demonstrate_operation(engine, BY_NUMBER[number], Reporter(output))
    assert engine_snapshot(engine) == original
    assert "Before" in output.getvalue() and "After" in output.getvalue()
    assert f"ROLLBACK task {number}" in output.getvalue()
    if number == "3.1":
        assert values(report["before"], "user_id", "email", "phone_number") == [(1, "arman.armanov@example.com", "+77010000001")]
        assert values(report["after"], "user_id", "email", "phone_number") == [(1, "arman.armanov@example.com", "+77773414141")]
        assert report["result"] == report["after"]
        assert "%(phone_number)s" in output.getvalue()
        assert "Bound parameters: {'phone_number': '+77773414141', 'email': 'arman.armanov@example.com'}" in output.getvalue()
    elif number == "3.2":
        assert values(report["before"], "conference_id", "review_deadline") == [(1, date(2026, 11, 15)), (2, date(2026, 11, 17)), (3, date(2026, 11, 19))]
        assert values(report["after"], "conference_id", "review_deadline") == [(1, date(2026, 11, 22)), (2, date(2026, 11, 20)), (3, date(2026, 11, 26))]
        assert report["result"] == report["after"]
    elif number == "4.1":
        assert values(report["result"], "paper_id") == [(6,), (7,)]
        assert values(report["after"], "paper_id") == [(p,) for p in [1, 2, 3, 4, 5, 8, 9, 10]]
        assert counts(report["counts_before"]) == COUNTS
        expected = COUNTS | {"paper": 8, "paper_author": 9, "paper_keyword": 8, "paper_version": 9, "review": 8}
        assert counts(report["counts_after"]) == expected
    else:
        assert values(report["before"], "session_id", "paper_count") == [(1, 1), (2, 0)]
        assert values(report["result"], "session_id") == [(2,)]
        assert values(report["after"], "session_id", "paper_count") == [(1, 1)]
        assert counts(report["counts_after"]) == COUNTS | {"conference_session": 1}


def test_task_3_1_uses_bound_email_not_name(conn):
    conn.execute(text("UPDATE app_user SET given_name = 'Arman', surname = 'Armanov' WHERE user_id = 3"))
    assert values(execute(conn, "3.1"), "user_id") == [(1,)]
    assert conn.execute(text("SELECT phone_number FROM app_user WHERE user_id = 3")).scalar_one() == "+77010000003"
    assert execute(conn, "3.1", email="' OR TRUE --") == []


def test_task_4_1_requires_status_and_corresponding_authorship(conn):
    replace_paper_authors(conn, 7, [
        {"author_id": 2, "author_position": 1, "is_corresponding": False},
        {"author_id": 3, "author_position": 2, "is_corresponding": True},
    ])
    replace_paper_authors(conn, 5, [{"author_id": 2, "author_position": 1, "is_corresponding": True}])
    assert values(execute(conn, "4.1"), "paper_id") == [(6,)]
    assert list(conn.execute(text("SELECT paper_id FROM paper WHERE paper_id IN (5, 7) ORDER BY paper_id")).scalars()) == [5, 7]


def test_task_4_2_keeps_empty_non_astana_and_nonempty_astana_sessions(conn):
    save_session(conn, session_id=90, conference_id=2, title="Empty Almaty", session_date=date(2026, 12, 15), start_time=time(9), end_time=time(10), room_label="A", chair_id=2)
    assert values(execute(conn, "4.2"), "session_id") == [(2,)]
    assert list(conn.execute(text("SELECT session_id FROM conference_session ORDER BY session_id")).scalars()) == [1, 90]
    assert conn.execute(text("SELECT count(*) FROM conference")).scalar_one() == 3


def test_task_5_1_exact_accepted_papers_and_corresponding_authors(conn):
    rows = execute(conn, "5.1")
    assert values(rows, "paper_id", "title", "corresponding_author_name", "corresponding_author_email", "track_name", "conference_id", "acronym") == [
        (1, "Learning Query Plans", "Arman Armanov", "arman.armanov@example.com", "Data Systems", 1, "SDC26"),
        (2, "Reliable Indexes", "Dana Sarsenova", "dana.sarsenova@example.com", "Data Systems", 1, "SDC26"),
        (8, "Learning for Agriculture", "Aliya Nurgali", "aliya.nurgali@example.com", "Applied Computing", 2, "ACC26"),
    ]


def test_task_5_2_case_insensitive_phrase_in_abstract(conn):
    assert execute(conn, "5.2") == [
        {"paper_id": 1, "title": "Learning Query Plans"},
        {"paper_id": 8, "title": "Learning for Agriculture"},
    ]
    save_paper(conn, paper_id=5, title="machine learning in title only")
    assert values(execute(conn, "5.2"), "paper_id") == [(1,), (8,)]
    assert execute(conn, "5.2", pattern="%' OR TRUE --") == []


def test_task_5_3_versions_dates_paths_and_descending_order(conn):
    assert values(execute(conn, "5.3"), "version_no", "file_location", "uploaded_at") == [
        (3, "papers/1/v3.pdf", datetime(2026, 9, 15, 9, tzinfo=timezone.utc)),
        (1, "papers/1/v1.pdf", datetime(2026, 9, 1, 9, tzinfo=timezone.utc)),
    ]
    assert values(execute(conn, "5.3", paper_id=2), "version_no") == [(1,)]


def test_task_5_4_pool_expertise_experience_and_one_row_per_reviewer(conn):
    assert execute(conn, "5.4") == [{"reviewer_id": 9, "full_name": "Timur Karimov", "email": "timur.karimov@example.com"}]
    conn.execute(text("INSERT INTO reviewer_expertise VALUES (9, 'Networks'), (10, 'Databases')"))
    conn.execute(text("INSERT INTO conference_reviewer VALUES (1, 10)"))
    conn.execute(text("UPDATE reviewer SET years_experience = 2 WHERE reviewer_id = 10"))
    assert values(execute(conn, "5.4"), "reviewer_id") == [(9,)]
    conn.execute(text("UPDATE reviewer SET years_experience = 3 WHERE reviewer_id = 10"))
    assert values(execute(conn, "5.4"), "reviewer_id") == [(9,), (10,)]
    assert values(execute(conn, "5.4", conference_id=2), "reviewer_id") == [(2,)]


def test_task_6_1_distinct_counts_and_empty_track(conn):
    assert execute(conn, "6.1") == [
        {"track_id": 1, "track_name": "Data Systems", "conference_id": 1, "paper_count": 7, "author_count": 6},
        {"track_id": 2, "track_name": "Applied Computing", "conference_id": 2, "paper_count": 3, "author_count": 3},
        {"track_id": 3, "track_name": "Future Networks", "conference_id": 3, "paper_count": 0, "author_count": 0},
    ]


def test_task_6_2_zero_reviews_null_average_and_review_scores(conn):
    rows = execute(conn, "6.2")
    assert values(rows, "reviewer_id", "full_name", "review_count") == [(2, "Amina Aminova", 4), (9, "Timur Karimov", 6), (10, "Zhanna Iskakova", 0)]
    assert rows[0]["average_score"] == Decimal("3.5")
    assert rows[1]["average_score"] == pytest.approx(Decimal(17) / 6)
    assert rows[2]["average_score"] is None


def test_task_6_3_counts_review_weighted_average_and_empty_conference(conn):
    rows = execute(conn, "6.3")
    assert values(rows, "conference_id", "acronym", "paper_count", "accepted_count") == [(1, "SDC26", 7, 2), (2, "ACC26", 3, 1), (3, "SNC26", 0, 0)]
    assert rows[0]["average_score"] == Decimal(3)
    assert rows[1]["average_score"] == pytest.approx(Decimal(10) / 3)
    assert rows[2]["average_score"] is None


def test_aggregates_do_not_multiply_labels_versions_authors_or_deduplicate_scores(conn):
    baseline = {n: execute(conn, n) for n in ["6.1", "6.2", "6.3", "6.4", "7"]}
    conn.execute(text("INSERT INTO paper_keyword VALUES (1, 'extra'), (1, 'another')"))
    conn.execute(text("INSERT INTO paper_version VALUES (1, 9, 'v9.pdf', '2026-09-20 09:00+00', NULL)"))
    for n, expected in baseline.items():
        assert execute(conn, n) == expected
    save_review(conn, review_id=90, paper_id=2, reviewer_id=2, overall_score=4, recommendation="accept", comments_for_authors="Another independent score of four.", review_submission_date=date(2026, 10, 20))
    rows = execute(conn, "6.3")
    assert (rows[0]["paper_count"], rows[0]["accepted_count"], rows[0]["average_score"]) == (7, 2, Decimal("3.125"))


def test_task_6_4_average_includes_zero_reviewers(conn):
    rows = execute(conn, "6.4")
    assert values(rows, "reviewer_id", "full_name", "review_count") == [(2, "Amina Aminova", 4), (9, "Timur Karimov", 6)]
    assert all(r["overall_average"] == pytest.approx(Decimal(10) / 3) for r in rows)


def test_task_6_4_strictly_greater_than_average(conn):
    for rid, pid in [(90, 5), (91, 6)]:
        save_review(conn, review_id=rid, paper_id=pid, reviewer_id=10, overall_score=4, recommendation="accept", comments_for_authors="Complete test review.", review_submission_date=date(2026, 10, 20))
    assert execute(conn, "6.4") == [{"reviewer_id": 9, "full_name": "Timur Karimov", "review_count": 6, "overall_average": Decimal(4)}]


def test_task_7_decided_denominator_two_decimal_rounding_and_null(conn):
    assert execute(conn, "7") == [
        {"conference_id": 1, "acronym": "SDC26", "accepted_count": 2, "rejected_count": 1, "acceptance_rate": Decimal("66.67")},
        {"conference_id": 2, "acronym": "ACC26", "accepted_count": 1, "rejected_count": 1, "acceptance_rate": Decimal("50.00")},
        {"conference_id": 3, "acronym": "SNC26", "accepted_count": 0, "rejected_count": 0, "acceptance_rate": None},
    ]
    save_paper(conn, paper_id=5, track_id=3)
    assert execute(conn, "7")[2]["acceptance_rate"] is None  # Populated but no decisions.


def schedule(conn):
    return [dict(r) for r in conn.execute(text(SCHEDULE_QUERY)).mappings()]


def test_task_8_real_view_exact_columns_and_seed_row(conn):
    create_view(conn)
    assert conn.execute(text("SELECT relkind FROM pg_class WHERE oid = 'csci341_part1.accepted_paper_schedule'::regclass")).scalar_one() == "v"
    assert schedule(conn) == [{
        "paper_id": 1, "paper_title": "Learning Query Plans", "conference_id": 1,
        "acronym": "SDC26", "track_name": "Data Systems", "session_id": 1,
        "session_title": "Data Systems Presentations", "session_date": date(2026, 12, 10),
        "start_time": time(9), "end_time": time(10), "room_label": "Room A",
        "chair_full_name": "Timur Karimov", "corresponding_author_name": "Arman Armanov",
        "corresponding_author_email": "arman.armanov@example.com",
    }]


def test_task_8_view_tracks_changes_through_existing_integrity_helpers(conn):
    create_view(conn)
    save_paper(conn, paper_id=2, session_id=1)
    assert values(schedule(conn), "paper_id") == [(1,), (2,)]
    replace_paper_authors(conn, 1, [
        {"author_id": 1, "author_position": 1, "is_corresponding": False},
        {"author_id": 3, "author_position": 2, "is_corresponding": True},
    ])
    save_session(conn, session_id=1, title="Updated session", room_label="Room C")
    assert schedule(conn)[0]["corresponding_author_name"] == "Dana Sarsenova"
    assert schedule(conn)[0]["session_title"] == "Updated session"
    assert schedule(conn)[0]["room_label"] == "Room C"
    save_paper(conn, paper_id=1, session_id=None)
    assert values(schedule(conn), "paper_id") == [(2,)]


def test_task_8_schedule_order_with_multiple_papers_sessions_conferences(conn):
    create_view(conn)
    save_session(conn, session_id=90, conference_id=2, title="Almaty", session_date=date(2026, 12, 15), start_time=time(8), end_time=time(9), room_label="A", chair_id=2)
    save_paper(conn, paper_id=2, session_id=2)
    save_paper(conn, paper_id=3, status="accepted", session_id=1)
    save_paper(conn, paper_id=8, session_id=90)
    assert values(schedule(conn), "paper_id", "session_id", "conference_id") == [(1, 1, 1), (3, 1, 1), (2, 2, 1), (8, 90, 2)]


def test_failed_demonstration_rolls_back_mutation(engine):
    class FailingReporter(Reporter):
        def execute(self, *args, **kwargs):
            if kwargs.get("caption") == "After":
                raise RuntimeError("Simulated output failure after the UPDATE")
            return super().execute(*args, **kwargs)

    before = engine_snapshot(engine)
    with pytest.raises(RuntimeError, match="Simulated"):
        demo.demonstrate_operation(engine, BY_NUMBER["3.1"], FailingReporter(StringIO()))
    assert engine_snapshot(engine) == before


def test_complete_demo_numbering_sql_parameters_results_repeatability(engine):
    before = engine_snapshot(engine)
    stream = StringIO()
    first = demo.run_demo(engine, Reporter(stream))
    second = demo.run_demo(engine, Reporter(StringIO()))
    assert first == second
    assert engine_snapshot(engine) == before
    expected = ["1", "2"] + [op.number for op in OPERATIONS] + ["8"]
    assert list(first) == expected
    transcript = stream.getvalue()
    positions = [transcript.index(f"=== Task {number}:") for number in expected]
    assert positions == sorted(positions)
    assert "SQL:" in transcript and "Bound parameters:" in transcript and "NULL" in transcript
    for operation in OPERATIONS:
        assert first[operation.number]["result"]
        assert f"ROLLBACK task {operation.number}:" in transcript
    assert first["8"][0]["paper_id"] == 1
