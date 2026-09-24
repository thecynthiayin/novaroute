"""Explicit public API outputs. Private ORM fields never enter these schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, JsonValue

from app.schemas import Extraction, Feedback, Project

T = TypeVar("T")


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(Output, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ProfileOut(Output):
    id: int
    user_id: int
    extracted_skills: list[str]
    coursework: list[str]
    projects: list[Project]
    degree: str
    location: str
    preferences: dict[str, JsonValue]
    version: int
    created_at: datetime
    updated_at: datetime


class CompanyOut(Output):
    company_name: str
    website: str
    industry: str
    location: str
    description: str
    verification_status: str = "pending"
    reviewed_at: datetime | None = None
    demo_company: bool = False


class ListingOut(Output):
    id: int
    employer_id: int
    title: str
    description: str
    required_skills: list[str]
    location: str
    work_mode: str
    duration: str
    stipend_min: Decimal | None
    stipend_max: Decimal | None
    currency: str | None
    deadline: datetime | None
    status: str
    admin_hidden: bool = False
    content_version: int
    provenance: dict[str, JsonValue]
    company: CompanyOut
    moderation: dict[str, JsonValue] | None = None
    moderation_model: str | None = None
    created_at: datetime
    updated_at: datetime


class UnavailableListing(Output):
    id: int
    title: str
    status: str


class ResumeOut(Output):
    id: int
    student_id: int
    filename: str
    content_hash: str
    parse_state: str
    extracted: Extraction | dict[str, JsonValue]
    failure: str | None
    profile_version: int
    created_at: datetime
    updated_at: datetime
    confirmation_needed: bool | None = None
    ai_mode: str | None = None


class Related(Output):
    application_id: int | None = None
    internship_id: int | None = None
    version: int | None = None
    status: str | None = None
    similarity: float | None = None


class NotificationOut(Output):
    id: int
    recipient_id: int
    type: str
    title: str
    body: str
    related: Related
    feedback: Feedback | None
    feedback_state: str
    read_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime
    email_state: str | None = None


class HistoryOut(Output):
    id: int
    application_id: int
    previous_status: str | None
    new_status: str
    actor_id: int
    employer_note: str | None
    event_version: int
    created_at: datetime


class ApplicationOut(Output):
    id: int
    student_id: int
    internship_id: int
    internship_title: str
    student_name: str
    listing_status: str
    cover_message: str
    status: str
    profile_snapshot: dict[str, JsonValue]
    match_score: float | None
    version: int
    applied_at: datetime
    updated_at: datetime
    withdrawn_at: datetime | None
    history: list[HistoryOut]
    events: list[NotificationOut]


class SavedOut(Output):
    id: int
    student_id: int
    internship_id: int
    note: str
    created_at: datetime
    updated_at: datetime
    available: bool | None = None
    internship: ListingOut | UnavailableListing | None = None


class MatchOut(Output):
    internship: ListingOut
    similarity: float
    percentage: float
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str
    score_help: str


class RecommendationsOut(Output):
    items: list[MatchOut]
    threshold: float
    strictly_greater: bool


class DashboardOut(Output):
    counts: dict[str, int]
    recent_events: list[NotificationOut]


class CountOut(Output):
    unread: int


class CSRFOut(Output):
    csrf_token: str


class InternshipStates(Output):
    saved_ids: list[int]
    applied_ids: list[int]
