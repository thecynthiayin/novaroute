from sqlalchemy import delete, select, update

from app.models import (
    Application,
    EmailOutbox,
    Internship,
    Notification,
    Resume,
    SavedInternship,
    StatusHistory,
    StudentProfile,
    utcnow,
)
from app.services.embeddings import embeddings
from app.services.resumes import remove_file


def deactivate_account(db, user):
    for resume in db.scalars(select(Resume).where(Resume.student_id == user.id)):
        remove_file(resume.storage_ref)
        db.delete(resume)
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    if profile:
        profile.raw_resume_text = None
        profile.extracted_skills, profile.coursework, profile.projects = [], [], []
        profile.resume_derived, profile.preferences = {}, {}
        profile.degree, profile.location = "", ""
        profile.version += 1
    application_ids = []
    for application in db.scalars(select(Application).where(Application.student_id == user.id)):
        application.profile_snapshot, application.cover_message = {}, ""
        application_ids.append(application.id)
    if application_ids:
        db.execute(
            update(StatusHistory)
            .where(StatusHistory.application_id.in_(application_ids))
            .values(employer_note=None)
        )
        for event in db.scalars(
            select(Notification).where(Notification.type.in_(["new_application", "withdrawal"]))
        ):
            if event.related.get("application_id") in application_ids:
                event.body = "A deactivated applicant's event is retained in the application history."
    db.execute(delete(SavedInternship).where(SavedInternship.student_id == user.id))
    db.execute(
        update(Internship)
        .where(Internship.employer_id == user.id)
        .values(status="closed", content_version=Internship.content_version + 1)
    )
    for event in db.scalars(select(Notification).where(Notification.recipient_id == user.id)):
        event.feedback, event.body, event.dismissed_at = None, "Account deactivated", utcnow()
    db.execute(
        update(EmailOutbox)
        .where(
            EmailOutbox.notification_id.in_(
                select(Notification.id).where(Notification.recipient_id == user.id)
            ),
            EmailOutbox.state != "sent",
        )
        .values(state="suppressed")
    )
    user.name = "Deactivated account"
    user.email = f"deactivated-{user.id}@novaroute.test"
    user.deactivated_at = utcnow()
    embeddings.invalidate()
