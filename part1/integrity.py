"""Required Part 1 application checks, reusable by a future application.

Pass a SQLAlchemy Connection inside engine.begin(). These helpers validate
proposed state before writing; no UI, Part 2 operations, or advanced concurrency.
Direct SQL can bypass these checks, as permitted by the assignment.
"""
from sqlalchemy import MetaData, Table, delete, insert, select, text, update


class ValidationError(ValueError):
    """A proposed change would violate a documented business rule."""


def _prepare(connection, name, key, values):
    table = Table(name, MetaData(), autoload_with=connection, resolve_fks=False)
    existing = None
    if key in values:
        existing = connection.execute(
            select(table).where(table.c[key] == values[key])
        ).mappings().one_or_none()
    merged = dict(existing or {}) | dict(values)
    return table, existing, merged


def _write(connection, table, key, existing, values):
    statement = (
        update(table).where(table.c[key] == values[key]) if existing is not None else insert(table)
    )
    return connection.execute(statement.values(**values).returning(table.c[key])).scalar_one()


def save_review(connection, **values):
    """Insert a completed review, or update the review identified by review_id."""
    table, existing, proposed = _prepare(connection, "review", "review_id", values)
    conflict = connection.execute(text("""
        SELECT 1 FROM paper_author WHERE paper_id = :paper_id AND author_id = :reviewer_id
    """), proposed).first()
    if conflict:
        raise ValidationError("A reviewer cannot review a paper they authored.")
    return _write(connection, table, "review_id", existing, proposed)


def replace_paper_authors(connection, paper_id, authors):
    """Replace the complete ordered authorship list; rollback any failed replacement.

    Each entry has author_id, author_position, and is_corresponding.
    This also enforces at least one author and exactly one corresponding author.
    """
    authors = list(authors)
    if not connection.execute(text("SELECT 1 FROM paper WHERE paper_id = :p"), {"p": paper_id}).first():
        raise ValidationError("Paper does not exist.")
    if not authors or sum(a["is_corresponding"] is True for a in authors) != 1:
        raise ValidationError("A paper must have authors and exactly one corresponding author.")
    reviewers = set(connection.execute(text("SELECT reviewer_id FROM review WHERE paper_id = :p"), {"p": paper_id}).scalars())
    if reviewers.intersection(a["author_id"] for a in authors):
        raise ValidationError("Authorship would turn an existing review into a self-review.")
    table = Table("paper_author", MetaData(), autoload_with=connection, resolve_fks=False)
    with connection.begin_nested():
        connection.execute(delete(table).where(table.c.paper_id == paper_id))
        connection.execute(insert(table), [dict(a, paper_id=paper_id) for a in authors])


def _validate_assignment(connection, proposed):
    if proposed.get("session_id") is None:
        return
    if proposed["status"] != "accepted":
        raise ValidationError("Only accepted papers can be assigned to a session.")
    compatible = connection.execute(text("""
        SELECT 1 FROM track t JOIN conference_session s ON s.conference_id = t.conference_id
        WHERE t.track_id = :track_id AND s.session_id = :session_id
    """), proposed).first()
    if not compatible:
        raise ValidationError("The paper track and session must belong to the same conference.")


def save_paper(connection, **values):
    """Validate inserts, session assignments, status changes, and track changes."""
    table, existing, proposed = _prepare(connection, "paper", "paper_id", values)
    _validate_assignment(connection, proposed)
    return _write(connection, table, "paper_id", existing, proposed)


def save_session(connection, **values):
    """Reject conference changes that invalidate papers already in a session."""
    table, existing, proposed = _prepare(connection, "conference_session", "session_id", values)
    if existing is not None:
        invalid = connection.execute(text("""
            SELECT 1 FROM paper p JOIN track t ON t.track_id = p.track_id
            WHERE p.session_id = :session_id
              AND (p.status <> 'accepted' OR t.conference_id <> :conference_id)
            LIMIT 1
        """), proposed).first()
        if invalid:
            raise ValidationError("Changing this session would invalidate an assigned paper.")
    return _write(connection, table, "session_id", existing, proposed)


def save_track(connection, **values):
    """Also protect assigned papers if their track itself moves conference."""
    table, existing, proposed = _prepare(connection, "track", "track_id", values)
    if existing is not None:
        invalid = connection.execute(text("""
            SELECT 1 FROM paper p JOIN conference_session s ON s.session_id = p.session_id
            WHERE p.track_id = :track_id
              AND (p.status <> 'accepted' OR s.conference_id <> :conference_id)
            LIMIT 1
        """), proposed).first()
        if invalid:
            raise ValidationError("Changing this track would invalidate an assigned paper.")
    return _write(connection, table, "track_id", existing, proposed)
