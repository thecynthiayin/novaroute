from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    csrf,
    current_user,
    dummy_hash,
    find_session,
    issue_session,
    passwords,
    rate_limit,
    revoke_all,
    verify_password,
)
from app.db.session import get_db
from app.models import EmployerProfile, StudentProfile, User, utcnow
from app.schemas import OK, AccountPatch, ConfirmPassword, Login, PasswordChange, Register, UserOut
from app.schemas.responses import CSRFOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf", response_model=CSRFOut)
def bootstrap(request: Request, response: Response, db: Session = Depends(get_db)):
    session = find_session(request, db)
    if not session:
        session = issue_session(db, response)
        db.commit()
    return {"csrf_token": session.csrf_token}


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[Depends(csrf)])
def register(data: Register, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "auth", settings().login_rate_limit)
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(name=data.name, email=data.email, role=data.role, password_hash=passwords.hash(data.password))
    db.add(user)
    db.flush()
    db.add(StudentProfile(user_id=user.id) if user.role == "student" else EmployerProfile(user_id=user.id))
    find_session(request, db).revoked_at = utcnow()
    issue_session(db, response, user.id)
    db.commit()
    return user


@router.post("/login", response_model=UserOut, dependencies=[Depends(csrf)])
def login(data: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    valid = verify_password(user.password_hash if user else dummy_hash, data.password)
    if (
        not valid
        or not user
        or user.deactivated_at
        or (settings().environment == "production" and user.is_demo)
    ):
        raise HTTPException(401, "Invalid email or password")
    find_session(request, db).revoked_at = utcnow()
    issue_session(db, response, user.id)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/logout", response_model=OK, dependencies=[Depends(csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    find_session(request, db).revoked_at = utcnow()
    db.commit()
    response.delete_cookie(settings().cookie_name, path="/")
    return {"message": "Signed out"}


@router.patch("/account", response_model=UserOut, dependencies=[Depends(csrf)])
def account(
    data: AccountPatch, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    email = str(data.email).lower()
    if user.role == "employer" and (email != user.email or data.name != user.name):
        company = db.scalar(
            select(EmployerProfile).where(EmployerProfile.user_id == user.id).with_for_update()
        )
        if company.verification_status != "suspended":
            company.verification_status = "pending"
        company.verification_version += 1
        company.submitted_at, company.reviewed_at = None, None
        company.review_reason = "Recruiter account details changed. Verification must be submitted again."
    if email != user.email:
        if not verify_password(user.password_hash, data.current_password):
            raise HTTPException(400, "Current password is required to change email")
        if db.scalar(select(User).where(User.email == email, User.id != user.id)):
            raise HTTPException(409, "Email is already registered")
        revoke_all(db, user.id)
        issue_session(db, response, user.id)
    user.name, user.email = data.name, email
    user.email_matches, user.email_applications = data.email_matches, data.email_applications
    db.commit()
    return user


@router.post("/password", response_model=OK, dependencies=[Depends(csrf)])
def change_password(
    data: PasswordChange,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(user.password_hash, data.current_password):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = passwords.hash(data.new_password)
    revoke_all(db, user.id)
    db.commit()
    response.delete_cookie(settings().cookie_name, path="/")
    return {"message": "Password changed. Sign in again."}


@router.post("/deactivate", response_model=OK, dependencies=[Depends(csrf)])
def deactivate(
    data: ConfirmPassword,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from app.services.privacy import deactivate_account

    if not verify_password(user.password_hash, data.password):
        raise HTTPException(400, "Password is incorrect")
    deactivate_account(db, user)
    revoke_all(db, user.id)
    db.commit()
    response.delete_cookie(settings().cookie_name, path="/")
    return {"message": "Account deactivated and private resume content removed"}
