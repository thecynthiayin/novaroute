import logging

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Application, EmployerProfile, Internship, StudentProfile, User, utcnow
from app.services.embeddings import EmbeddingUnavailable, embeddings, listing_text, profile_text, rank
from app.services.events import notify
from app.services.serialization import listing_dict
from app.services.skills import evidence


def eligible_query():
    query = (
        select(Internship)
        .join(User, User.id == Internship.employer_id)
        .join(EmployerProfile, EmployerProfile.user_id == User.id)
        .where(
            Internship.status == "active",
            Internship.admin_hidden.is_(False),
            EmployerProfile.verification_status == "approved",
            Internship.deleted_at.is_(None),
            User.deactivated_at.is_(None),
            or_(Internship.deadline.is_(None), Internship.deadline > utcnow()),
        )
    )
    if settings().environment == "production":
        query = query.where(User.is_demo.is_(False))
    return query


def recommendations(db, user_id, limit=10, threshold=None):
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if not profile or not (profile.extracted_skills or profile.coursework or profile.projects):
        return []
    listings = list(
        db.scalars(
            eligible_query().where(
                ~Internship.id.in_(select(Application.internship_id).where(Application.student_id == user_id))
            )
        )
    )
    # Release the read transaction before CPU/model work.
    db.commit()
    if not listings:
        return []
    vector = embeddings.encode(profile_text(profile))
    ranked = rank(
        vector,
        [(item.id, embeddings.encode(listing_text(item))) for item in listings],
        threshold if threshold is not None else settings().recommendation_min_score,
        limit,
    )
    by_id = {item.id: item for item in listings}
    skills = profile.extracted_skills + [s for p in profile.projects for s in p["technologies"]]
    results = []
    for identifier, score in ranked:
        item = by_id[identifier]
        matched, missing = evidence(skills, item.required_skills)
        results.append(
            {
                "internship": listing_dict(db, item),
                "similarity": score,
                "percentage": round(score * 100, 1),
                "matched_skills": matched,
                "missing_skills": missing,
                "explanation": (
                    "Confirmed skill overlap: " + ", ".join(matched)
                    if matched
                    else "Semantic alignment with your confirmed coursework and projects; no exact required-skill overlap."
                )
                + (". Requirements to develop: " + ", ".join(missing) if missing else ""),
                "score_help": "Semantic similarity, not hiring probability or measured accuracy.",
            }
        )
    return results


def evaluate_alerts(student_id=None, listing_id=None):
    try:
        with SessionLocal() as db:
            ids = (
                [student_id]
                if student_id
                else list(
                    db.scalars(select(User.id).where(User.role == "student", User.deactivated_at.is_(None)))
                )
            )
        for identifier in ids:
            with SessionLocal() as db:
                results = recommendations(db, identifier, limit=10000)
                for match in results:
                    item = match["internship"]
                    if listing_id and item["id"] != listing_id:
                        continue
                    try:
                        with db.begin_nested():
                            notify(
                                db,
                                identifier,
                                f"match:{identifier}:{item['id']}",
                                "high_match",
                                "A new internship matches your profile",
                                f"{item['title']} has {match['percentage']}% semantic similarity. This is not a hiring probability.",
                                {"internship_id": item["id"], "similarity": match["similarity"]},
                            )
                    except IntegrityError:
                        pass
                db.commit()
        from app.jobs.delivery import retry_pending

        retry_pending(50)
    except EmbeddingUnavailable:
        logging.getLogger(__name__).warning(
            "High-match evaluation deferred: embedding model unavailable. Run retry-matches after model warmup."
        )
