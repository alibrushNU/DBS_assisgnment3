"""Run all numbered Part 2 tasks: python -m part2.demo."""
import argparse
import sys
from pathlib import Path

from part1.db import make_engine
from part1.setup import ROOT
from .operations import OPERATIONS, SCHEDULE_QUERY
from .reporting import Reporter
from .state import snapshot, table_counts, verify_owned_schema
from .view import create_view


def demonstrate_setup(engine, reporter):
    """Tasks 1–2 reuse the unchanged SQL scripts, then restore existing objects.

    PostgreSQL transactional DDL lets us demonstrate real creation/insertion
    without permanently rebuilding Part 1 or losing an existing view.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            verify_owned_schema(connection)
            original = snapshot(connection)
            reporter.heading("1", "Create all tables and constraints using the Part 1 script")
            reporter.line("BEGIN creation/insertion demonstration; all DDL and seed writes will roll back.")
            reporter.execute(connection, "DROP SCHEMA csci341_part1 CASCADE", caption="Temporarily clear the owned schema inside this transaction")
            reporter.execute(connection, (ROOT / "sql/schema.sql").read_text(encoding="utf-8"), script=True, caption="Execute existing sql/schema.sql")
            created = table_counts(connection, reporter, caption="Created tables (all empty)")
            reporter.heading("2", "Insert the original seed using the Part 1 script")
            reporter.execute(connection, (ROOT / "sql/seed.sql").read_text(encoding="utf-8"), script=True, caption="Execute existing sql/seed.sql")
            inserted = table_counts(connection, reporter)
            expected = snapshot(connection)
            if expected["tables"] != original["tables"]:
                raise ValueError("Current rows differ from the original seed. Restore with python -m part1.setup --reset, then rerun.")
        finally:
            transaction.rollback()
            reporter.line("ROLLBACK tasks 1–2: original schema objects, rows, sequences, and any view restored.")
    return {"1": created.rows, "2": inserted.rows}


def demonstrate_operation(engine, operation, reporter, parameters=None):
    """Each task uses a separate transaction and always rolls back, even on failure."""
    bound = operation.parameters | (parameters or {})
    report = {}
    reporter.heading(operation.number, operation.title)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            if operation.is_mutation:
                report["before"] = reporter.execute(connection, operation.before_after_sql, bound, caption="Before").rows
                if operation.number.startswith("4."):
                    report["counts_before"] = table_counts(connection, reporter, caption="Before: parent and dependent table counts").rows
            report["result"] = reporter.execute(connection, operation.sql, bound, caption="Mutation RETURNING rows" if operation.is_mutation else "Query result").rows
            if operation.is_mutation:
                report["after"] = reporter.execute(connection, operation.before_after_sql, bound, caption="After").rows
                if operation.number.startswith("4."):
                    report["counts_after"] = table_counts(connection, reporter, caption="After: parent and dependent table counts").rows
        finally:
            transaction.rollback()
            reporter.line(f"ROLLBACK task {operation.number}: original seed retained.")
    return report


def run_demo(engine, reporter=None):
    reporter = reporter if reporter is not None else Reporter()
    with engine.connect() as connection:
        verify_owned_schema(connection)
        original = snapshot(connection)
    reports = demonstrate_setup(engine, reporter)
    for operation in OPERATIONS:
        reports[operation.number] = demonstrate_operation(engine, operation, reporter)
    reporter.heading("8", "Create and query accepted_paper_schedule")
    with engine.begin() as connection:
        create_view(connection, reporter)
        reports["8"] = reporter.execute(connection, SCHEDULE_QUERY, caption="Schedule ordered by conference, date, time, session, paper").rows
        if snapshot(connection) != original:
            raise AssertionError("Part 2 changed the seed or identity sequences unexpectedly.")
    reporter.line("COMMIT task 8: view retained for export; all original table rows and sequences unchanged.")
    return reports


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, value):
        for stream in self.streams:
            stream.write(value)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Also save the complete SQL/parameter/result transcript as UTF-8.")
    args = parser.parse_args()
    engine = make_engine()
    try:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("w", encoding="utf-8") as output:
                run_demo(engine, Reporter(Tee(sys.stdout, output)))
        else:
            run_demo(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
