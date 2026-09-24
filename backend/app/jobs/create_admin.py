"""Create an administrator locally; never through public signup or demo seeding."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select

from app.core.security import passwords
from app.db.session import SessionLocal
from app.models import User
from app.schemas import Register


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Admin password (10+ characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        values = Register(email=args.email, name=args.name, password=password, role="employer")
    except ValidationError as exc:
        raise SystemExit("; ".join(f"{error['loc'][0]}: {error['msg']}" for error in exc.errors())) from None
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == values.email)):
            raise SystemExit("Email already exists; no existing account was changed")
        db.add(
            User(
                name=values.name,
                email=values.email,
                password_hash=passwords.hash(values.password),
                role="admin",
            )
        )
        db.commit()
    print("Administrator created. Sign in through /login; you will be directed to /admin/dashboard.")


if __name__ == "__main__":
    main()
