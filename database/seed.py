"""Idempotent importer. Actual Kaggle headers inspected on 2026-09-20."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import pandas as pd
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import settings
from app.core.security import passwords
from app.db.session import SessionLocal
from app.models import EmployerProfile, Internship, StudentProfile, User
from app.schemas import ListingInput
from app.services.skills import infer, normalize

ALIASES = {
    "title": ["internship_title", "title", "job_title", "position", "role"],
    "company": ["company_name", "company", "organization"],
    "description": ["description", "job_description", "about_internship"],
    "skills": ["skills", "required_skills", "skill_required"],
    "location": ["location", "locations", "city"],
    "stipend": ["stipend", "salary", "compensation"],
    "duration": ["duration", "internship_duration"],
    "deadline": ["deadline", "apply_by", "application_deadline"],
    "source_id": ["source_id", "id", "internship_id"],
}
PASSWORD = "NovaRouteDemo!2026"


def header(value):
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def mapping(columns, overrides=None):
    normalized = {header(c): c for c in columns}
    selected = {
        key: next((normalized[a] for a in aliases if a in normalized), None)
        for key, aliases in ALIASES.items()
    }
    for key, value in (overrides or {}).items():
        if key not in ALIASES or value not in columns:
            raise ValueError(f"Invalid mapping: {key} -> {value}")
        selected[key] = value
    if not selected["title"] or not selected["company"]:
        raise ValueError("CSV must provide title and company columns; use --mapping JSON to override aliases")
    return selected


def skill_values(value):
    if not value:
        return []
    if value.strip().startswith("["):
        result = json.loads(value)
        if not isinstance(result, list) or not all(isinstance(s, str) for s in result):
            raise ValueError("Skills must be a JSON array of strings")
        return normalize(result)
    return normalize(re.split(r"[,;|]", value))


def prepare(row, selected, kind):
    get = lambda key: str(row.get(selected.get(key), "") or "").strip()
    title, company = get("title"), get("company")
    if not title or not company:
        raise ValueError("Missing title or company")
    location = get("location") or "Not specified"
    duration = get("duration") or "Not specified"
    source_description = get("description")
    inferred = not bool(get("skills"))
    skills = infer(title + " " + source_description) if inferred else skill_values(get("skills"))
    # Keep dataset sampling technical; unknown requirements remain unknown.
    if not skills and not re.search(
        r"software|web|data|development|engineering|cloud|cyber|testing|programming|design|machine learning",
        title,
        re.I,
    ):
        raise ValueError("Nontechnical or insufficient technical evidence")
    description = (
        source_description
        or f"Historical dataset example: {title} at {company}. Source location: {location}. Duration: {duration}. Source stipend: {get('stipend') or 'Not specified'}. Responsibilities and requirements were not provided by the source. This is a demonstration record, not a verified current vacancy."
    )
    stipend = get("stipend")
    # Preserve the original text; variable/one-time stipend amounts are not guessed.
    low = high = currency = None
    matched = re.fullmatch(r"(?:\u20b9|INR)\s*([\d,]+)(?:\s*-\s*([\d,]+))?\s*/month", stipend, re.I)
    if matched:
        low = matched[1].replace(",", "")
        high = (matched[2] or matched[1]).replace(",", "")
        currency = "INR"
    deadline = None
    if get("deadline"):
        parsed = pd.to_datetime(get("deadline"), errors="coerce", utc=True)
        if not pd.isna(parsed):
            deadline = parsed.to_pydatetime()
    mode = (
        "remote"
        if re.search("work from home|remote", location, re.I)
        else "hybrid"
        if "hybrid" in location.lower()
        else "onsite"
    )
    values = ListingInput(
        title=title,
        description=description,
        required_skills=skills,
        location=location,
        work_mode=mode,
        duration=duration,
        stipend_min=low,
        stipend_max=high,
        currency=currency,
        deadline=deadline,
    ).model_dump()
    stable = get("source_id") or json.dumps(
        {"title": title, "company": company, "location": location, "duration": duration, "stipend": stipend},
        sort_keys=True,
    )
    return (
        values,
        sha256((kind + ":" + stable).encode()).hexdigest(),
        {
            "kind": kind,
            "source_company": company,
            "skills_inferred": inferred,
            "description_assembled": not bool(source_description),
            "source_stipend": stipend,
            "source_deadline": get("deadline"),
            "historical": kind == "kaggle",
            "source_url": "https://www.kaggle.com/datasets/everydaycodings/internship-opportunities-dataset"
            if kind == "kaggle"
            else "synthetic-local-v1",
        },
    )


def account(db, email, role, name):
    user = db.scalar(select(User).where(User.email == email))
    if user:
        if not user.is_demo or user.role != role:
            raise ValueError("Seed email collides with a non-demo account")
        return user
    user = User(email=email, role=role, name=name, password_hash=passwords.hash(PASSWORD), is_demo=True)
    db.add(user)
    db.flush()
    return user


def seed_accounts(db):
    employer = account(db, "employer@novaroute.test", "employer", "Nova Labs Demo")
    if not db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == employer.id)):
        db.add(
            EmployerProfile(
                user_id=employer.id,
                company_name="Nova Labs · Demo Employer",
                verification_status="approved",
                review_reason="Synthetic demo employer only; not an independently verified company.",
                industry="Software & learning",
                location="Remote",
                description="A fictional employer for capstone demonstrations. Imported listings are historical examples; this account does not represent their source companies.",
            )
        )
    students = [
        (
            "student@novaroute.test",
            "Maya Chen",
            ["Python", "FastAPI", "React", "SQL", "Git"],
            ["Data Structures", "Software Engineering", "Database Systems"],
            "Internship platform",
            "Built an internship platform with Python FastAPI, React and SQL. Implemented REST APIs, authentication, and tests.",
        ),
        (
            "database@novaroute.test",
            "Arun Patel",
            ["SQL", "MySQL", "PostgreSQL", "Python"],
            ["Database Systems", "Data Modeling"],
            "Library database",
            "Designed relational tables, indexes, and secure SQL queries for a library management system.",
        ),
        (
            "data@novaroute.test",
            "Leah Morgan",
            ["Python", "pandas", "NumPy", "PyTorch", "Machine Learning"],
            ["Linear Algebra", "Machine Learning", "Statistics"],
            "Motion analysis",
            "Analyzed human motion using computer vision features and evaluated a neural classifier on a small dataset.",
        ),
    ]
    for email, name, skills, courses, title, description in students:
        user = account(db, email, "student", name)
        if not db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id)):
            db.add(
                StudentProfile(
                    user_id=user.id,
                    extracted_skills=skills,
                    coursework=courses,
                    projects=[{"title": title, "description": description, "technologies": skills}],
                    degree="BSc Computer Science",
                    location="Remote",
                    preferences={"work_mode": "remote", "interests": "Technical internships"},
                )
            )
    return employer


def import_dataframe(frame, limit=25, seed=42, kind="kaggle", overrides=None):
    if settings().environment == "production":
        raise ValueError("Development seeding is disabled in production")
    frame = frame.fillna("").astype(str)
    selected = mapping(frame.columns, overrides)
    print("Selected header mapping:", json.dumps(selected))
    stats = {"imported": 0, "skipped": 0, "updated": 0, "duplicates": 0}
    with SessionLocal() as db:
        employer = seed_accounts(db)
        usable = 0
        for row in frame.sample(frac=1, random_state=seed).to_dict("records"):
            if usable >= limit:
                break
            try:
                values, key, provenance = prepare(row, selected, kind)
            except (ValueError, TypeError):
                stats["skipped"] += 1
                continue
            usable += 1
            if db.scalar(select(Internship).where(Internship.source_key == key)):
                stats["duplicates"] += 1
                continue
            # Seeded historical/synthetic records are explicitly curated demo fixtures.
            db.add(
                Internship(
                    employer_id=employer.id,
                    **values,
                    status="active",
                    source_key=key,
                    provenance=provenance,
                    moderation={
                        "classification": "valid",
                        "risk_reasons": [],
                        "suggested_changes": [],
                        "seed_fixture": True,
                    },
                    moderation_model="curated-demo-seed",
                )
            )
            db.flush()
            stats["imported"] += 1
        db.commit()
    return stats


def import_csv(path, limit=25, seed=42, demo=False, overrides=None):
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    kind = "synthetic" if demo else "kaggle"
    return import_dataframe(frame, limit=limit, seed=seed, kind=kind, overrides=overrides)


def load_kaggle_dataset(file_path="internship.csv"):
    import kagglehub
    from kagglehub import KaggleDatasetAdapter

    print("Loading dataset from Kaggle via kagglehub...")
    target_file = file_path if file_path else "internship.csv"
    loader = getattr(kagglehub, "dataset_load", getattr(kagglehub, "load_dataset", None))
    df = loader(
        KaggleDatasetAdapter.PANDAS,
        "everydaycodings/internship-opportunities-dataset",
        target_file,
    )
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", type=Path)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--kaggle", action="store_true", help="Download and load dataset using kagglehub")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--file-path", default="internship.csv", help="Relative file path within Kaggle dataset (default: internship.csv)"
    )
    parser.add_argument(
        "--mapping", type=Path, help="JSON object mapping logical fields to exact CSV headers"
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= 10000:
        parser.error("limit must be 1..10000")
    overrides = json.loads(args.mapping.read_text()) if args.mapping else None
    try:
        if args.kaggle:
            df = load_kaggle_dataset(args.file_path)
            stats = import_dataframe(df, args.limit, args.seed, kind="kaggle", overrides=overrides)
        else:
            stats = import_csv(
                args.csv or ROOT / "database/data/synthetic-internships.csv",
                args.limit,
                args.seed,
                args.demo,
                overrides,
            )
        print(json.dumps(stats, indent=2))
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        parser.exit(2, f"Import failed: {exc}\n")
