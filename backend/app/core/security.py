import secrets
from collections import defaultdict, deque
from datetime import timedelta
from hashlib import sha256
from threading import Lock
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.db.session import get_db
from app.models import EmployerProfile, Session, User, utcnow

passwords = PasswordHasher()
dummy_hash = passwords.hash("not-a-real-user-password")
_attempts: dict = defaultdict(deque)
_lock = Lock()


def rate_limit(request: Request, scope: str, limit: int):
    key = (scope, request.client.host if request.client else "unknown")
    now = monotonic()
    with _lock:
        for old_key in list(_attempts):
            if not _attempts[old_key] or _attempts[old_key][-1] < now - 600:
                del _attempts[old_key]
        queue = _attempts[key]
        while queue and queue[0] < now - 600:
            queue.popleft()
        if len(queue) >= limit:
            raise HTTPException(429, "Too many attempts. Try again in ten minutes.")
        queue.append(now)


def verify_password(hashed, plain):
    try:
        return passwords.verify(hashed, plain)
    except (VerificationError, InvalidHashError):
        return False


def find_session(request: Request, db: DBSession):
    raw = request.cookies.get(settings().cookie_name, "")
    if not raw:
        return None
    return db.scalar(
        select(Session).where(
            Session.token_hash == sha256(raw.encode()).hexdigest(),
            Session.revoked_at.is_(None),
            Session.expires_at > utcnow(),
        )
    )


def csrf(request: Request, db: DBSession = Depends(get_db)):
    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in settings().origins:
        raise HTTPException(403, "Request origin is not allowed")
    session = find_session(request, db)
    supplied = request.headers.get("x-csrf-token", "")
    if not session or not supplied or not secrets.compare_digest(supplied, session.csrf_token):
        raise HTTPException(403, "Session security token expired. Refresh and try again.")


def current_user(request: Request, db: DBSession = Depends(get_db)):
    session = find_session(request, db)
    user = db.get(User, session.user_id) if session and session.user_id else None
    if not user or user.deactivated_at or (settings().environment == "production" and user.is_demo):
        raise HTTPException(401, "Please sign in")
    return user


def role(required):
    def dependency(user: User = Depends(current_user)):
        if user.role != required:
            raise HTTPException(403, f"This action requires a {required} account")
        return user

    return dependency


student = role("student")
admin = role("admin")


def employer(user: User = Depends(role("employer")), db: DBSession = Depends(get_db)):
    company = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
    if company and company.verification_status == "suspended":
        raise HTTPException(403, "Employer account suspended. Contact the platform administrator.")
    return user


def issue_session(db, response: Response, user_id=None):
    raw = secrets.token_urlsafe(40)
    session = Session(
        user_id=user_id,
        token_hash=sha256(raw.encode()).hexdigest(),
        csrf_token=secrets.token_urlsafe(32),
        expires_at=utcnow() + timedelta(hours=settings().session_hours),
    )
    db.add(session)
    response.set_cookie(
        settings().cookie_name,
        raw,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        max_age=settings().session_hours * 3600,
        path="/",
    )
    return session


def revoke_all(db, user_id):
    db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
