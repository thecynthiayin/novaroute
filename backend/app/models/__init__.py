from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    # MySQL DATETIME stores whole seconds in this schema. Avoid rounding a new
    # outbox's due time into the future when it is delivered immediately.
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Timestamped, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(Enum("student", "employer", "admin", name="user_role"))
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email_matches: Mapped[bool] = mapped_column(Boolean, default=True)
    email_applications: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime)


class StudentProfile(Timestamped, Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    extracted_skills: Mapped[list] = mapped_column(JSON, default=list)
    coursework: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    resume_derived: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_resume_text: Mapped[str | None] = mapped_column(Text)
    degree: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(default=1)


class EmployerProfile(Timestamped, Base):
    __tablename__ = "employer_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    company_name: Mapped[str] = mapped_column(String(150), default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    industry: Mapped[str] = mapped_column(String(150), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    legal_name: Mapped[str] = mapped_column(String(200), default="")
    registration_number: Mapped[str] = mapped_column(String(150), default="")
    registration_explanation: Mapped[str] = mapped_column(String(1000), default="")
    recruiter_name: Mapped[str] = mapped_column(String(100), default="")
    recruiter_position: Mapped[str] = mapped_column(String(150), default="")
    contact_email: Mapped[str] = mapped_column(String(254), default="")
    contact_phone: Mapped[str] = mapped_column(String(80), default="")
    verification_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    verification_version: Mapped[int] = mapped_column(default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_reason: Mapped[str] = mapped_column(Text, default="")


class Resume(Timestamped, Base):
    __tablename__ = "resumes"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    storage_ref: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64))
    parse_state: Mapped[str] = mapped_column(String(30), default="draft")
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_text: Mapped[str | None] = mapped_column(Text)
    failure: Mapped[str | None] = mapped_column(String(250))
    profile_version: Mapped[int] = mapped_column(Integer)


class Internship(Timestamped, Base):
    __tablename__ = "internships"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String(200))
    work_mode: Mapped[str] = mapped_column(Enum("remote", "hybrid", "onsite", name="work_mode"))
    duration: Mapped[str] = mapped_column(String(100))
    stipend_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stipend_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(
        Enum("pending_ai_review", "active", "flagged", "closed", name="internship_status"),
        default="pending_ai_review",
        index=True,
    )
    moderation: Mapped[dict] = mapped_column(JSON, default=dict)
    moderation_model: Mapped[str | None] = mapped_column(String(200))
    content_version: Mapped[int] = mapped_column(default=1)
    source_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    admin_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (Index("ix_internship_eligible", "status", "deleted_at", "deadline"),)


class Application(Timestamped, Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    internship_id: Mapped[int] = mapped_column(ForeignKey("internships.id"), index=True)
    cover_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        Enum("applied", "viewed", "rejected", "accepted", "withdrawn", name="application_status"),
        default="applied",
    )
    profile_snapshot: Mapped[dict] = mapped_column(JSON)
    match_score: Mapped[float | None]
    version: Mapped[int] = mapped_column(default=1)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("student_id", "internship_id", name="uq_application_student_listing"),)


class StatusHistory(Base):
    __tablename__ = "application_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    employer_note: Mapped[str | None] = mapped_column(Text)
    event_version: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("application_id", "event_version", name="uq_history_version"),)


class SavedInternship(Timestamped, Base):
    __tablename__ = "saved_internships"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    internship_id: Mapped[int] = mapped_column(ForeignKey("internships.id"))
    note: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("student_id", "internship_id", name="uq_saved_pair"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    related: Mapped[dict] = mapped_column(JSON, default=dict)
    feedback: Mapped[dict | None] = mapped_column(JSON)
    feedback_state: Mapped[str] = mapped_column(String(30), default="not_required")
    event_key: Mapped[str] = mapped_column(String(150), unique=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), unique=True)
    event_key: Mapped[str] = mapped_column(String(160), unique=True)
    state: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(250))
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ListingReport(Timestamped, Base):
    __tablename__ = "listing_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("internships.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (UniqueConstraint("listing_id", "reporter_id", name="uq_report_student_listing"),)


class AdminAudit(Base):
    __tablename__ = "admin_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
