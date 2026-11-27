"""Request/response schemas. PUT replaces a complete record and its nested lists."""
from datetime import date, time
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
Labels = Annotated[list[Label], Field(min_length=1)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorProfile(Model):
    orcid: str | None = None
    research_areas: Labels


class ReviewerProfile(Model):
    years_experience: Annotated[int, Field(strict=True, ge=0)]
    expertise_areas: Labels


class UserWrite(Model):
    given_name: Label
    surname: Label
    email: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]
    affiliation: Label
    country: Label
    phone_number: Label
    author: AuthorProfile | None = None
    reviewer: ReviewerProfile | None = None

    @model_validator(mode="after")
    def has_role(self):
        if self.author is None and self.reviewer is None:
            raise ValueError("A user must have an author or reviewer profile (or both).")
        return self


class UserRead(UserWrite):
    user_id: int


class Authorship(Model):
    author_id: PositiveInt
    author_position: PositiveInt
    is_corresponding: StrictBool


class Version(Model):
    version_no: PositiveInt
    file_location: Label
    uploaded_at: AwareDatetime
    change_note: str | None = None


class PaperWrite(Model):
    track_id: PositiveInt
    title: Label
    abstract: Label
    submission_date: date
    status: Literal["submitted", "under review", "accepted", "rejected", "withdrawn"]
    session_id: PositiveInt | None = None
    authors: Annotated[list[Authorship], Field(min_length=1)]
    keywords: Labels
    versions: Annotated[list[Version], Field(min_length=1)]


class PaperRead(PaperWrite):
    paper_id: int
    current_version_no: int


class ReviewWrite(Model):
    paper_id: PositiveInt
    reviewer_id: PositiveInt
    overall_score: Annotated[int, Field(strict=True, ge=1, le=5)]
    recommendation: Literal["accept", "reject"]
    comments_for_authors: Label
    confidential_comments: str | None = None
    review_submission_date: date


class ReviewRead(ReviewWrite):
    review_id: int


class SessionWrite(Model):
    conference_id: PositiveInt
    title: Label
    session_date: date
    start_time: time
    end_time: time
    room_label: Label
    chair_id: PositiveInt

    @model_validator(mode="after")
    def valid_times(self):
        if self.start_time.tzinfo is not None or self.end_time.tzinfo is not None:
            raise ValueError("Session times must be local wall times without a timezone.")
        if self.end_time <= self.start_time:
            raise ValueError("Session end_time must be later than start_time.")
        return self


class SessionRead(SessionWrite):
    session_id: int
