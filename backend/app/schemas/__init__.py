from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal

from email_validator import validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings


def valid_email(value: str) -> str:
    return validate_email(
        value, check_deliverability=False, test_environment=settings().environment != "production"
    ).normalized.lower()


Email = Annotated[str, Field(max_length=254), AfterValidator(valid_email)]

Short = Annotated[str, Field(min_length=1, max_length=150)]
SkillList = Annotated[list[Short], Field(max_length=60)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class Project(Strict):
    title: str = Field(max_length=200)
    description: str = Field(max_length=1500)
    technologies: SkillList


class Extraction(Strict):
    skills: SkillList
    coursework: SkillList
    projects: list[Project] = Field(max_length=20)
    education: list[Short] = Field(max_length=10)


class Moderation(Strict):
    classification: Literal["valid", "flagged"]
    risk_reasons: list[Short] = Field(max_length=12)
    suggested_changes: list[Short] = Field(max_length=12)


class Feedback(Strict):
    summary: str = Field(max_length=1200)
    strengths: list[Short] = Field(max_length=10)
    potential_gaps: list[Short] = Field(max_length=10)
    next_steps: list[Short] = Field(max_length=10)
    practice_questions: list[Short] = Field(max_length=10)


class Login(Strict):
    email: Email
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class Register(Login):
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)
    role: Literal["student", "employer"]


class AccountPatch(Strict):
    name: str = Field(min_length=2, max_length=100)
    email: Email
    email_matches: bool
    email_applications: bool
    current_password: str = Field(default="", max_length=128)


class PasswordChange(Strict):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ConfirmPassword(Strict):
    password: str = Field(max_length=128)


class Preferences(Strict):
    work_mode: Literal["", "remote", "hybrid", "onsite"] = ""
    interests: str = Field(default="", max_length=500)


class ProfilePatch(Strict):
    extracted_skills: SkillList
    coursework: SkillList
    projects: list[Project] = Field(max_length=20)
    degree: str = Field(max_length=200)
    location: str = Field(max_length=200)
    preferences: Preferences = Field(default_factory=Preferences)
    version: int = Field(ge=1)


class ExtractionConfirm(Extraction):
    version: int = Field(ge=1)


class CompanyPatch(Strict):
    company_name: str = Field(min_length=2, max_length=150)
    website: str = Field(default="", max_length=500)
    industry: str = Field(default="", max_length=150)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)

    @field_validator("website")
    @classmethod
    def safe_url(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Website must start with https:// or http://")
        return value


class ListingInput(Strict):
    title: str = Field(min_length=4, max_length=200)
    description: str = Field(min_length=30, max_length=12000)
    required_skills: SkillList
    location: str = Field(min_length=2, max_length=200)
    work_mode: Literal["remote", "hybrid", "onsite"]
    duration: str = Field(min_length=1, max_length=100)
    stipend_min: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stipend_max: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def utc_date(cls, value):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value

    @model_validator(mode="after")
    def stipend_range(self):
        if self.stipend_min is not None or self.stipend_max is not None:
            if not self.currency:
                raise ValueError("A currency is required for a numeric stipend")
        if (
            self.stipend_min is not None
            and self.stipend_max is not None
            and self.stipend_max < self.stipend_min
        ):
            raise ValueError("Maximum stipend must be at least minimum")
        return self


class ListingEdit(ListingInput):
    content_version: int = Field(ge=1)


class Apply(Strict):
    internship_id: int = Field(gt=0)
    cover_message: str = Field(default="", max_length=4000)


class CoverEdit(Strict):
    cover_message: str = Field(max_length=4000)
    version: int = Field(ge=1)


class StatusChange(Strict):
    status: Literal["viewed", "accepted", "rejected"]
    version: int = Field(ge=1)
    employer_note: str | None = Field(default=None, max_length=2000)


class Version(Strict):
    version: int = Field(ge=1)


class Note(Strict):
    note: str = Field(default="", max_length=2000)


class NotificationEdit(Strict):
    read: bool


class UserOut(Strict):
    id: int
    role: Literal["student", "employer", "admin"]
    name: str
    email: str
    email_matches: bool
    email_applications: bool


class OK(Strict):
    message: str


class Page(Strict):
    items: list[dict]
    total: int
    page: int
    page_size: int
