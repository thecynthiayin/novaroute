import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock

import httpx
import pytest
from openai import APITimeoutError
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import EmailOutbox, Internship, Notification, StudentProfile, utcnow
from app.schemas import Extraction, Moderation


def test_provider_timeout_has_bounded_retries(monkeypatch):
    from app.core.config import settings
    from app.services.openrouter import AIError, structured

    config = settings()
    monkeypatch.setattr(config, "openrouter_api_key", "fake-test-key")
    monkeypatch.setattr(config, "openrouter_model", "test-model")
    fake = Mock()
    fake.chat.completions.create.side_effect = APITimeoutError(
        request=httpx.Request("POST", "https://example.test")
    )
    monkeypatch.setattr("app.services.openrouter.OpenAI", lambda **kwargs: fake)
    monkeypatch.setattr("app.services.openrouter.time.sleep", lambda seconds: None)
    with pytest.raises(AIError) as error:
        structured(Extraction, "extract", {})
    assert error.value.kind == "timeout"
    assert fake.chat.completions.create.call_count == 3


def test_stale_ai_result_cannot_activate_new_content(pair, listing, monkeypatch):
    from app.services.moderation import moderate_listing

    with SessionLocal() as db:
        item = db.get(Internship, listing["id"])
        item.status = "pending_ai_review"
        db.commit()

    def delayed_review(data):
        with SessionLocal() as db:
            item = db.get(Internship, listing["id"])
            item.content_version += 1
            item.title = "New content awaiting review"
            db.commit()
        return Moderation(classification="valid", risk_reasons=[], suggested_changes=[])

    monkeypatch.setattr("app.services.moderation.review", delayed_review)
    moderate_listing(listing["id"], 1)
    with SessionLocal() as db:
        item = db.get(Internship, listing["id"])
        assert item.status == "pending_ai_review" and item.content_version == 2


def test_concurrent_decisions_only_one_wins(pair, application):
    employer = pair[0]
    token = employer.get("/api/auth/csrf").json()["csrf_token"]

    def decide(status):
        return employer.put(
            f"/api/applications/{application['id']}/status",
            json={"status": status, "version": 1},
            headers={"Origin": "http://localhost:3000", "X-CSRF-Token": token},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, ["accepted", "rejected"]))
    assert sorted(results) == [200, 409]


def test_outbox_retry_and_active_claim(pair, application, monkeypatch):
    from app.jobs.delivery import deliver, retry_pending

    def fail(*args):
        raise ConnectionError()

    monkeypatch.setattr("app.jobs.delivery.send_email", fail)
    pair[0].mutate("PUT", f"/applications/{application['id']}/status", {"status": "accepted", "version": 1})
    with SessionLocal() as db:
        item = db.scalar(select(EmailOutbox))
        identifier = item.id
        assert item.state == "failed"
        item.state = "sending"
        item.claimed_at = utcnow()
        item.next_attempt_at = utcnow()
        db.commit()
    send = Mock()
    monkeypatch.setattr("app.jobs.delivery.send_email", send)
    deliver(identifier)
    assert send.call_count == 0
    with SessionLocal() as db:
        item = db.get(EmailOutbox, identifier)
        item.claimed_at = utcnow() - timedelta(minutes=11)
        db.commit()
    assert retry_pending(5) == 1
    deliver(identifier)
    assert send.call_count == 1
    with SessionLocal() as db:
        assert db.get(EmailOutbox, identifier).state == "sent"


@pytest.mark.real_model
def test_real_model_high_match_alert(pair, listing, monkeypatch):
    if os.environ.get("RUN_REAL_MODEL") != "1":
        pytest.skip("Opt-in real model check: RUN_REAL_MODEL=1")
    if os.environ.get("RUN_MAILPIT") == "1":
        from app.services.email import send_email

        monkeypatch.setattr("app.jobs.delivery.send_email", send_email)
    import importlib

    import app.services.recommendations as module

    importlib.reload(module)
    with SessionLocal() as db:
        profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == pair[3]["id"]))
        profile.extracted_skills = listing["required_skills"]
        profile.coursework = []
        profile.projects = [
            {
                "title": listing["title"],
                "technologies": listing["required_skills"],
                "description": listing["description"],
            }
        ]
        db.commit()
        matches = module.recommendations(db, pair[3]["id"])
        assert matches and matches[0]["similarity"] > 0.8
        print("Controlled positive-example real cosine:", matches[0]["similarity"])
    module.evaluate_alerts(student_id=pair[3]["id"])
    module.evaluate_alerts(student_id=pair[3]["id"])
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Notification.id)).where(Notification.type == "high_match")) == 1
        if os.environ.get("RUN_MAILPIT") == "1":
            assert db.scalar(select(EmailOutbox)).state == "sent"


@pytest.mark.mailpit
def test_real_mailpit_delivery(pair, application, monkeypatch):
    if os.environ.get("RUN_MAILPIT") != "1":
        pytest.skip("Opt-in local SMTP check: RUN_MAILPIT=1")
    from app.services.email import send_email

    monkeypatch.setattr("app.jobs.delivery.send_email", send_email)
    pair[0].mutate("PUT", f"/applications/{application['id']}/status", {"status": "viewed", "version": 1})
    with SessionLocal() as db:
        assert db.scalar(select(EmailOutbox)).state == "sent"
    messages = httpx.get("http://127.0.0.1:8025/api/v1/messages", timeout=10).json()["messages"]
    assert any(
        m["Subject"] == "Application viewed" and any(to["Address"] == pair[3]["email"] for to in m["To"])
        for m in messages
    )
