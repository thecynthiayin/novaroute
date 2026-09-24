import smtplib
import ssl
from email.message import EmailMessage
from html import escape

from app.core.config import settings


def send_email(recipient, title, body, feedback, related):
    config = settings()
    if not config.smtp_allow_real_recipients and not recipient.endswith(".test"):
        raise RuntimeError(
            "Real recipients are disabled; use .test addresses or explicitly configure SMTP_ALLOW_REAL_RECIPIENTS"
        )
    suffix = (
        f"/student/applications?application={related['application_id']}"
        if related.get("application_id")
        else f"/student/internships/{related['internship_id']}"
        if related.get("internship_id")
        else "/student/notifications"
    )
    url = config.frontend_url.rstrip("/") + suffix
    advice = ""
    if feedback:
        advice = (
            "\n\nAI suggestions\n" + feedback["summary"] + "\n" + "\n".join(feedback.get("next_steps", []))
        )
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = config.smtp_from, recipient, title
    message.set_content(body + advice + "\n\nView in NovaRoute: " + url)
    message.add_alternative(
        f'<html><body><h1>{escape(title)}</h1><p>{escape(body)}</p><p style="white-space:pre-line">{escape(advice)}</p><p><a href="{escape(url, quote=True)}">View in NovaRoute</a></p></body></html>',
        subtype="html",
    )
    transport = smtplib.SMTP_SSL if config.smtp_ssl else smtplib.SMTP
    with transport(config.smtp_host, config.smtp_port, timeout=15) as smtp:
        if config.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if config.smtp_username:
            smtp.login(config.smtp_username, config.smtp_password)
        refused = smtp.send_message(message)
        if refused:
            raise RuntimeError("SMTP rejected a recipient")
