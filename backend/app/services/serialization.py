from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import EmployerProfile, User


def row_dict(obj, exclude=()):
    result = {}
    for column in obj.__table__.columns:
        if column.name in exclude:
            continue
        value = getattr(obj, column.name)
        if isinstance(value, datetime):
            value = value.isoformat() + "Z"
        elif isinstance(value, Decimal):
            value = str(value)
        result[column.name] = value
    return result


def listing_dict(db, listing, owner=False):
    data = row_dict(listing, () if owner else ("moderation", "moderation_model", "source_key"))
    company = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == listing.employer_id))
    # Explicit allowlist: private verification contact details never reach student APIs.
    data["company"] = (
        {
            k: getattr(company, k)
            for k in (
                "company_name",
                "website",
                "industry",
                "location",
                "description",
                "verification_status",
                "reviewed_at",
            )
        }
        if company
        else {"company_name": "Employer"}
    )
    data["company"]["demo_company"] = db.get(User, listing.employer_id).is_demo
    return data
