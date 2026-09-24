from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas import Email, Strict
from app.schemas.responses import CompanyOut, Output


class VerificationInput(Strict):
    version: int = Field(ge=1)
    legal_name: str = Field(min_length=2, max_length=200)
    registration_number: str = Field(default="", max_length=150)
    registration_explanation: str = Field(default="", max_length=1000)
    recruiter_name: str = Field(min_length=2, max_length=100)
    recruiter_position: str = Field(min_length=2, max_length=150)
    contact_email: Email
    contact_phone: str = Field(min_length=5, max_length=80)

    @model_validator(mode="after")
    def registration(self):
        if not self.registration_number and len(self.registration_explanation) < 10:
            raise ValueError("Provide a registration number or explain why registration is not applicable")
        return self


class VerificationOut(CompanyOut):
    user_id: int
    legal_name: str
    registration_number: str
    registration_explanation: str
    recruiter_name: str
    recruiter_position: str
    contact_email: str
    contact_phone: str
    verification_version: int
    submitted_at: datetime | None
    review_reason: str


class Decision(Strict):
    version: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=2000)
    evidence: str = Field(default="", max_length=4000)


class EmployerDecision(Decision):
    action: Literal["approve", "reject", "suspend", "reopen", "request_info"]
    company_checked: bool = False
    representative_checked: bool = False


class ListingDecision(Decision):
    action: Literal["approve", "hide", "restore"]


class ReportInput(Strict):
    category: Literal["payment_request", "impersonation", "personal_data", "misleading", "other"]
    details: str = Field(min_length=10, max_length=2000)


class ReportDecision(Decision):
    action: Literal["resolved", "dismissed"]


class ReportOut(Output):
    id: int
    listing_id: int
    category: str
    details: str
    status: str
    resolution: str
    version: int
    created_at: datetime
    updated_at: datetime


class AuditOut(Output):
    id: int
    actor_id: int
    target_type: str
    target_id: int
    action: str
    reason: str
    evidence: str
    created_at: datetime


class AdminSummary(Output):
    pending_employers: int
    suspended_employers: int
    flagged_listings: int
    open_reports: int
