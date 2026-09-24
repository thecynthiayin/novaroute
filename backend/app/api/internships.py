from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.security import csrf, employer, find_session
from app.db.session import get_db
from app.models import EmployerProfile, Internship, User, utcnow
from app.schemas import OK, ListingEdit, ListingInput, Version
from app.schemas.responses import ListingOut, Page
from app.services.embeddings import embeddings
from app.services.moderation import moderate_listing
from app.services.recommendations import eligible_query
from app.services.serialization import listing_dict
from app.services.skills import normalize

router = APIRouter(tags=["Internships"])


def owned(db, identifier, user_id, lock=False):
    query = select(Internship).where(
        Internship.id == identifier, Internship.employer_id == user_id, Internship.deleted_at.is_(None)
    )
    item = db.scalar(query.with_for_update() if lock else query)
    if not item:
        raise HTTPException(404, "Internship not found")
    return item


def listing_page(db, query, page, page_size, owner=False):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    return {
        "items": [
            listing_dict(db, x, owner)
            for x in db.scalars(query.offset((page - 1) * page_size).limit(page_size))
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/internships", response_model=Page[ListingOut])
def browse(
    q: str = Query("", max_length=100),
    skill: str = Query("", max_length=100),
    location: str = Query("", max_length=100),
    work_mode: str = Query("", pattern="^(|remote|hybrid|onsite)$"),
    sort: str = Query("newest", pattern="^(newest|oldest|title)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = eligible_query()
    if q:
        query = query.where(
            or_(
                Internship.title.icontains(q, autoescape=True),
                Internship.description.icontains(q, autoescape=True),
            )
        )
    if skill:
        query = query.where(
            func.lower(cast(Internship.required_skills, String)).contains(skill.lower(), autoescape=True)
        )
    if location:
        query = query.where(Internship.location.icontains(location, autoescape=True))
    if work_mode:
        query = query.where(Internship.work_mode == work_mode)
    order = (
        Internship.title.asc()
        if sort == "title"
        else Internship.created_at.asc()
        if sort == "oldest"
        else Internship.created_at.desc()
    )
    return listing_page(db, query.order_by(order, Internship.id), page, page_size)


@router.get("/employer/internships", response_model=Page[ListingOut])
def mine(
    q: str = Query("", max_length=100),
    status: str = Query("", pattern="^(|active|flagged|closed|pending_ai_review)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(employer),
    db: Session = Depends(get_db),
):
    query = select(Internship).where(Internship.employer_id == user.id, Internship.deleted_at.is_(None))
    if q:
        query = query.where(Internship.title.icontains(q, autoescape=True))
    if status:
        query = query.where(Internship.status == status)
    return listing_page(
        db, query.order_by(Internship.created_at.desc(), Internship.id), page, page_size, True
    )


@router.get("/internships/{identifier}", response_model=ListingOut)
def detail(identifier: int, request: Request, db: Session = Depends(get_db)) -> dict:
    session = find_session(request, db)
    user = db.get(User, session.user_id) if session and session.user_id else None
    item = db.get(Internship, identifier)
    owner = item and user and not user.deactivated_at and item.employer_id == user.id
    if (
        not item
        or item.deleted_at
        or (not owner and not db.scalar(eligible_query().where(Internship.id == identifier)))
    ):
        raise HTTPException(404, "Internship is no longer available")
    return listing_dict(db, item, bool(owner))


@router.post("/internships", response_model=ListingOut, status_code=201, dependencies=[Depends(csrf)])
@router.post("/post-internship", response_model=ListingOut, status_code=201, dependencies=[Depends(csrf)])
def create(
    data: ListingInput, tasks: BackgroundTasks, user: User = Depends(employer), db: Session = Depends(get_db)
) -> dict:
    company = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
    if not company.company_name:
        raise HTTPException(409, "Complete your company profile before posting")
    values = data.model_dump()
    values["required_skills"] = normalize(values["required_skills"])
    item = Internship(employer_id=user.id, **values)
    db.add(item)
    db.commit()
    tasks.add_task(moderate_listing, item.id, item.content_version)
    return listing_dict(db, item, True)


@router.patch("/internships/{identifier}", response_model=ListingOut, dependencies=[Depends(csrf)])
def edit(
    identifier: int,
    data: ListingEdit,
    tasks: BackgroundTasks,
    user: User = Depends(employer),
    db: Session = Depends(get_db),
) -> dict:
    item = owned(db, identifier, user.id, True)
    if item.content_version != data.content_version:
        raise HTTPException(409, "Listing changed. Reload before editing.")
    for key, value in data.model_dump(exclude={"content_version"}).items():
        setattr(item, key, normalize(value) if key == "required_skills" else value)
    item.content_version += 1
    item.status, item.moderation = "pending_ai_review", {}
    db.commit()
    embeddings.invalidate()
    tasks.add_task(moderate_listing, item.id, item.content_version)
    return listing_dict(db, item, True)


@router.post("/internships/{identifier}/{action}", response_model=ListingOut, dependencies=[Depends(csrf)])
def action(
    identifier: int,
    action: str,
    data: Version,
    tasks: BackgroundTasks,
    user: User = Depends(employer),
    db: Session = Depends(get_db),
) -> dict:
    if action not in ("close", "reopen", "review"):
        raise HTTPException(404, "Unknown action")
    item = owned(db, identifier, user.id, True)
    if item.content_version != data.version:
        raise HTTPException(409, "Listing changed. Reload first.")
    item.content_version += 1
    item.status = "closed" if action == "close" else "pending_ai_review"
    item.moderation = {} if action != "close" else item.moderation
    db.commit()
    embeddings.invalidate()
    if action != "close":
        tasks.add_task(moderate_listing, item.id, item.content_version)
    return listing_dict(db, item, True)


@router.delete("/internships/{identifier}", response_model=OK, dependencies=[Depends(csrf)])
def delete(identifier: int, user: User = Depends(employer), db: Session = Depends(get_db)) -> dict:
    item = owned(db, identifier, user.id, True)
    item.deleted_at, item.status = utcnow(), "closed"
    item.content_version += 1
    db.commit()
    embeddings.invalidate()
    return {"message": "Listing removed. Application history is retained."}
