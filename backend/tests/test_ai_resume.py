from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import HTTPException
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Resume, StudentProfile
from app.schemas import Extraction
from app.services.embeddings import EmbeddingUnavailable, embeddings, rank
from app.services.openrouter import AIError, redact_contacts, structured
from app.services.resumes import extract_pdf
from app.services.skills import normalize


def pdf(text="Python SQL JavaScript. Database systems and software projects."):
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(40, 700, text)
    canvas.save()
    return buffer.getvalue()


def test_resume_invalid_signature_empty_corrupt_size(monkeypatch):
    from app.core.config import settings

    for data in (b"not PDF", b"%PDF-corrupt", pdf("")):
        with pytest.raises(HTTPException):
            extract_pdf(data)
    monkeypatch.setattr(settings(), "upload_max_bytes", 5)
    with pytest.raises(HTTPException) as exc:
        extract_pdf(pdf())
    assert exc.value.status_code == 413


def test_resume_draft_confirmation_and_delete(pair, register):
    student, user = pair[2], pair[3]
    response = student.mutate(
        "POST", "/upload-resume", files={"file": ("../../resume.pdf", pdf(), "application/pdf")}
    )
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft["parse_state"] == "draft" and draft["filename"] == "resume.pdf"
    assert "JavaScript" not in student.get("/api/student/profile").json()["extracted_skills"]
    other, _ = register()
    assert other.get(f"/api/student/resumes/{draft['id']}/download").status_code == 404
    assert pair[0].get(f"/api/student/resumes/{draft['id']}/download").status_code == 403
    confirm = student.mutate(
        "POST",
        f"/student/resumes/{draft['id']}/confirm",
        {**draft["extracted"], "version": draft["profile_version"]},
    )
    assert confirm.status_code == 200, confirm.text
    assert "JavaScript" in confirm.json()["extracted_skills"]
    assert student.mutate("DELETE", f"/student/resumes/{draft['id']}").status_code == 200
    current = student.get("/api/student/profile").json()
    assert "JavaScript" in current["extracted_skills"]
    result = student.mutate("POST", "/student/profile/clear-resume", {"version": current["version"]})
    assert result.json()["extracted_skills"] == ["Python", "SQL"]
    with SessionLocal() as db:
        assert (
            db.scalar(select(StudentProfile).where(StudentProfile.user_id == user["id"])).raw_resume_text
            is None
        )
        assert db.get(Resume, draft["id"]) is None


def test_resume_failure_and_stale_draft_preserve_manual_profile(pair, monkeypatch):
    student = pair[2]
    draft = student.mutate(
        "POST", "/upload-resume", files={"file": ("resume.pdf", pdf(), "application/pdf")}
    ).json()
    profile = student.get("/api/student/profile").json()
    body = {
        k: profile[k]
        for k in (
            "extracted_skills",
            "coursework",
            "projects",
            "degree",
            "location",
            "preferences",
            "version",
        )
    }
    body["extracted_skills"] = ["React"]
    assert student.mutate("PATCH", "/student/profile", body).status_code == 200
    assert (
        student.mutate(
            "POST",
            f"/student/resumes/{draft['id']}/confirm",
            {**draft["extracted"], "version": draft["profile_version"]},
        ).status_code
        == 409
    )

    def fail(*args):
        raise AIError("timeout")

    monkeypatch.setattr("app.api.profiles.parse", fail)
    failed = student.mutate(
        "POST", "/upload-resume", files={"file": ("replacement.pdf", pdf(), "application/pdf")}
    )
    assert failed.json()["parse_state"] == "failed"
    assert student.get("/api/student/profile").json()["extracted_skills"] == ["React"]


def test_ai_invalid_json_and_configuration(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings(), "openrouter_api_key", "")
    with pytest.raises(AIError) as exc:
        structured(Extraction, "extract", {})
    assert exc.value.kind == "configuration"
    monkeypatch.setattr(settings(), "openrouter_api_key", "fake-test-key")
    monkeypatch.setattr(settings(), "openrouter_model", "configured-test-model")
    fake = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"skills":[123]}'))]
                )
            )
        ),
        close=lambda: None,
    )
    monkeypatch.setattr("app.services.openrouter.OpenAI", lambda **kwargs: fake)
    with pytest.raises(AIError) as exc:
        structured(Extraction, "extract", {})
    assert exc.value.kind == "validation"


def test_contact_redaction_and_distinct_java():
    result = redact_contacts("a.person@example.test +66 123 456 789 https://private.test")
    assert "example.test" not in result and "123" not in result and "https" not in result
    assert normalize(["JS", "JavaScript", "Java", "Postgres"]) == ["JavaScript", "Java", "PostgreSQL"]


def test_cosine_threshold_sorting_empty():
    query = np.array([1.0, 0.0])
    candidates = [
        (9, np.array([1.0, 0.0])),
        (2, np.array([1.0, 0.0])),
        (4, np.array([0.8, 0.6])),
        (7, np.array([0.0, 1.0])),
    ]
    assert rank(query, candidates, 0.8, 10) == [(2, 1.0), (9, 1.0)]
    assert rank(query, candidates, 1.0, 10) == []
    assert rank(query, candidates, 0.8, 1) == [(2, 1.0)]


def test_recommendation_scope_and_unavailable(pair, listing, monkeypatch):
    student, user = pair[2], pair[3]
    assert student.get(f"/api/recommendations/{user['id'] + 100}").status_code == 403
    assert student.get("/api/student/recommendations?limit=0").status_code == 422

    def fail(*args):
        raise EmbeddingUnavailable("Unavailable")

    monkeypatch.setattr(embeddings, "encode", fail)
    assert student.get("/api/student/recommendations").status_code == 503
    assert student.get("/api/internships").status_code == 200


def test_moderation_tampering_flagged_pending_stale(pair, listing, monkeypatch):
    employer = pair[0]
    body = {
        k: listing[k]
        for k in (
            "title",
            "description",
            "required_skills",
            "location",
            "work_mode",
            "duration",
            "stipend_min",
            "stipend_max",
            "currency",
            "deadline",
        )
    }
    assert employer.mutate("POST", "/post-internship", {**body, "status": "active"}).status_code == 422
    body["description"] = "You must pay an upfront fee before we review your internship application."
    response = employer.mutate("POST", "/post-internship", body)
    identifier = response.json()["id"]
    assert employer.get(f"/api/internships/{identifier}").json()["status"] == "flagged"
    from app.services.moderation import moderate_listing

    def fail(*args):
        raise AIError("timeout")

    monkeypatch.setattr("app.services.moderation.review", fail)
    employer.mutate("POST", f"/internships/{identifier}/review", {"version": 1})
    assert employer.get(f"/api/internships/{identifier}").json()["status"] == "pending_ai_review"
    employer.mutate("POST", f"/internships/{identifier}/close", {"version": 2})
    moderate_listing(identifier, 2)
    assert employer.get(f"/api/internships/{identifier}").json()["status"] == "closed"


def test_cache_content_hash_and_invalidation(monkeypatch):
    from app.services.embeddings import Embeddings

    calls = []
    fake = SimpleNamespace(
        max_seq_length=4,
        tokenizer=SimpleNamespace(
            encode=lambda text, **kwargs: text.split(), decode=lambda tokens: " ".join(tokens)
        ),
        encode=lambda chunks, **kwargs: calls.append(chunks) or np.ones((len(chunks), 3)),
    )
    service = Embeddings()
    service.model = fake
    service.encode("Python SQL")
    service.encode("Python  SQL")
    assert len(calls) == 1
    service.encode("React SQL")
    assert len(calls) == 2
    service.invalidate()
    service.encode("Python SQL")
    assert len(calls) == 3


def test_profile_edit_invalidates_cache(pair):
    embeddings.cache[("test", "old")] = np.array([1.0])
    profile = pair[2].get("/api/student/profile").json()
    body = {
        k: profile[k]
        for k in (
            "extracted_skills",
            "coursework",
            "projects",
            "degree",
            "location",
            "preferences",
            "version",
        )
    }
    assert pair[2].mutate("PATCH", "/student/profile", body).status_code == 200
    assert not embeddings.cache


def test_student_deactivation_removes_resume_content(pair, application):
    from app.models import Application

    student = pair[2]
    draft = student.mutate(
        "POST", "/upload-resume", files={"file": ("resume.pdf", pdf(), "application/pdf")}
    ).json()
    with SessionLocal() as db:
        from app.services.resumes import private_path

        path = private_path(db.get(Resume, draft["id"]).storage_ref)
    assert path.exists()
    assert student.mutate("POST", "/auth/deactivate", {"password": "TestingPassword!26"}).status_code == 200
    assert not path.exists()
    with SessionLocal() as db:
        assert db.get(Application, application["id"]).profile_snapshot == {}
