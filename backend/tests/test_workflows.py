from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Application, EmailOutbox, Internship, Notification, StatusHistory, utcnow


def test_duplicate_application_snapshot_and_ownership(pair, listing, application, register):
    employer, _, student, _ = pair
    assert student.mutate("POST", "/applications", {"internship_id": listing["id"]}).status_code == 409
    other, _ = register()
    unrelated, _ = register("employer")
    assert other.get(f"/api/applications/{application['id']}").status_code == 404
    assert unrelated.get(f"/api/applications/{application['id']}").status_code == 404
    detail = employer.get(f"/api/applications/{application['id']}").json()
    assert detail["profile_snapshot"]["extracted_skills"] == ["Python", "SQL"]
    assert "raw_resume_text" not in detail["profile_snapshot"]
    assert (
        student.mutate(
            "PUT", f"/applications/{application['id']}/status", {"status": "accepted", "version": 1}
        ).status_code
        == 403
    )


def test_status_idempotency_terminal_and_history(pair, application):
    employer, _, student, _ = pair
    path = f"/applications/{application['id']}/status"
    body = {"status": "viewed", "version": 1}
    first = employer.mutate("PUT", path, body)
    assert first.status_code == 200, first.text
    assert employer.mutate("PUT", path, body).status_code == 200
    with SessionLocal() as db:
        assert (
            db.scalar(select(func.count(Notification.id)).where(Notification.type == "application_status"))
            == 1
        )
        assert db.scalar(select(func.count(EmailOutbox.id))) == 1
        assert db.scalar(select(func.count(StatusHistory.id))) == 2
    assert employer.mutate("PUT", path, {"status": "rejected", "version": 1}).status_code == 409
    result = employer.mutate("PUT", path, {"status": "rejected", "version": 2})
    assert result.status_code == 200
    assert employer.mutate("PUT", path, {"status": "accepted", "version": 3}).status_code == 409
    assert (
        student.mutate("POST", f"/applications/{application['id']}/withdraw", {"version": 3}).status_code
        == 409
    )


def test_withdrawal_blocks_reapplication(pair, listing, application):
    student = pair[2]
    assert (
        student.mutate("POST", f"/applications/{application['id']}/withdraw", {"version": 1}).status_code
        == 200
    )
    assert student.mutate("POST", "/applications", {"internship_id": listing["id"]}).status_code == 409
    assert len(student.get(f"/api/applications/{application['id']}").json()["history"]) == 2


@pytest.mark.parametrize("state", ["closed", "flagged", "pending_ai_review", "deleted", "expired"])
def test_unavailable_listing_rejection(pair, listing, state):
    with SessionLocal() as db:
        item = db.get(Internship, listing["id"])
        if state == "deleted":
            item.deleted_at = utcnow()
        elif state == "expired":
            item.deadline = utcnow() - timedelta(days=1)
        else:
            item.status = state
        db.commit()
    assert pair[2].mutate("POST", "/applications", {"internship_id": listing["id"]}).status_code == 409
    assert pair[2].get(f"/api/internships/{listing['id']}").status_code == 404


def test_soft_delete_preserves_application(pair, listing, application, register):
    unrelated, _ = register("employer")
    assert unrelated.mutate("DELETE", f"/internships/{listing['id']}").status_code == 404
    assert pair[0].mutate("DELETE", f"/internships/{listing['id']}").status_code == 200
    assert pair[2].get(f"/api/applications/{application['id']}").status_code == 200


def test_cover_edit_version_and_review(pair, application):
    student = pair[2]
    path = f"/applications/{application['id']}"
    assert student.mutate("PATCH", path, {"cover_message": "Updated", "version": 1}).status_code == 200
    assert student.mutate("PATCH", path, {"cover_message": "Stale", "version": 1}).status_code == 409
    assert pair[0].mutate("PUT", path + "/status", {"status": "viewed", "version": 2}).status_code == 200
    assert student.mutate("PATCH", path, {"cover_message": "Too late", "version": 3}).status_code == 409


def test_email_failure_cannot_undo_status(pair, application, monkeypatch):
    def fail(*args):
        raise ConnectionError("private smtp error")

    monkeypatch.setattr("app.jobs.delivery.send_email", fail)
    response = pair[0].mutate(
        "PUT", f"/applications/{application['id']}/status", {"status": "accepted", "version": 1}
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(Application, application["id"]).status == "accepted"
        outbox = db.scalar(select(EmailOutbox))
        assert outbox.state == "failed" and outbox.retry_count == 1
        assert "private smtp" not in outbox.last_error


def test_feedback_failure_factual_notification(pair, application, monkeypatch):
    from app.services.openrouter import AIError

    def fail(*args):
        raise AIError("timeout")

    monkeypatch.setattr("app.jobs.delivery.generate_feedback", fail)
    assert (
        pair[0]
        .mutate("PUT", f"/applications/{application['id']}/status", {"status": "rejected", "version": 1})
        .status_code
        == 200
    )
    with SessionLocal() as db:
        event = db.scalar(select(Notification).where(Notification.type == "application_status"))
        assert event.feedback_state == "failed" and "rejected" in event.body


def test_saved_notes_and_inbox_privacy(pair, listing, application, register):
    student = pair[2]
    assert student.mutate("POST", f"/student/saved/{listing['id']}", {"note": "Private"}).status_code == 200
    assert (
        student.mutate("PATCH", f"/student/saved/{listing['id']}", {"note": "Updated note"}).status_code
        == 200
    )
    assert student.get("/api/student/saved").json()["items"][0]["note"] == "Updated note"
    assert listing["id"] in student.get("/api/student/internship-states").json()["saved_ids"]
    assert listing["id"] in student.get("/api/student/internship-states").json()["applied_ids"]
    assert student.mutate("DELETE", f"/student/saved/{listing['id']}").status_code == 200
    pair[0].mutate("PUT", f"/applications/{application['id']}/status", {"status": "viewed", "version": 1})
    event = student.get("/api/notifications").json()["items"][0]
    other, _ = register()
    assert other.mutate("PATCH", f"/notifications/{event['id']}", {"read": True}).status_code == 404
    assert student.mutate("POST", "/notifications/read-all").status_code == 200
    assert student.get("/api/notifications/count").json()["unread"] == 0
    assert student.mutate("PATCH", f"/notifications/{event['id']}", {"read": False}).status_code == 200
    assert student.mutate("DELETE", f"/notifications/{event['id']}").status_code == 200
    assert student.get("/api/notifications").json()["total"] == 0


def test_employer_deactivation_closes_listings(pair, listing):
    employer = pair[0]
    assert employer.mutate("POST", "/auth/deactivate", {"password": "TestingPassword!26"}).status_code == 200
    assert employer.get("/api/auth/me").status_code == 401
    with SessionLocal() as db:
        assert db.get(Internship, listing["id"]).status == "closed"
