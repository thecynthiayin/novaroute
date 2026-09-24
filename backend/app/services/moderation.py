import re

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Internship
from app.schemas import Moderation
from app.services.openrouter import AIError, structured


def review(data):
    text = (data["title"] + " " + data["description"]).lower()
    patterns = [
        (
            r"upfront fee|pay to apply|application fee|registration fee|pay.{0,40}(equipment|training|deposit)|(?:equipment|training).{0,30}(fee|payment)",
            "Requests applicant payment",
        ),
        (
            r"your password|login credentials|one.time password|send.{0,30}(otp|bank details|passport|national id)",
            "Requests private credentials or sensitive identity data",
        ),
        (
            r"guaranteed job|guaranteed income|no work.{0,30}(income|salary)",
            "Makes an implausible employment guarantee",
        ),
        (
            r"gift card|send.{0,30}(crypto|bitcoin)|deposit.{0,30}check|check.{0,40}(send|return|transfer)",
            "Potential payment diversion or fake-check scheme",
        ),
    ]
    risks = [label for pattern, label in patterns if re.search(pattern, text)]
    # These are review signals, not a fraud verdict. Human review can resolve false positives.
    if settings().ai_mode == "demo":
        return Moderation(
            classification="flagged" if risks else "valid",
            risk_reasons=risks,
            suggested_changes=["Remove payment, credential, or guarantee requests and clarify the role."]
            if risks
            else [],
        )
    result = structured(
        Moderation,
        "Review internship content for upfront payment requests, credential collection, inconsistent details, and implausible guarantees. An unpaid internship alone is not fraud. This is automated content review, not identity verification or a safety guarantee.",
        data,
    )
    if risks:
        result.classification = "flagged"
        result.risk_reasons = list(dict.fromkeys(risks + result.risk_reasons))[:12]
    return result


def moderate_listing(listing_id, version):
    with SessionLocal() as db:
        listing = db.get(Internship, listing_id)
        if (
            not listing
            or listing.deleted_at
            or listing.content_version != version
            or listing.status != "pending_ai_review"
        ):
            return
        payload = {
            k: getattr(listing, k)
            for k in ("title", "description", "required_skills", "location", "duration")
        }
    try:
        result = review(payload)
        failure = None
    except AIError as exc:
        result, failure = None, str(exc)
    with SessionLocal() as db:
        listing = db.scalar(select(Internship).where(Internship.id == listing_id).with_for_update())
        if (
            not listing
            or listing.deleted_at
            or listing.content_version != version
            or listing.status != "pending_ai_review"
        ):
            return
        listing.moderation = result.model_dump() if result else {"error": failure}
        listing.moderation_model = (
            "demo-rules-v1" if settings().ai_mode == "demo" else settings().openrouter_model
        )
        if result:
            listing.status = "active" if result.classification == "valid" else "flagged"
        db.commit()
        active = listing.status == "active"
    if active:
        from app.services.recommendations import evaluate_alerts

        evaluate_alerts(listing_id=listing_id)
