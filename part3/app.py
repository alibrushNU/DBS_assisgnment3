"""Swagger UI and transactional CRUD. No schema resets or seeding at startup."""
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Body, Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from part1.integrity import ValidationError, save_review, save_session
from part2.operations import SCHEDULE_QUERY
from . import service
from .database import check_schema, environment_engine
from .models import PaperRead, PaperWrite, ReviewRead, ReviewWrite, SessionRead, SessionWrite, UserRead, UserWrite


def get_connection(request: Request):
    # Function-scoped dependency commits (or rolls back) before the HTTP response.
    with request.app.state.engine.begin() as connection:
        yield connection


DB = Annotated[object, Depends(get_connection, scope="function")]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
REFERENCE = {
    "conferences": "conference", "tracks": "track", "reviewer-pools": "conference_reviewer",
    "hosts": "conference_host", "research-areas": "author_research_area", "expertise-areas": "reviewer_expertise",
}

USER_EXAMPLE = {"given_name": "Demo", "surname": "Author", "email": "demo.author@example.com",
                "affiliation": "Demo Institute", "country": "Kazakhstan", "phone_number": "+77019990000",
                "author": {"orcid": None, "research_areas": ["Databases"]}, "reviewer": None}
PAPER_EXAMPLE = {"track_id": 1, "title": "Demo Paper", "abstract": "A demonstration submission.",
                 "submission_date": "2026-09-20", "status": "submitted", "session_id": None,
                 "authors": [{"author_id": 1, "author_position": 1, "is_corresponding": True}],
                 "keywords": ["databases"], "versions": [{"version_no": 1, "file_location": "papers/demo/v1.pdf",
                 "uploaded_at": "2026-09-20T09:00:00Z", "change_note": None}]}
REVIEW_EXAMPLE = {"paper_id": 5, "reviewer_id": 9, "overall_score": 4, "recommendation": "accept",
                  "comments_for_authors": "Clear contribution and evaluation.", "confidential_comments": None,
                  "review_submission_date": "2026-10-20"}
SESSION_EXAMPLE = {"conference_id": 1, "title": "Demo session", "session_date": "2026-12-11",
                   "start_time": "09:00:00", "end_time": "10:00:00", "room_label": "Room C", "chair_id": 9}


def create_app(engine=None):
    @asynccontextmanager
    async def lifespan(application):
        owned = engine is None
        application.state.engine = environment_engine() if owned else engine
        try:
            with application.state.engine.connect() as connection:
                check_schema(connection)
            yield
        finally:
            if owned:
                application.state.engine.dispose()

    application = FastAPI(
        title="CSCI 341 Conference Management", version="1.0.0", lifespan=lifespan,
        description="Manage users, papers, completed reviews, and conference sessions. "
                    "Use the reference endpoints to select conference, track, and reviewer IDs. "
                    "PUT replaces the full record, including nested profiles or lists. "
                    "GET a record to inspect its current values; omit read-only IDs when submitting a body.",
        swagger_ui_parameters={"defaultModelsExpandDepth": 0},
        responses={404: {"description": "Record not found"}, 409: {"description": "Duplicate or referenced record"},
                   422: {"description": "Invalid input or business rule violation"}, 503: {"description": "Database unavailable"}},
    )

    @application.exception_handler(ValidationError)
    async def business_error(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.exception_handler(IntegrityError)
    async def integrity_error(request, error):
        state = getattr(error.orig, "sqlstate", "")
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        specific = {
            "uq_user_email": "That email address is already registered.",
            "uq_review_paper_reviewer": "This reviewer already has a review for this paper.",
            "uq_paper_author_position": "Author positions must be unique within a paper.",
            "uq_one_corresponding_author": "A paper can have only one corresponding author.",
            "fk_session_chair_pool": "The session chair must belong to the conference reviewer pool.",
        }
        message = specific.get(constraint) or {
            "23503": "A referenced record does not exist, or this record still has dependent records. Check the IDs or remove the dependents first.",
            "23505": "Duplicate value: IDs, labels, author positions, and version numbers must be unique within their parent record.",
            "23514": "A value violates a database constraint. Check allowed values, ranges, and date/time order.",
            "23502": "A required field is missing.",
        }.get(state, "The change violates a database constraint.")
        return JSONResponse(status_code=409 if state in {"23503", "23505"} else 422,
                            content={"detail": message, "constraint": constraint})

    @application.exception_handler(DBAPIError)
    async def database_error(request, error):
        # Never return raw driver errors, SQL, connection details, or credentials.
        return JSONResponse(status_code=503, content={"detail": "Database unavailable. Retry after checking the service."})

    @application.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")

    @application.get("/health", tags=["Status"])
    def health(conn: DB):
        conn.execute(text("SELECT 1 FROM csci341_part1.app_user LIMIT 0"))
        return {"status": "ok"}

    @application.get("/users", response_model=list[UserRead], tags=["Users"])
    def list_users(conn: DB, limit: Limit = 50, offset: Offset = 0):
        return [service.read_user(conn, r["user_id"]) for r in service.list_rows(conn, "app_user", limit, offset)]

    @application.post("/users", response_model=UserRead, status_code=201, tags=["Users"])
    def create_user(conn: DB, body: UserWrite = Body(openapi_examples={"author": {"value": USER_EXAMPLE}})):
        return service.write_user(conn, body)

    @application.get("/users/{user_id}", response_model=UserRead, tags=["Users"])
    def read_user(user_id: int, conn: DB):
        return service.read_user(conn, user_id)

    @application.put("/users/{user_id}", response_model=UserRead, tags=["Users"], summary="Replace a user and author/reviewer profiles")
    def update_user(user_id: int, body: UserWrite, conn: DB):
        return service.write_user(conn, body, user_id)

    @application.delete("/users/{user_id}", status_code=204, tags=["Users"])
    def delete_user(user_id: int, conn: DB):
        service.delete_record(conn, "app_user", "user_id", user_id)
        return Response(status_code=204)

    @application.get("/papers", response_model=list[PaperRead], tags=["Papers"])
    def list_papers(conn: DB, limit: Limit = 50, offset: Offset = 0):
        return [service.read_paper(conn, r["paper_id"]) for r in service.list_rows(conn, "paper", limit, offset)]

    @application.post("/papers", response_model=PaperRead, status_code=201, tags=["Papers"])
    def create_paper(conn: DB, body: PaperWrite = Body(openapi_examples={"submission": {"value": PAPER_EXAMPLE}})):
        return service.write_paper(conn, body)

    @application.get("/papers/{paper_id}", response_model=PaperRead, tags=["Papers"])
    def read_paper(paper_id: int, conn: DB):
        return service.read_paper(conn, paper_id)

    @application.put("/papers/{paper_id}", response_model=PaperRead, tags=["Papers"], summary="Replace a paper, authors, keywords, and versions")
    def update_paper(paper_id: int, body: PaperWrite, conn: DB):
        return service.write_paper(conn, body, paper_id)

    @application.delete("/papers/{paper_id}", status_code=204, tags=["Papers"])
    def delete_paper(paper_id: int, conn: DB):
        service.delete_record(conn, "paper", "paper_id", paper_id)
        return Response(status_code=204)

    @application.get("/reviews", response_model=list[ReviewRead], tags=["Reviews"])
    def list_reviews(conn: DB, limit: Limit = 50, offset: Offset = 0):
        return service.list_rows(conn, "review", limit, offset)

    @application.post("/reviews", response_model=ReviewRead, status_code=201, tags=["Reviews"])
    def create_review(conn: DB, body: ReviewWrite = Body(openapi_examples={"completed": {"value": REVIEW_EXAMPLE}})):
        identifier = save_review(conn, **body.model_dump())
        return service.get_row(conn, "review", "review_id", identifier)

    @application.get("/reviews/{review_id}", response_model=ReviewRead, tags=["Reviews"])
    def read_review(review_id: int, conn: DB):
        return service.get_row(conn, "review", "review_id", review_id)

    @application.put("/reviews/{review_id}", response_model=ReviewRead, tags=["Reviews"])
    def update_review(review_id: int, body: ReviewWrite, conn: DB):
        service.get_row(conn, "review", "review_id", review_id)
        save_review(conn, review_id=review_id, **body.model_dump())
        return service.get_row(conn, "review", "review_id", review_id)

    @application.delete("/reviews/{review_id}", status_code=204, tags=["Reviews"])
    def delete_review(review_id: int, conn: DB):
        service.delete_record(conn, "review", "review_id", review_id)
        return Response(status_code=204)

    @application.get("/sessions", response_model=list[SessionRead], tags=["Sessions"])
    def list_sessions(conn: DB, limit: Limit = 50, offset: Offset = 0):
        return service.list_rows(conn, "conference_session", limit, offset)

    @application.post("/sessions", response_model=SessionRead, status_code=201, tags=["Sessions"])
    def create_session(conn: DB, body: SessionWrite = Body(openapi_examples={"session": {"value": SESSION_EXAMPLE}})):
        identifier = save_session(conn, **body.model_dump())
        return service.get_row(conn, "conference_session", "session_id", identifier)

    @application.get("/sessions/{session_id}", response_model=SessionRead, tags=["Sessions"])
    def read_session(session_id: int, conn: DB):
        return service.get_row(conn, "conference_session", "session_id", session_id)

    @application.put("/sessions/{session_id}", response_model=SessionRead, tags=["Sessions"])
    def update_session(session_id: int, body: SessionWrite, conn: DB):
        service.get_row(conn, "conference_session", "session_id", session_id)
        save_session(conn, session_id=session_id, **body.model_dump())
        return service.get_row(conn, "conference_session", "session_id", session_id)

    @application.delete("/sessions/{session_id}", status_code=204, tags=["Sessions"])
    def delete_session(session_id: int, conn: DB):
        service.delete_record(conn, "conference_session", "session_id", session_id)
        return Response(status_code=204)

    @application.get("/reference/{relation}", tags=["Reference data"])
    def reference(relation: Literal["conferences", "tracks", "reviewer-pools", "hosts", "research-areas", "expertise-areas"], conn: DB,
                  limit: Limit = 50, offset: Offset = 0):
        return service.list_rows(conn, REFERENCE[relation], limit, offset)

    @application.get("/schedule", tags=["Reference data"], summary="Read the Part 2 accepted-paper schedule")
    def schedule(conn: DB):
        return [dict(row) for row in conn.execute(text(SCHEDULE_QUERY)).mappings()]

    return application


app = create_app()
