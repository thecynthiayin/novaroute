"""Bounded restart recovery. Claims commit before any model/network operation."""

import argparse
from datetime import timedelta

from sqlalchemy import or_, select

from app.db.session import SessionLocal
from app.models import Application, EmailOutbox, Internship, Notification, StatusHistory, User, utcnow
from app.services.email import send_email
from app.services.feedback import generate_feedback
from app.services.openrouter import AIError


def process_feedback(notification_id):
    with SessionLocal() as db:
        event = db.get(Notification, notification_id)
        if not event or event.feedback_state not in ("pending", "failed"):
            return
        application = db.get(Application, event.related["application_id"])
        listing = db.get(Internship, application.internship_id)
        history = db.scalar(
            select(StatusHistory).where(
                StatusHistory.application_id == application.id,
                StatusHistory.event_version == event.related["version"],
            )
        )
        payload = (
            application.profile_snapshot,
            {
                "title": listing.title,
                "required_skills": listing.required_skills,
                "description": listing.description,
            },
            history.new_status,
            history.employer_note,
        )
    try:
        result = generate_feedback(*payload).model_dump()
        state = "complete"
    except AIError:
        result, state = None, "failed"
    with SessionLocal() as db:
        event = db.scalar(select(Notification).where(Notification.id == notification_id).with_for_update())
        if event and event.feedback_state != "complete":
            event.feedback, event.feedback_state = result, state
            db.commit()


def deliver(outbox_id):
    now = utcnow()
    with SessionLocal() as db:
        outbox = db.scalar(
            select(EmailOutbox).where(EmailOutbox.id == outbox_id).with_for_update(skip_locked=True)
        )
        if not outbox or outbox.state in ("sent", "suppressed"):
            return
        if (
            outbox.state == "sending"
            and outbox.claimed_at
            and outbox.claimed_at > now - timedelta(minutes=10)
        ):
            return
        if outbox.next_attempt_at > now:
            return
        outbox.state, outbox.claimed_at = "sending", now
        outbox.retry_count += 1
        event_id = outbox.notification_id
        db.commit()
    process_feedback(event_id)
    with SessionLocal() as db:
        event = db.get(Notification, event_id)
        user = db.get(User, event.recipient_id)
        enabled = user.email_matches if event.type == "high_match" else user.email_applications
        if user.deactivated_at or not enabled:
            db.get(EmailOutbox, outbox_id).state = "suppressed"
            db.commit()
            return
        payload = (
            user.email,
            event.title,
            event.body
            + (
                " AI suggestions are temporarily unavailable; the status update is confirmed."
                if event.feedback_state == "failed"
                else ""
            ),
            event.feedback,
            event.related,
        )
    try:
        send_email(*payload)
        error = None
    except Exception as exc:
        # Never persist a provider response, server hostname, password, or message body.
        error = "Delivery failed (" + type(exc).__name__ + "). Check SMTP configuration and retry."
    with SessionLocal() as db:
        outbox = db.get(EmailOutbox, outbox_id)
        outbox.state = "failed" if error else "sent"
        outbox.last_error = error
        outbox.sent_at = None if error else utcnow()
        outbox.next_attempt_at = utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(outbox.retry_count, 7)))
        db.commit()


def process_event(event_id):
    with SessionLocal() as db:
        outbox_id = db.scalar(select(EmailOutbox.id).where(EmailOutbox.notification_id == event_id))
    if outbox_id:
        deliver(outbox_id)
    else:
        process_feedback(event_id)


def retry_pending(limit=50):
    with SessionLocal() as db:
        ids = list(
            db.scalars(
                select(EmailOutbox.id)
                .where(
                    EmailOutbox.state.in_(["pending", "failed", "sending"]),
                    EmailOutbox.next_attempt_at <= utcnow(),
                    or_(
                        EmailOutbox.claimed_at.is_(None),
                        EmailOutbox.claimed_at < utcnow() - timedelta(minutes=10),
                        EmailOutbox.state != "sending",
                    ),
                )
                .order_by(EmailOutbox.id)
                .limit(limit)
            )
        )
        feedback_ids = list(
            db.scalars(
                select(Notification.id)
                .where(Notification.feedback_state.in_(["pending", "failed"]))
                .order_by(Notification.id)
                .limit(limit)
            )
        )
    for identifier in ids:
        deliver(identifier)
    for identifier in feedback_ids:
        process_feedback(identifier)
    return len(ids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    print(f"Processed {retry_pending(max(1, min(args.limit, 500)))} eligible email events")
