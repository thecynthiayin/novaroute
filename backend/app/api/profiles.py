from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import csrf, employer, rate_limit, student
from app.db.session import get_db
from app.models import EmployerProfile, Resume, StudentProfile, User
from app.schemas import OK, CompanyPatch, ExtractionConfirm, ProfilePatch, Version
from app.schemas.responses import CompanyOut, ProfileOut, ResumeOut
from app.services.embeddings import embeddings
from app.services.openrouter import AIError
from app.services.recommendations import evaluate_alerts
from app.services.resumes import display_filename, extract_pdf, parse, private_path, remove_file, store_pdf
from app.services.serialization import row_dict
from app.services.skills import normalize

router = APIRouter(tags=["Profiles and resumes"])


def profile_for(db, user_id, lock=False):
    query = select(StudentProfile).where(StudentProfile.user_id == user_id)
    return db.scalar(query.with_for_update() if lock else query)


def own_resume(db, user_id, identifier):
    item = db.scalar(select(Resume).where(Resume.id == identifier, Resume.student_id == user_id))
    if not item:
        raise HTTPException(404, "Resume not found")
    return item


@router.get("/student/profile", response_model=ProfileOut)
def profile(user: User = Depends(student), db: Session = Depends(get_db)) -> dict:
    return row_dict(profile_for(db, user.id), ("raw_resume_text",))


@router.patch("/student/profile", response_model=ProfileOut, dependencies=[Depends(csrf)])
def edit_profile(
    data: ProfilePatch, tasks: BackgroundTasks, user: User = Depends(student), db: Session = Depends(get_db)
) -> dict:
    profile = profile_for(db, user.id, True)
    if profile.version != data.version:
        raise HTTPException(409, "Your profile changed. Reload before saving.")
    for key, value in data.model_dump(exclude={"version"}).items():
        setattr(profile, key, normalize(value) if key in ("extracted_skills", "coursework") else value)
    profile.version += 1
    db.commit()
    embeddings.invalidate()
    tasks.add_task(evaluate_alerts, student_id=user.id)
    return row_dict(profile, ("raw_resume_text",))


@router.post("/student/profile/clear-resume", response_model=ProfileOut, dependencies=[Depends(csrf)])
def clear_derived(
    data: Version, tasks: BackgroundTasks, user: User = Depends(student), db: Session = Depends(get_db)
) -> dict:
    profile = profile_for(db, user.id, True)
    if profile.version != data.version:
        raise HTTPException(409, "Profile changed. Reload first.")
    derived = profile.resume_derived
    if derived.get("degree") == profile.degree:
        profile.degree = ""
    profile.extracted_skills = [x for x in profile.extracted_skills if x not in derived.get("skills", [])]
    profile.coursework = [x for x in profile.coursework if x not in derived.get("coursework", [])]
    profile.projects = [x for x in profile.projects if x not in derived.get("projects", [])]
    profile.raw_resume_text, profile.resume_derived = None, {}
    profile.version += 1
    db.commit()
    embeddings.invalidate()
    tasks.add_task(evaluate_alerts, student_id=user.id)
    return row_dict(profile, ("raw_resume_text",))


@router.get("/employer/profile", response_model=CompanyOut)
def company(user: User = Depends(employer), db: Session = Depends(get_db)) -> dict:
    return row_dict(db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id)))


@router.patch("/employer/profile", response_model=CompanyOut, dependencies=[Depends(csrf)])
def edit_company(data: CompanyPatch, user: User = Depends(employer), db: Session = Depends(get_db)) -> dict:
    company = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id).with_for_update())
    if company.verification_status == "suspended":
        raise HTTPException(403, "Employer account suspended")
    changed = any(getattr(company, key) != value for key, value in data.model_dump().items())
    if changed:
        company.verification_version += 1
        company.verification_status = "pending"
        company.reviewed_at = None
        company.submitted_at = None
        company.review_reason = "Company profile changed. Submit updated details for review."
    for key, value in data.model_dump().items():
        setattr(company, key, value)
    db.commit()
    return row_dict(company)


@router.post("/upload-resume", response_model=ResumeOut, status_code=201, dependencies=[Depends(csrf)])
def upload(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(student),
    db: Session = Depends(get_db),
) -> dict:
    rate_limit(request, "upload", settings().upload_rate_limit)
    data = file.file.read(settings().upload_max_bytes + 1)
    text = extract_pdf(data)
    profile_version = profile_for(db, user.id).version
    db.commit()
    ref, content_hash = store_pdf(data)
    item = Resume(
        student_id=user.id,
        storage_ref=ref,
        filename=display_filename(file.filename),
        content_hash=content_hash,
        profile_version=profile_version,
        raw_text=text,
        parse_state="processing",
    )
    db.add(item)
    db.commit()
    try:
        extracted = parse(text)
        item.extracted, item.parse_state = extracted.model_dump(), "draft"
    except AIError as exc:
        item.parse_state, item.failure = "failed", str(exc)
    db.commit()
    return {
        **row_dict(item, ("storage_ref", "raw_text")),
        "confirmation_needed": item.parse_state == "draft",
        "ai_mode": settings().ai_mode,
    }


@router.get("/student/resumes", response_model=list[ResumeOut])
def resumes(user: User = Depends(student), db: Session = Depends(get_db)) -> list[dict]:
    return [
        row_dict(x, ("storage_ref", "raw_text"))
        for x in db.scalars(select(Resume).where(Resume.student_id == user.id).order_by(Resume.id.desc()))
    ]


@router.get("/student/resumes/{identifier}", response_model=ResumeOut)
def resume_detail(identifier: int, user: User = Depends(student), db: Session = Depends(get_db)) -> dict:
    return row_dict(own_resume(db, user.id, identifier), ("storage_ref", "raw_text"))


@router.get("/student/resumes/{identifier}/download")
def download(identifier: int, user: User = Depends(student), db: Session = Depends(get_db)):
    item = own_resume(db, user.id, identifier)
    path = private_path(item.storage_ref)
    if not path.exists():
        raise HTTPException(404, "Private file is unavailable")
    return FileResponse(
        path, media_type="application/pdf", filename=item.filename, headers={"Cache-Control": "no-store"}
    )


@router.post("/student/resumes/{identifier}/confirm", response_model=ProfileOut, dependencies=[Depends(csrf)])
def confirm(
    identifier: int,
    data: ExtractionConfirm,
    tasks: BackgroundTasks,
    user: User = Depends(student),
    db: Session = Depends(get_db),
) -> dict:
    profile = profile_for(db, user.id, True)
    item = own_resume(db, user.id, identifier)
    if item.parse_state != "draft":
        raise HTTPException(409, "Only a parsed draft can be confirmed")
    if profile.version != data.version or item.profile_version != data.version:
        raise HTTPException(409, "Profile changed since upload. Upload again or merge the draft manually.")
    # Merge reviewed entries; record only newly introduced entries, preserving prior manual data.
    derived = dict(profile.resume_derived)
    for field, target in (
        ("skills", "extracted_skills"),
        ("coursework", "coursework"),
        ("projects", "projects"),
    ):
        incoming = data.model_dump()[field]
        if field != "projects":
            incoming = normalize(incoming)
        current = getattr(profile, target)
        additions = [x for x in incoming if x not in current]
        setattr(profile, target, current + additions)
        derived[field] = derived.get(field, []) + [x for x in additions if x not in derived.get(field, [])]
    if data.education and not profile.degree:
        profile.degree = "; ".join(data.education)[:200]
        derived["degree"] = profile.degree
    profile.resume_derived = derived
    profile.raw_resume_text = item.raw_text
    profile.version += 1
    item.parse_state = "confirmed"
    item.extracted = data.model_dump(exclude={"version"})
    db.commit()
    embeddings.invalidate()
    tasks.add_task(evaluate_alerts, student_id=user.id)
    return row_dict(profile, ("raw_resume_text",))


@router.delete("/student/resumes/{identifier}", response_model=OK, dependencies=[Depends(csrf)])
def delete_resume(identifier: int, user: User = Depends(student), db: Session = Depends(get_db)) -> dict:
    profile = profile_for(db, user.id, True)
    item = own_resume(db, user.id, identifier)
    remove_file(item.storage_ref)
    db.delete(item)
    profile.raw_resume_text = None
    profile.version += 1
    db.commit()
    embeddings.invalidate()
    return {
        "message": "Private file and extraction deleted. Confirmed entries remain; use Clear resume-derived entries to remove them."
    }
