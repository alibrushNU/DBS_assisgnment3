"""Small transactional resource workflows built on the Part 1 integrity helpers."""
from fastapi import HTTPException
from sqlalchemy import MetaData, Table, delete, insert, select, update

from part1.integrity import replace_paper_authors, save_paper


def table(conn, name):
    return Table(name, MetaData(), schema="csci341_part1", autoload_with=conn, resolve_fks=False)


def get_row(conn, name, key, identifier):
    relation = table(conn, name)
    row = conn.execute(select(relation).where(relation.c[key] == identifier)).mappings().first()
    if row is None:
        raise HTTPException(404, "Record not found.")
    return dict(row)


def list_rows(conn, name, limit=50, offset=0):
    relation = table(conn, name)
    statement = select(relation).order_by(*relation.primary_key.columns).limit(limit).offset(offset)
    return [dict(r) for r in conn.execute(statement).mappings()]


def children(conn, name, key, identifier, order):
    relation = table(conn, name)
    return [dict(r) for r in conn.execute(select(relation).where(relation.c[key] == identifier).order_by(relation.c[order])).mappings()]


def replace_children(conn, name, key, identifier, rows):
    relation = table(conn, name)
    conn.execute(delete(relation).where(relation.c[key] == identifier))
    if rows:
        conn.execute(insert(relation), [dict(row, **{key: identifier}) for row in rows])


def delete_record(conn, name, key, identifier):
    get_row(conn, name, key, identifier)
    relation = table(conn, name)
    conn.execute(delete(relation).where(relation.c[key] == identifier))


def read_user(conn, user_id):
    result = get_row(conn, "app_user", "user_id", user_id)
    author = children(conn, "author", "author_id", user_id, "author_id")
    reviewer = children(conn, "reviewer", "reviewer_id", user_id, "reviewer_id")
    result["author"] = None if not author else {
        "orcid": author[0]["orcid"],
        "research_areas": [r["area_label"] for r in children(conn, "author_research_area", "author_id", user_id, "area_label")],
    }
    result["reviewer"] = None if not reviewer else {
        "years_experience": reviewer[0]["years_experience"],
        "expertise_areas": [r["area_label"] for r in children(conn, "reviewer_expertise", "reviewer_id", user_id, "area_label")],
    }
    return result


def write_user(conn, body, user_id=None):
    values = body.model_dump(exclude={"author", "reviewer"})
    relation = table(conn, "app_user")
    if user_id is None:
        user_id = conn.execute(insert(relation).values(**values).returning(relation.c.user_id)).scalar_one()
    else:
        get_row(conn, "app_user", "user_id", user_id)
        conn.execute(update(relation).where(relation.c.user_id == user_id).values(**values))
    for name, profile, label_table, label_field in (
        ("author", body.author, "author_research_area", "research_areas"),
        ("reviewer", body.reviewer, "reviewer_expertise", "expertise_areas"),
    ):
        role = table(conn, name)
        key = f"{name}_id"
        exists = conn.execute(select(role.c[key]).where(role.c[key] == user_id)).first()
        if profile is None:
            if exists:
                conn.execute(delete(role).where(role.c[key] == user_id))
        else:
            role_values = profile.model_dump(exclude={label_field})
            if exists:
                conn.execute(update(role).where(role.c[key] == user_id).values(**role_values))
            else:
                conn.execute(insert(role).values(**{key: user_id}, **role_values))
            replace_children(conn, label_table, key, user_id,
                             [{"area_label": label} for label in getattr(profile, label_field)])
    return read_user(conn, user_id)


def read_paper(conn, paper_id):
    result = get_row(conn, "paper", "paper_id", paper_id)
    result["authors"] = [{k: v for k, v in r.items() if k != "paper_id"}
                         for r in children(conn, "paper_author", "paper_id", paper_id, "author_position")]
    result["keywords"] = [r["keyword"] for r in children(conn, "paper_keyword", "paper_id", paper_id, "keyword")]
    result["versions"] = [{k: v for k, v in r.items() if k != "paper_id"}
                          for r in children(conn, "paper_version", "paper_id", paper_id, "version_no")]
    result["current_version_no"] = max(v["version_no"] for v in result["versions"])
    return result


def write_paper(conn, body, paper_id=None):
    values = body.model_dump(exclude={"authors", "keywords", "versions"})
    if paper_id is not None:
        get_row(conn, "paper", "paper_id", paper_id)
        values["paper_id"] = paper_id
    paper_id = save_paper(conn, **values)
    replace_paper_authors(conn, paper_id, [a.model_dump() for a in body.authors])
    replace_children(conn, "paper_keyword", "paper_id", paper_id, [{"keyword": k} for k in body.keywords])
    replace_children(conn, "paper_version", "paper_id", paper_id, [v.model_dump() for v in body.versions])
    return read_paper(conn, paper_id)
