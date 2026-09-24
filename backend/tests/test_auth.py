from datetime import timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Session, User, utcnow


def test_csrf_includes_login_and_origin(client):
    body = {"email": "anyone@example.test", "password": "x"}
    assert client.post("/api/auth/login", json=body).status_code == 403
    token = client.get("/api/auth/csrf").json()["csrf_token"]
    assert (
        client.post(
            "/api/auth/login", json=body, headers={"Origin": "https://evil.test", "X-CSRF-Token": token}
        ).status_code
        == 403
    )
    assert client.mutate("POST", "/auth/login", body).status_code == 401


def test_register_login_logout_rotation_and_expiry(register):
    client, user = register(email="Case@Example.test")
    assert user["email"] == "case@example.test"
    raw = client.cookies.get("novaroute_session")
    assert client.get("/api/auth/me").json()["id"] == user["id"]
    assert client.mutate("POST", "/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    response = client.mutate(
        "POST", "/auth/login", {"email": user["email"], "password": "TestingPassword!26"}
    )
    assert response.status_code == 200
    assert client.cookies.get("novaroute_session") != raw
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    with SessionLocal() as db:
        for session in db.scalars(select(Session).where(Session.user_id == user["id"])):
            session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_email_and_immutable_role(register):
    client, user = register()
    assert (
        client.mutate(
            "POST",
            "/auth/register",
            {
                "name": "Another User",
                "email": user["email"].upper(),
                "password": "TestingPassword!26",
                "role": "employer",
            },
        ).status_code
        == 409
    )
    assert (
        client.mutate(
            "PATCH",
            "/auth/account",
            {
                "name": "Changed",
                "email": user["email"],
                "email_matches": True,
                "email_applications": True,
                "role": "employer",
            },
        ).status_code
        == 422
    )
    assert client.get("/api/employer/profile").status_code == 403


def test_password_change_revokes_all_sessions(register):
    client, _ = register()
    assert (
        client.mutate(
            "POST", "/auth/password", {"current_password": "wrong", "new_password": "NewPassword!2026"}
        ).status_code
        == 400
    )
    assert (
        client.mutate(
            "POST",
            "/auth/password",
            {"current_password": "TestingPassword!26", "new_password": "NewPassword!2026"},
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").status_code == 401


def test_email_change_requires_password(register):
    client, user = register()
    body = {
        "name": "New Name",
        "email": "new@example.test",
        "email_matches": False,
        "email_applications": True,
    }
    assert client.mutate("PATCH", "/auth/account", body).status_code == 400
    response = client.mutate("PATCH", "/auth/account", {**body, "current_password": "TestingPassword!26"})
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.test"
    with SessionLocal() as db:
        assert db.get(User, user["id"]).password_hash.startswith("$argon2")


def test_validation_errors_do_not_echo_password(client):
    response = client.mutate(
        "POST", "/auth/register", {"name": "A", "email": "bad", "password": "SECRET", "role": "admin"}
    )
    assert response.status_code == 422
    assert "SECRET" not in response.text


def test_login_allowed_after_repeated_failures(register, monkeypatch):
    from app.core.config import settings
    from app.core.security import _attempts

    _attempts.clear()
    monkeypatch.setattr(settings(), "login_rate_limit", 1)
    client, user = register()
    assert client.mutate("POST", "/auth/logout").status_code == 200
    body = {"email": user["email"], "password": "invalid"}
    for _ in range(3):
        assert client.mutate("POST", "/auth/login", body).status_code == 401
    response = client.mutate(
        "POST", "/auth/login", {**body, "password": "TestingPassword!26"}
    )
    assert response.status_code == 200
    assert client.get("/api/auth/me").json()["id"] == user["id"]
