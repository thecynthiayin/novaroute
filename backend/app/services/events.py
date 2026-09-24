from sqlalchemy import select

from app.models import EmailOutbox, Notification, User


def notify(db, recipient_id, event_key, kind, title, body, related, feedback=False, email=True):
    existing = db.scalar(select(Notification).where(Notification.event_key == event_key))
    if existing:
        return existing
    user = db.get(User, recipient_id)
    if not user or user.deactivated_at:
        return None
    event = Notification(
        recipient_id=recipient_id,
        event_key=event_key,
        type=kind,
        title=title,
        body=body,
        related=related,
        feedback_state="pending" if feedback else "not_required",
    )
    db.add(event)
    db.flush()
    enabled = user.email_matches if kind == "high_match" else user.email_applications
    if email and enabled:
        db.add(EmailOutbox(notification_id=event.id, event_key=event_key + ":email"))
    return event
