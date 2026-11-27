"""HTTP tests against the dedicated PostgreSQL database, not an SQLite substitute."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from part2.state import snapshot
from part3.app import PAPER_EXAMPLE, REVIEW_EXAMPLE, SESSION_EXAMPLE, USER_EXAMPLE, create_app, get_connection
from part3.database import check_schema, environment_engine
from part3.initialize import initialize_database


@pytest.fixture
def client(engine, conn):
    app = create_app(engine)

    def transactional_connection():
        # Per-request savepoint models commit/rollback; outer test transaction restores rows.
        with conn.begin_nested():
            yield conn

    app.dependency_overrides[get_connection] = transactional_connection
    with TestClient(app) as instance:
        yield instance


def payload(client, resource, identifier):
    row = client.get(f"/{resource}/{identifier}")
    assert row.status_code == 200, row.text
    result = row.json()
    for key in ("user_id", "paper_id", "review_id", "session_id", "current_version_no"):
        # Foreign-key paper_id/session_id must remain in review/paper bodies.
        if key == {"users": "user_id", "papers": "paper_id", "reviews": "review_id", "sessions": "session_id"}[resource] or key == "current_version_no":
            result.pop(key, None)
    return result


def test_swagger_openapi_health_reference_schedule_and_pagination(client):
    assert client.get("/").status_code == 200
    assert "swagger-ui" in client.get("/docs").text
    spec = client.get("/openapi.json").json()
    for resource, key in [("users", "user_id"), ("papers", "paper_id"), ("reviews", "review_id"), ("sessions", "session_id")]:
        assert {"get", "post"} <= set(spec["paths"][f"/{resource}"])
        assert {"get", "put", "delete"} <= set(spec["paths"][f"/{resource}/{{{key}}}"])
        assert client.get(f"/{resource}").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    assert [r["user_id"] for r in client.get("/users?limit=2&offset=1").json()] == [2, 3]
    for relation in ["conferences", "tracks", "reviewer-pools", "hosts", "research-areas", "expertise-areas"]:
        assert client.get(f"/reference/{relation}").json()
        assert client.post(f"/reference/{relation}", json={}).status_code == 405
    assert client.get("/schedule").json()[0]["paper_id"] == 1
    assert client.get("/reference/paper").status_code == 422
    assert client.get("/users?limit=0").status_code == 422


def test_user_crud_profiles_labels_and_role_removal(client, conn):
    body = deepcopy(USER_EXAMPLE)
    created = client.post("/users", json=body)
    assert created.status_code == 201, created.text
    uid = created.json()["user_id"]
    body["phone_number"] = "+77019991111"
    body["author"] = {"orcid": "0000-0002-1825-0097", "research_areas": ["Databases", "Security"]}
    body["reviewer"] = {"years_experience": 3, "expertise_areas": ["Databases", "Networks"]}
    updated = client.put(f"/users/{uid}", json=body)
    assert updated.status_code == 200, updated.text
    assert updated.json()["reviewer"] == body["reviewer"]
    assert client.get(f"/users/{uid}").json()["author"] == body["author"]
    body["author"] = None
    body["reviewer"]["expertise_areas"] = ["Networks"]
    assert client.put(f"/users/{uid}", json=body).json()["author"] is None
    assert conn.execute(text("SELECT count(*) FROM author_research_area WHERE author_id = :id"), {"id": uid}).scalar_one() == 0
    assert client.delete(f"/users/{uid}").status_code == 204
    assert client.get(f"/users/{uid}").status_code == 404
    assert conn.execute(text("SELECT count(*) FROM reviewer_expertise WHERE reviewer_id = :id"), {"id": uid}).scalar_one() == 0


def test_paper_crud_nested_authors_keywords_versions_and_review_cascade(client, conn):
    body = deepcopy(PAPER_EXAMPLE)
    created = client.post("/papers", json=body)
    assert created.status_code == 201, created.text
    pid = created.json()["paper_id"]
    assert created.json()["current_version_no"] == 1
    body["authors"] = [{"author_id": 3, "author_position": 1, "is_corresponding": True},
                       {"author_id": 1, "author_position": 2, "is_corresponding": False}]
    body["keywords"] = ["learning", "databases"]
    body["versions"].append(dict(body["versions"][0], version_no=4, file_location="papers/demo/v4.pdf"))
    updated = client.put(f"/papers/{pid}", json=body)
    assert updated.status_code == 200, updated.text
    assert updated.json()["authors"] == body["authors"]
    assert updated.json()["keywords"] == ["databases", "learning"]
    assert updated.json()["current_version_no"] == 4
    body["versions"] = [body["versions"][1]]
    body["keywords"] = ["learning"]
    assert client.put(f"/papers/{pid}", json=body).status_code == 200
    assert len(client.get(f"/papers/{pid}").json()["versions"]) == 1
    review = client.post("/reviews", json=dict(REVIEW_EXAMPLE, paper_id=pid))
    assert review.status_code == 201, review.text
    assert client.delete(f"/papers/{pid}").status_code == 204
    assert client.get(f"/papers/{pid}").status_code == 404
    assert client.get(f"/reviews/{review.json()['review_id']}").status_code == 404
    for name in ["paper_author", "paper_keyword", "paper_version", "review"]:
        assert conn.execute(text(f"SELECT count(*) FROM {name} WHERE paper_id = :id"), {"id": pid}).scalar_one() == 0


def test_review_crud_and_duplicate_pair(client):
    response = client.post("/reviews", json=REVIEW_EXAMPLE)
    assert response.status_code == 201, response.text
    rid = response.json()["review_id"]
    assert client.post("/reviews", json=REVIEW_EXAMPLE).status_code == 409
    changed = dict(REVIEW_EXAMPLE, paper_id=4, reviewer_id=2, overall_score=5, confidential_comments="Updated.")
    assert client.put(f"/reviews/{rid}", json=changed).status_code == 200
    assert client.get(f"/reviews/{rid}").json()["overall_score"] == 5
    assert client.delete(f"/reviews/{rid}").status_code == 204
    assert client.get(f"/reviews/{rid}").status_code == 404


def test_session_crud_empty_conference_move_and_assignment_on_delete(client):
    response = client.post("/sessions", json=SESSION_EXAMPLE)
    assert response.status_code == 201, response.text
    sid = response.json()["session_id"]
    moved = dict(SESSION_EXAMPLE, conference_id=2, chair_id=2)
    assert client.put(f"/sessions/{sid}", json=moved).status_code == 200
    assert client.put(f"/sessions/{sid}", json=SESSION_EXAMPLE).status_code == 200
    paper = payload(client, "papers", 2)
    paper["session_id"] = sid
    assert client.put("/papers/2", json=paper).status_code == 200
    assert len(client.get("/schedule").json()) == 2
    assert client.delete(f"/sessions/{sid}").status_code == 204
    assert client.get(f"/sessions/{sid}").status_code == 404
    assert client.get("/papers/2").json()["session_id"] is None


@pytest.mark.parametrize("resource,body", [("users", USER_EXAMPLE), ("papers", PAPER_EXAMPLE), ("reviews", REVIEW_EXAMPLE), ("sessions", SESSION_EXAMPLE)])
def test_get_update_delete_missing_records_are_404(client, resource, body):
    assert client.get(f"/{resource}/999999").status_code == 404
    assert client.put(f"/{resource}/999999", json=body).status_code == 404
    assert client.delete(f"/{resource}/999999").status_code == 404


@pytest.mark.parametrize("rid,changes", [(None, {"paper_id": 6, "reviewer_id": 2}), (6, {"reviewer_id": 2}), (2, {"paper_id": 6})])
def test_self_review_rejected_on_create_and_reviewer_or_paper_change(client, rid, changes):
    before = client.get("/reviews").json()
    body = dict(REVIEW_EXAMPLE) if rid is None else payload(client, "reviews", rid)
    body.update(changes)
    result = client.post("/reviews", json=body) if rid is None else client.put(f"/reviews/{rid}", json=body)
    assert result.status_code == 422, result.text
    assert "authored" in result.json()["detail"]
    assert client.get("/reviews").json() == before


def test_authorship_change_rejects_self_review_and_rolls_back_parent(client):
    before = client.get("/papers/1").json()
    body = payload(client, "papers", 1)
    body["title"] = "Must not persist"
    body["authors"].append({"author_id": 2, "author_position": 3, "is_corresponding": False})
    result = client.put("/papers/1", json=body)
    assert result.status_code == 422
    assert "self-review" in result.json()["detail"]
    assert client.get("/papers/1").json() == before


@pytest.mark.parametrize("pid,changes", [(3, {"session_id": 1}), (4, {"session_id": 1}), (5, {"session_id": 1}),
    (6, {"session_id": 1}), (8, {"session_id": 1}), (1, {"status": "rejected"}), (1, {"track_id": 2})])
def test_invalid_session_assignment_and_relevant_paper_updates(client, pid, changes):
    before = client.get(f"/papers/{pid}").json()
    body = payload(client, "papers", pid) | changes
    assert client.put(f"/papers/{pid}", json=body).status_code == 422
    assert client.get(f"/papers/{pid}").json() == before


def test_invalid_session_assignment_on_paper_create(client):
    assert client.post("/papers", json=dict(PAPER_EXAMPLE, session_id=1)).status_code == 422
    assert len(client.get("/papers").json()) == 10


def test_session_conference_update_rejected_and_explicit_unassignment_allowed(client):
    before = client.get("/sessions/1").json()
    body = payload(client, "sessions", 1) | {"conference_id": 2, "chair_id": 2}
    assert client.put("/sessions/1", json=body).status_code == 422
    assert client.get("/sessions/1").json() == before
    paper = payload(client, "papers", 1) | {"session_id": None, "status": "withdrawn", "track_id": 2}
    assert client.put("/papers/1", json=paper).status_code == 200
    assert client.put("/sessions/1", json=body).status_code == 200


def test_user_duplicate_referenced_deletion_and_role_removal_are_atomic(client):
    duplicate = dict(USER_EXAMPLE, email="arman.armanov@example.com")
    assert client.post("/users", json=duplicate).status_code == 409
    assert client.delete("/users/1").status_code == 409
    before = client.get("/users/2").json()
    body = payload(client, "users", 2)
    body["given_name"] = "Must roll back"
    body["reviewer"] = None
    assert client.put("/users/2", json=body).status_code == 409
    assert client.get("/users/2").json() == before


def test_invalid_chair_pool_and_foreign_keys(client):
    assert client.post("/sessions", json=dict(SESSION_EXAMPLE, chair_id=2)).status_code == 409
    assert client.post("/reviews", json=dict(REVIEW_EXAMPLE, reviewer_id=999)).status_code == 409
    assert client.post("/papers", json=dict(PAPER_EXAMPLE, track_id=999)).status_code == 409
    assert len(client.get("/papers").json()) == 10


@pytest.mark.parametrize("field,value", [("overall_score", 0), ("overall_score", 6), ("overall_score", 2.5),
    ("overall_score", True), ("recommendation", "maybe"), ("comments_for_authors", "  "), ("review_submission_date", None)])
def test_completed_review_and_score_validation(client, field, value):
    assert client.post("/reviews", json=dict(REVIEW_EXAMPLE, **{field: value})).status_code == 422


@pytest.mark.parametrize("change", [{"authors": []}, {"keywords": []}, {"versions": []}, {"status": "pending"},
    {"authors": [{"author_id": 1, "author_position": 0, "is_corresponding": True}]},
    {"authors": [{"author_id": 1, "author_position": 1, "is_corresponding": False}]}])
def test_paper_required_children_and_corresponding_author(client, change):
    assert client.post("/papers", json=dict(PAPER_EXAMPLE, **change)).status_code == 422
    assert len(client.get("/papers").json()) == 10


def test_late_nested_failure_rolls_back_paper_user_and_children(client):
    before = client.get("/papers/1").json()
    body = payload(client, "papers", 1)
    body["title"] = "Temporary"
    body["keywords"] = ["replacement"]
    body["versions"].append(dict(body["versions"][0], file_location="duplicate.pdf"))
    assert client.put("/papers/1", json=body).status_code == 409
    assert client.get("/papers/1").json() == before
    body = deepcopy(USER_EXAMPLE)
    body["author"]["research_areas"] = ["Databases", "Databases"]
    assert client.post("/users", json=body).status_code == 409
    assert len(client.get("/users").json()) == 10


def test_optional_minimum_roles_labels_and_session_time_validation(client):
    assert client.post("/users", json=dict(USER_EXAMPLE, author=None)).status_code == 422
    assert client.post("/users", json=dict(USER_EXAMPLE, author={"research_areas": []})).status_code == 422
    assert client.post("/users", json=dict(USER_EXAMPLE, reviewer={"years_experience": -1, "expertise_areas": ["Databases"]})).status_code == 422
    assert client.post("/sessions", json=dict(SESSION_EXAMPLE, end_time="09:00:00")).status_code == 422


def test_real_commits_are_visible_to_other_connections_and_failed_writes_are_not(engine):
    with TestClient(create_app(engine)) as http:
        uid = None
        try:
            created = http.post("/users", json=dict(USER_EXAMPLE, email="committed@example.com"))
            assert created.status_code == 201
            uid = created.json()["user_id"]
            with engine.connect() as conn:
                assert conn.execute(text("SELECT email FROM app_user WHERE user_id=:id"), {"id": uid}).scalar_one() == "committed@example.com"
            invalid = deepcopy(USER_EXAMPLE)
            invalid["email"] = "rollback@example.com"
            invalid["author"]["research_areas"] = ["Databases", "Databases"]
            assert http.post("/users", json=invalid).status_code == 409
            with engine.connect() as conn:
                assert conn.execute(text("SELECT count(*) FROM app_user WHERE email='rollback@example.com'")).scalar_one() == 0
        finally:
            if uid is not None:
                assert http.delete(f"/users/{uid}").status_code == 204


def test_database_failure_returns_safe_error_without_credentials(engine):
    app = create_app(engine)

    def broken_connection():
        raise OperationalError("secret SQL", {}, RuntimeError("database-password-must-not-leak"))
        yield  # Makes this a yield dependency, like the real connection dependency.

    app.dependency_overrides[get_connection] = broken_connection
    with TestClient(app) as http:
        result = http.get("/users")
        assert result.status_code == 503
        assert "password" not in result.text and "secret SQL" not in result.text


def test_deployment_initializer_fresh_and_idempotent_preserves_existing_changes(conn):
    conn.exec_driver_sql("DROP SCHEMA csci341_part1 CASCADE")
    assert "Created" in initialize_database(conn)
    check_schema(conn)
    assert conn.execute(text("SELECT count(*) FROM paper")).scalar_one() == 10
    conn.execute(text("UPDATE app_user SET phone_number='changed' WHERE user_id=1"))
    before = snapshot(conn)
    assert "preserved" in initialize_database(conn)
    assert snapshot(conn) == before


def test_deployment_initializer_rejects_unowned_schema(conn):
    conn.exec_driver_sql("COMMENT ON SCHEMA csci341_part1 IS NULL")
    with pytest.raises(ValueError, match="ownership"):
        initialize_database(conn)


@pytest.mark.parametrize("url", [None, "not-a-url", "sqlite:///file.db", "postgresql://user@host/db"])
def test_production_requires_explicit_postgres_credentials(monkeypatch, url):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if url is not None:
        monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError) as error:
        environment_engine()
    assert "user@host" not in str(error.value)


def test_provider_postgresql_url_normalizes_to_psycopg_without_logging_password(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:example-secret@provider.example/db?sslmode=require")
    engine = environment_engine()
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.query["sslmode"] == "require"
        assert engine.hide_parameters
        assert "example-secret" not in str(engine)
    finally:
        engine.dispose()
