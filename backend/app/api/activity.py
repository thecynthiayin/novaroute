from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import csrf, current_user, student
from app.db.session import get_db
from app.models import Application, Internship, Notification, SavedInternship, StudentProfile, User, utcnow
from app.schemas import OK, Note, NotificationEdit
from app.schemas.responses import (
    CountOut,
    DashboardOut,
    InternshipStates,
    NotificationOut,
    Page,
    RecommendationsOut,
    SavedOut,
)
from app.services.embeddings import EmbeddingUnavailable
from app.services.recommendations import eligible_query, recommendations
from app.services.serialization import listing_dict, row_dict

router = APIRouter(tags=["Recommendations, saved listings, notifications"])


@router.get("/student/internship-states", response_model=InternshipStates)
def internship_states(user: User = Depends(student), db: Session = Depends(get_db)):
    return InternshipStates(
        saved_ids=list(
            db.scalars(select(SavedInternship.internship_id).where(SavedInternship.student_id == user.id))
        ),
        applied_ids=list(
            db.scalars(select(Application.internship_id).where(Application.student_id == user.id))
        ),
    )


@router.get("/student/recommendations", response_model=RecommendationsOut)
def recommended(
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(settings().recommendation_min_score, ge=0, le=1),
    user: User = Depends(student),
    db: Session = Depends(get_db),
) -> dict:
    try:
        items = recommendations(db, user.id, limit, threshold)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    return {"items": items, "threshold": threshold, "strictly_greater": True}


@router.get("/recommendations/{student_id}", response_model=RecommendationsOut)
def recommended_id(
    student_id: int,
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(settings().recommendation_min_score, ge=0, le=1),
    user: User = Depends(student),
    db: Session = Depends(get_db),
) -> dict:
    if student_id != user.id:
        raise HTTPException(403, "You may only request your own recommendations")
    return recommended(limit, threshold, user, db)


@router.get("/student/saved", response_model=Page[SavedOut])
def saved(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(student),
    db: Session = Depends(get_db),
):
    query = select(SavedInternship).where(SavedInternship.student_id == user.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = []
    for item in db.scalars(
        query.order_by(SavedInternship.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ):
        listing = db.get(Internship, item.internship_id)
        available = bool(db.scalar(eligible_query().where(Internship.id == listing.id)))
        items.append(
            {
                **row_dict(item),
                "available": available,
                "internship": listing_dict(db, listing)
                if available
                else {"id": listing.id, "title": listing.title, "status": "unavailable"},
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/student/saved/{identifier}", response_model=SavedOut, dependencies=[Depends(csrf)])
def save(identifier: int, data: Note, user: User = Depends(student), db: Session = Depends(get_db)) -> dict:
    existing = db.scalar(
        select(SavedInternship).where(
            SavedInternship.student_id == user.id, SavedInternship.internship_id == identifier
        )
    )
    if existing:
        return row_dict(existing)
    if not db.scalar(eligible_query().where(Internship.id == identifier)):
        raise HTTPException(409, "Only available internships can be saved")
    item = SavedInternship(student_id=user.id, internship_id=identifier, note=data.note)
    db.add(item)
    db.commit()
    return row_dict(item)


@router.patch("/student/saved/{identifier}", response_model=SavedOut, dependencies=[Depends(csrf)])
def save_note(
    identifier: int, data: Note, user: User = Depends(student), db: Session = Depends(get_db)
) -> dict:
    item = db.scalar(
        select(SavedInternship).where(
            SavedInternship.student_id == user.id, SavedInternship.internship_id == identifier
        )
    )
    if not item:
        raise HTTPException(404, "Saved internship not found")
    item.note = data.note
    db.commit()
    return row_dict(item)


@router.delete("/student/saved/{identifier}", response_model=OK, dependencies=[Depends(csrf)])
def unsave(identifier: int, user: User = Depends(student), db: Session = Depends(get_db)) -> dict:
    item = db.scalar(
        select(SavedInternship).where(
            SavedInternship.student_id == user.id, SavedInternship.internship_id == identifier
        )
    )
    if item:
        db.delete(item)
        db.commit()
    return {"message": "Internship unsaved"}


@router.get("/notifications", response_model=Page[NotificationOut])
def inbox(
    read: str = Query("all", pattern="^(all|unread|read)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    query = select(Notification).where(
        Notification.recipient_id == user.id, Notification.dismissed_at.is_(None)
    )
    if read != "all":
        query = query.where(
            Notification.read_at.is_(None) if read == "unread" else Notification.read_at.is_not(None)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    return {
        "items": [
            row_dict(x, ("event_key",))
            for x in db.scalars(
                query.order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/notifications/count", response_model=CountOut)
def unread(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return {
        "unread": db.scalar(
            select(func.count(Notification.id)).where(
                Notification.recipient_id == user.id,
                Notification.read_at.is_(None),
                Notification.dismissed_at.is_(None),
            )
        )
    }


@router.post("/notifications/read-all", response_model=OK, dependencies=[Depends(csrf)])
def all_read(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    db.execute(
        update(Notification)
        .where(Notification.recipient_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    db.commit()
    return {"message": "All notifications marked read"}


def own_notification(db, user, identifier):
    item = db.scalar(
        select(Notification).where(Notification.id == identifier, Notification.recipient_id == user.id)
    )
    if not item:
        raise HTTPException(404, "Notification not found")
    return item


@router.patch("/notifications/{identifier}", response_model=NotificationOut, dependencies=[Depends(csrf)])
def read_notification(
    identifier: int, data: NotificationEdit, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    item = own_notification(db, user, identifier)
    item.read_at = utcnow() if data.read else None
    db.commit()
    return row_dict(item, ("event_key",))


@router.delete("/notifications/{identifier}", response_model=OK, dependencies=[Depends(csrf)])
def dismiss(identifier: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    own_notification(db, user, identifier).dismissed_at = utcnow()
    db.commit()
    return {"message": "Notification dismissed"}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role == "student":
        profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        completion = (
            sum(
                bool(getattr(profile, key))
                for key in ("extracted_skills", "coursework", "projects", "degree", "location")
            )
            * 20
        )
        counts = {
            "Applications": db.scalar(
                select(func.count(Application.id)).where(Application.student_id == user.id)
            ),
            "Saved internships": db.scalar(
                select(func.count(SavedInternship.id)).where(SavedInternship.student_id == user.id)
            ),
            "Profile completion": completion,
        }
    else:
        counts = {
            "Active listings": db.scalar(
                select(func.count(Internship.id)).where(
                    Internship.employer_id == user.id,
                    Internship.status == "active",
                    Internship.deleted_at.is_(None),
                )
            ),
            "Awaiting review": db.scalar(
                select(func.count(Internship.id)).where(
                    Internship.employer_id == user.id,
                    Internship.status.in_(["pending_ai_review", "flagged"]),
                    Internship.deleted_at.is_(None),
                )
            ),
            "Applications received": db.scalar(
                select(func.count(Application.id)).join(Internship).where(Internship.employer_id == user.id)
            ),
        }
    return {"counts": counts, "recent_events": inbox("all", 1, 4, user, db)["items"]}
