import importlib.util
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Internship, Notification
from app.services.embeddings import embeddings

spec = importlib.util.spec_from_file_location("seed", Path(__file__).parents[2] / "database/seed.py")
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


def test_actual_header_mapping_inference_and_provenance():
    row = {
        "internship_title": "Java Development",
        "company_name": "Example",
        "location": "Work From Home",
        "start_date": "Immediately",
        "duration": "6 Months",
        "stipend": "\u20b9 30,000 /month",
    }
    mapping = seed.mapping(row.keys())
    values, key, provenance = seed.prepare(row, mapping, "kaggle")
    assert values["required_skills"] == ["Java"]
    assert provenance["description_assembled"] and provenance["skills_inferred"]
    assert str(values["stipend_min"]) == "30000" and values["currency"] == "INR"
    assert values["deadline"] is None and values["work_mode"] == "remote"
    assert len(key) == 64
    with pytest.raises(ValueError):
        seed.mapping(["unknown"])
    with pytest.raises(ValueError):
        seed.skill_values("[1,2]")


def test_seeder_idempotent(db_ready):
    path = Path(__file__).parents[2] / "database/data/synthetic-internships.csv"
    assert seed.import_csv(path, demo=True)["imported"] == 25
    assert seed.import_csv(path, demo=True)["duplicates"] == 25
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Internship.id))) == 25


def test_new_match_event_dedup_and_get_has_no_side_effect(pair, listing, monkeypatch):
    # Restore the function patched by the fixture; controlled embeddings only.
    import importlib

    import app.services.recommendations as module

    importlib.reload(module)
    monkeypatch.setattr(embeddings, "encode", lambda text: np.array([1.0, 0.0]))
    module.evaluate_alerts(student_id=pair[3]["id"])
    module.evaluate_alerts(student_id=pair[3]["id"])
    pair[2].get("/api/student/recommendations")
    pair[2].get("/api/student/recommendations")
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Notification.id)).where(Notification.type == "high_match")) == 1
