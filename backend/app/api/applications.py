from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import csrf, current_user, employer, student
from app.db.session import get_db
from app.jobs.delivery import process_event
from app.models import (
    Application,
    EmailOutbox,
    EmployerProfile,
    Internship,
    Notification,
    StatusHistory,
    StudentProfile,
    User,
    utcnow,
)
from app.schemas import Apply, CoverEdit, StatusChange, Version
from app.schemas.responses import ApplicationOut, Page
from app.services.events import notify
from app.services.serialization import row_dict

router = APIRouter(prefix="/applications", tags=["Applications"])


def scoped(db, user, identifier, lock=False):
    application_access(db, user)
    query = select(Application).join(Internship).where(Application.id == identifier)
    query = (
        query.where(Application.student_id == user.id)
        if user.role == "student"
        else query.where(Internship.employer_id == user.id)
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise HTTPException(404, "Application not found")
    return item


def application_access(db, user):
    if user.role not in ("student", "employer"):
        raise HTTPException(403, "Application access requires a student or employer account")
    if user.role == "employer":
        company = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
        if company.verification_status == "suspended":
            raise HTTPException(403, "Employer account suspended")


def application_dict(db, item, user):
    data = row_dict(item)
    listing = db.get(Internship, item.internship_id)
    applicant = db.get(User, item.student_id)
    data["internship_title"], data["student_name"] = listing.title, applicant.name
    data["listing_status"] = listing.status
    data["history"] = [
        row_dict(x)
        for x in db.scalars(
            select(StatusHistory)
            .where(StatusHistory.application_id == item.id)
            .order_by(StatusHistory.event_version)
        )
    ]
    events = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_id == item.student_id, Notification.type == "application_status"
            )
        )
    )
    data["events"] = []
    for event in events:
        if event.related.get("application_id") == item.id:
            output = row_dict(event, ("event_key",))
            outbox = db.scalar(select(EmailOutbox).where(EmailOutbox.notification_id == event.id))
            output["email_state"] = outbox.state if outbox else "disabled"
            data["events"].append(output)
    return data


@router.post("", response_model=ApplicationOut, status_code=201, dependencies=[Depends(csrf)])
def apply(
    data: Apply, tasks: BackgroundTasks, user: User = Depends(student), db: Session = Depends(get_db)
) -> dict:
    employer_id = db.scalar(select(Internship.employer_id).where(Internship.id == data.internship_id))
    company = db.scalar(
        select(EmployerProfile).where(EmployerProfile.user_id == employer_id).with_for_update()
    )
    listing = db.scalar(select(Internship).where(Internship.id == data.internship_id).with_for_update())
    if (
        not listing
        or listing.deleted_at
        or listing.status != "active"
        or listing.admin_hidden
        or not company
        or company.verification_status != "approved"
        or (listing.deadline and listing.deadline <= utcnow())
        or db.get(User, listing.employer_id).deactivated_at
    ):
        raise HTTPException(409, "This internship is not accepting applications")
    if db.scalar(
        select(Application).where(Application.student_id == user.id, Application.internship_id == listing.id)
    ):
        raise HTTPException(
            409, "You already applied to this internship, including any withdrawn application"
        )
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if not (profile.extracted_skills or profile.coursework or profile.projects):
        raise HTTPException(409, "Add skills, coursework, or projects to your profile before applying")
    snapshot = {k: getattr(profile, k) for k in ("extracted_skills", "coursework", "projects", "degree")}
    item = Application(
        student_id=user.id,
        internship_id=listing.id,
        cover_message=data.cover_message,
        profile_snapshot=snapshot,
    )
    db.add(item)
    db.flush()
    db.add(
        StatusHistory(
            application_id=item.id,
            previous_status=None,
            new_status="applied",
            actor_id=user.id,
            event_version=1,
        )
    )
    notify(
        db,
        listing.employer_id,
        f"application:{item.id}:new",
        "new_application",
        "New internship application",
        f"{user.name} applied to {listing.title}.",
        {"application_id": item.id, "internship_id": listing.id},
        email=False,
    )
    db.commit()
    return application_dict(db, item, user)


@router.get("", response_model=Page[ApplicationOut])
def list_applications(
    status: str = Query("", pattern="^(|applied|viewed|accepted|rejected|withdrawn)$"),
    internship_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    application_access(db, user)
    query = select(Application).join(Internship)
    query = (
        query.where(Application.student_id == user.id)
        if user.role == "student"
        else query.where(Internship.employer_id == user.id)
    )
    if status:
        query = query.where(Application.status == status)
    if internship_id:
        query = query.where(Application.internship_id == internship_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Application.applied_at.desc(), Application.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [application_dict(db, item, user) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{identifier}", response_model=ApplicationOut)
def detail(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return application_dict(db, scoped(db, user, identifier), user)


@router.patch("/{identifier}", response_model=ApplicationOut, dependencies=[Depends(csrf)])
def cover(
    identifier: int, data: CoverEdit, user: User = Depends(student), db: Session = Depends(get_db)
) -> dict:
    item = scoped(db, user, identifier, True)
    if item.status != "applied" or item.version != data.version:
        raise HTTPException(
            409, "Cover message can only be edited before review; reload if the application changed"
        )
    item.cover_message, item.version = data.cover_message, item.version + 1
    db.commit()
    return application_dict(db, item, user)


def transition(db, item, user, status, version, tasks, note=None):
    if item.status == status:
        return application_dict(db, item, user)
    if item.version != version:
        raise HTTPException(409, "Application changed. Reload first.")
    if item.status not in ("applied", "viewed") or (item.status == "viewed" and status == "viewed"):
        raise HTTPException(409, "This application status is terminal or the transition is invalid")
    previous, item.status, item.version = item.status, status, item.version + 1
    if status == "withdrawn":
        item.withdrawn_at = utcnow()
    db.add(
        StatusHistory(
            application_id=item.id,
            previous_status=previous,
            new_status=status,
            actor_id=user.id,
            employer_note=note,
            event_version=item.version,
        )
    )
    listing = db.get(Internship, item.internship_id)
    event = notify(
        db,
        item.student_id,
        f"application:{item.id}:v{item.version}",
        "application_status",
        f"Application {status}",
        f"Your application for {listing.title} is now {status}."
        + (f" Employer note: {note}" if note else ""),
        {"application_id": item.id, "internship_id": listing.id, "version": item.version, "status": status},
        feedback=status in ("viewed", "rejected"),
    )
    if status == "withdrawn":
        notify(
            db,
            listing.employer_id,
            f"withdrawal:{item.id}",
            "withdrawal",
            "Application withdrawn",
            f"An applicant withdrew from {listing.title}.",
            {"application_id": item.id},
            email=False,
        )
    db.commit()
    if event:
        tasks.add_task(process_event, event.id)
    return application_dict(db, item, user)


@router.put("/{identifier}/status", response_model=ApplicationOut, dependencies=[Depends(csrf)])
def status(
    identifier: int,
    data: StatusChange,
    tasks: BackgroundTasks,
    user: User = Depends(employer),
    db: Session = Depends(get_db),
) -> dict:
    return transition(
        db, scoped(db, user, identifier, True), user, data.status, data.version, tasks, data.employer_note
    )


@router.post("/{identifier}/withdraw", response_model=ApplicationOut, dependencies=[Depends(csrf)])
def withdraw(
    identifier: int,
    data: Version,
    tasks: BackgroundTasks,
    user: User = Depends(student),
    db: Session = Depends(get_db),
) -> dict:
    return transition(db, scoped(db, user, identifier, True), user, "withdrawn", data.version, tasks)
