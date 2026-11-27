"""Print the DBAPI SQL and bound values actually sent by SQLAlchemy."""
import sys
from dataclasses import dataclass

from sqlalchemy import event, text


@dataclass
class Result:
    columns: list[str]
    rows: list[dict]
    rowcount: int


class Reporter:
    def __init__(self, stream=None):
        self.stream = stream if stream is not None else sys.stdout

    def line(self, message=""):
        print(message, file=self.stream)

    def heading(self, number, title):
        self.line(f"\n=== Task {number}: {title} ===")

    def execute(self, connection, sql, parameters=None, *, caption="Result", script=False):
        self.line(f"\n{caption}")

        def show_sql(conn, cursor, statement, bound, context, executemany):
            self.line("SQL:")
            self.line(statement.strip())
            self.line(f"Bound parameters: {bound!r}")

        event.listen(connection, "before_cursor_execute", show_sql)
        try:
            if script:
                cursor_result = connection.exec_driver_sql(sql)
            else:
                cursor_result = connection.execute(text(sql), parameters or {})
            columns = list(cursor_result.keys()) if cursor_result.returns_rows else []
            rows = [dict(row) for row in cursor_result.mappings()] if columns else []
            result = Result(columns, rows, cursor_result.rowcount)
            cursor_result.close()
        finally:
            event.remove(connection, "before_cursor_execute", show_sql)
        if columns:
            self.line(" | ".join(columns))
            for row in rows:
                self.line(" | ".join("NULL" if row[c] is None else str(row[c]) for c in columns))
            self.line(f"Rows returned: {len(rows)}")
        else:
            self.line("Executed successfully; no row result set.")
        return result
