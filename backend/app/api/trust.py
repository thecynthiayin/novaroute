"""Human employer verification and incident review. No automated identity claims."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import admin, csrf, rate_limit, role, student
from app.db.session import get_db
from app.jobs.delivery import retry_pending
from app.models import AdminAudit, Application, EmployerProfile, Internship, ListingReport, User, utcnow
from app.schemas.responses import ListingOut, Page
from app.schemas.trust import (
    AdminSummary,
    AuditOut,
    EmployerDecision,
    ListingDecision,
    ReportDecision,
    ReportInput,
    ReportOut,
    VerificationInput,
    VerificationOut,
)
from app.services.events import notify
from app.services.recommendations import eligible_query, evaluate_alerts
from app.services.serialization import listing_dict

router = APIRouter(tags=["Trust and safety"])


def company_for(db, identifier, lock=False):
    query = select(EmployerProfile).where(EmployerProfile.user_id == identifier)
    item = db.scalar(query.with_for_update() if lock else query)
    if not item or db.get(User, identifier).deactivated_at:
        raise HTTPException(404, "Employer not found")
    return item


def check_version(actual, expected):
    if actual != expected:
        raise HTTPException(409, "This record changed. Refresh before making a decision.")


def audit(db, actor, kind, identifier, action, reason, evidence=""):
    item = AdminAudit(
        actor_id=actor.id,
        target_type=kind,
        target_id=identifier,
        action=action,
        reason=reason,
        evidence=evidence,
    )
    db.add(item)
    db.flush()
    return item


def page_of(db, query, page, size, serializer=lambda item: item):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return {
        "items": [serializer(x) for x in db.scalars(query.offset((page - 1) * size).limit(size))],
        "total": total,
        "page": page,
        "page_size": size,
    }


def alert_applicants(db, query, event_id, body):
    for student_id in db.scalars(query.distinct()):
        notify(
            db,
            student_id,
            f"safety:{event_id}:{student_id}",
            "safety_update",
            "An internship you applied to is under review",
            body,
            {},
        )


@router.get("/employer/verification", response_model=VerificationOut)
def verification(user: User = Depends(role("employer")), db: Session = Depends(get_db)):
    return company_for(db, user.id)


@router.post("/employer/verification", response_model=VerificationOut, dependencies=[Depends(csrf)])
def submit(data: VerificationInput, user: User = Depends(role("employer")), db: Session = Depends(get_db)):
    company = company_for(db, user.id, True)
    check_version(company.verification_version, data.version)
    if company.verification_status == "suspended":
        raise HTTPException(403, "An administrator must reopen your verification before resubmission")
    if not company.company_name or not company.website or not company.location:
        raise HTTPException(409, "Save a company name, website and location in your company profile first")
    for key, value in data.model_dump(exclude={"version"}).items():
        setattr(company, key, value)
    company.verification_status = "pending"
    company.verification_version += 1
    company.submitted_at, company.reviewed_at = utcnow(), None
    company.review_reason = "Verification submitted. Listings remain unpublished until approval."
    audit(db, user, "employer", user.id, "submit", "Employer submitted verification details")
    db.commit()
    return company


@router.get("/admin/summary", response_model=AdminSummary)
def summary(user: User = Depends(admin), db: Session = Depends(get_db)):
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where))

    return {
        "pending_employers": count(
            EmployerProfile,
            EmployerProfile.verification_status == "pending",
            EmployerProfile.submitted_at.is_not(None),
        ),
        "suspended_employers": count(EmployerProfile, EmployerProfile.verification_status == "suspended"),
        "flagged_listings": count(
            Internship,
            Internship.status.in_(["flagged", "pending_ai_review"]),
            Internship.deleted_at.is_(None),
        ),
        "open_reports": count(ListingReport, ListingReport.status == "open"),
    }


@router.get("/admin/employers", response_model=Page[VerificationOut])
def employers(
    status: str = Query("pending", pattern="^(|pending|approved|rejected|suspended)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    query = (
        select(EmployerProfile)
        .join(User, User.id == EmployerProfile.user_id)
        .where(User.deactivated_at.is_(None))
    )
    if status:
        query = query.where(EmployerProfile.verification_status == status)
    return page_of(db, query.order_by(EmployerProfile.updated_at.desc(), EmployerProfile.id), page, page_size)


@router.post(
    "/admin/employers/{identifier}/decision", response_model=VerificationOut, dependencies=[Depends(csrf)]
)
def decide_employer(
    identifier: int,
    data: EmployerDecision,
    tasks: BackgroundTasks,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    company = company_for(db, identifier, True)
    check_version(company.verification_version, data.version)
    if data.action == "approve" and (
        company.verification_status != "pending" or not company.submitted_at
    ):
        raise HTTPException(409, "Only a submitted pending verification can be approved")
    if data.action == "request_info" and (
        company.verification_status != "pending" or not company.submitted_at
    ):
        raise HTTPException(409, "Only a submitted pending verification can request more info")
    if data.action == "reject" and company.verification_status != "pending":
        raise HTTPException(409, "Only pending verifications can be rejected")
    if data.action == "reopen" and company.verification_status not in ("suspended", "rejected"):
        raise HTTPException(409, "Only suspended or rejected accounts can be reopened")
    if data.action == "suspend" and company.verification_status == "suspended":
        raise HTTPException(409, "Employer is already suspended")
    if data.action == "approve" and (
        not data.company_checked or not data.representative_checked or len(data.evidence.strip()) < 20
    ):
        raise HTTPException(
            422, "Record independent evidence and confirm both the company and representative checks"
        )
    company.verification_status = {
        "approve": "approved",
        "reject": "rejected",
        "suspend": "suspended",
        "reopen": "pending",
        "request_info": "pending",
    }[data.action]
    company.verification_version += 1
    company.reviewed_at = utcnow() if data.action in ("approve", "reject", "suspend") else None
    company.review_reason = data.reason
    if data.action == "reopen":
        company.submitted_at = None
    # If rejecting a pending employer without submission, set submitted_at for audit trail
    if data.action == "reject" and not company.submitted_at:
        company.submitted_at = utcnow()
    event = audit(db, user, "employer", identifier, data.action, data.reason, data.evidence)
    notify(
        db,
        identifier,
        f"verification:{event.id}",
        "employer_verification",
        "Employer verification updated",
        f"Status: {company.verification_status}. {data.reason}",
        {},
    )
    if data.action == "suspend":
        alert_applicants(
            db,
            select(Application.student_id).join(Internship).where(Internship.employer_id == identifier),
            event.id,
            "An employer you applied to has been suspended while the platform reviews safety concerns. Avoid sending payments or sensitive information. Contact platform support for help.",
        )
    db.commit()
    tasks.add_task(retry_pending, 100)
    if data.action == "approve":
        tasks.add_task(evaluate_alerts)
    return company


@router.get("/admin/listings", response_model=Page[ListingOut])
def listings(
    status: str = Query("flagged", pattern="^(|flagged|pending_ai_review|active|closed|hidden)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    query = select(Internship).where(Internship.deleted_at.is_(None))
    if status == "hidden":
        query = query.where(Internship.admin_hidden.is_(True))
    elif status:
        query = query.where(Internship.status == status)
    return page_of(
        db,
        query.order_by(Internship.updated_at.desc(), Internship.id),
        page,
        page_size,
        lambda x: listing_dict(db, x, True),
    )


@router.post("/admin/listings/{identifier}/decision", response_model=ListingOut, dependencies=[Depends(csrf)])
def decide_listing(
    identifier: int,
    data: ListingDecision,
    tasks: BackgroundTasks,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    employer_id = db.scalar(select(Internship.employer_id).where(Internship.id == identifier))
    if employer_id is None:
        raise HTTPException(404, "Listing not found")
    company = company_for(db, employer_id, True)
    item = db.scalar(select(Internship).where(Internship.id == identifier).with_for_update())
    if item.deleted_at:
        raise HTTPException(404, "Listing not found")
    check_version(item.content_version, data.version)
    if data.action == "approve":
        if item.status not in ("flagged", "pending_ai_review") or company.verification_status != "approved":
            raise HTTPException(
                409, "Approve the employer first; only pending or flagged content can be approved"
            )
        if len(data.evidence.strip()) < 20:
            raise HTTPException(422, "Explain how you investigated and resolved the content concerns")
        item.status = "active"
        item.moderation = {
            **item.moderation,
            "manual_review": {
                "decision": "approved",
                "at": utcnow().isoformat() + "Z",
                "reason": data.reason,
            },
        }
    elif data.action == "restore":
        if not item.admin_hidden or company.verification_status != "approved" or item.status != "active":
            raise HTTPException(409, "Restoration requires a hidden, active listing and an approved employer")
        item.admin_hidden = False
    else:
        if item.admin_hidden:
            raise HTTPException(409, "Listing is already hidden")
        item.admin_hidden = True
    item.content_version += 1
    event = audit(db, user, "listing", identifier, data.action, data.reason, data.evidence)
    notify(
        db,
        employer_id,
        f"listing-review:{event.id}",
        "listing_review",
        "Listing review updated",
        f"{item.title}: {data.action}. {data.reason}",
        {},
    )
    if data.action == "hide":
        alert_applicants(
            db,
            select(Application.student_id).where(Application.internship_id == identifier),
            event.id,
            f"The listing '{item.title}' has been hidden for safety review. Avoid payments or sensitive-data requests and contact platform support if needed.",
        )
    db.commit()
    tasks.add_task(retry_pending, 100)
    if data.action != "hide":
        tasks.add_task(evaluate_alerts, listing_id=identifier)
    return listing_dict(db, item, True)


@router.post(
    "/internships/{identifier}/report",
    response_model=ReportOut,
    status_code=201,
    dependencies=[Depends(csrf)],
)
def report(
    identifier: int,
    data: ReportInput,
    request: Request,
    user: User = Depends(student),
    db: Session = Depends(get_db),
):
    rate_limit(request, "report", 20)
    existing = db.scalar(
        select(ListingReport).where(
            ListingReport.listing_id == identifier, ListingReport.reporter_id == user.id
        )
    )
    if existing:
        raise HTTPException(409, "You already reported this listing. Track its status in My reports.")
    applied = db.scalar(
        select(Application.id).where(
            Application.student_id == user.id, Application.internship_id == identifier
        )
    )
    if not applied and not db.scalar(eligible_query().where(Internship.id == identifier)):
        raise HTTPException(404, "Listing not found")
    item = ListingReport(listing_id=identifier, reporter_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    return item


@router.get("/student/reports", response_model=Page[ReportOut])
def my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(student),
    db: Session = Depends(get_db),
):
    return page_of(
        db,
        select(ListingReport).where(ListingReport.reporter_id == user.id).order_by(ListingReport.id.desc()),
        page,
        page_size,
    )


@router.get("/admin/reports", response_model=Page[ReportOut])
def reports(
    status: str = Query("open", pattern="^(|open|resolved|dismissed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    query = select(ListingReport)
    if status:
        query = query.where(ListingReport.status == status)
    return page_of(db, query.order_by(ListingReport.id.desc()), page, page_size)


@router.get("/admin/listings/{identifier}", response_model=ListingOut)
def admin_listing(identifier: int, user: User = Depends(admin), db: Session = Depends(get_db)):
    item = db.get(Internship, identifier)
    if not item:
        raise HTTPException(404, "Listing not found")
    return listing_dict(db, item, True)


@router.post("/admin/reports/{identifier}/decision", response_model=ReportOut, dependencies=[Depends(csrf)])
def decide_report(
    identifier: int,
    data: ReportDecision,
    tasks: BackgroundTasks,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    item = db.scalar(select(ListingReport).where(ListingReport.id == identifier).with_for_update())
    if not item:
        raise HTTPException(404, "Report not found")
    check_version(item.version, data.version)
    if item.status != "open":
        raise HTTPException(409, "This report has already been reviewed")
    item.status, item.resolution = data.action, data.reason
    item.version += 1
    event = audit(db, user, "report", identifier, data.action, data.reason, data.evidence)
    notify(
        db,
        item.reporter_id,
        f"report-review:{event.id}",
        "report_update",
        "Your report has been reviewed",
        data.reason,
        {},
    )
    db.commit()
    tasks.add_task(retry_pending, 100)
    return item


@router.get("/admin/audit", response_model=Page[AuditOut])
def history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    return page_of(db, select(AdminAudit).order_by(AdminAudit.id.desc()), page, page_size)
