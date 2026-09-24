import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.engine import make_url

TEST_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_URL:
    parsed_test_url = make_url(TEST_URL)
    if parsed_test_url.drivername != "mysql+pymysql" or parsed_test_url.database != "novaroute_test":
        raise RuntimeError("Tests require a dedicated MySQL database named novaroute_test")
    os.environ["DATABASE_URL"] = TEST_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["AI_MODE"] = "demo"
os.environ["LOGIN_RATE_LIMIT"] = "10000"

from fastapi.testclient import TestClient

from app.db.session import engine
from app.main import app
from app.models import Base


class BrowserClient(TestClient):
    def mutate(self, method, path, body=None, **kwargs):
        token = self.get("/api/auth/csrf").json()["csrf_token"]
        headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": token}
        return self.request(method, "/api" + path, json=body, headers=headers, **kwargs)


@pytest.fixture
def db_ready(monkeypatch, tmp_path):
    if not TEST_URL:
        pytest.skip("Set TEST_DATABASE_URL to an isolated MySQL 8 novaroute_test database")
    from alembic.config import Config

    from alembic import command

    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    command.upgrade(config, "head")
    with engine.begin() as conn:
        version = conn.scalar(text("SELECT VERSION()"))
        assert version.startswith("8."), "Integration tests must run against MySQL 8"
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(delete(table))
    from app.core.config import settings

    monkeypatch.setattr(settings(), "upload_private_dir", tmp_path / "private")
    monkeypatch.setattr("app.api.profiles.evaluate_alerts", lambda **kwargs: None)
    monkeypatch.setattr("app.services.recommendations.evaluate_alerts", lambda **kwargs: None)
    monkeypatch.setattr("app.api.trust.evaluate_alerts", lambda **kwargs: None)
    monkeypatch.setattr("app.jobs.delivery.send_email", lambda *args: None)
    yield


@pytest.fixture
def client(db_ready):
    with BrowserClient(app) as instance:
        yield instance


@pytest.fixture
def register(client):
    def create(role="student", email=None):
        instance = BrowserClient(app)
        response = instance.mutate(
            "POST",
            "/auth/register",
            {
                "email": email or f"{uuid4().hex}@example.test",
                "name": "Test Student" if role == "student" else "Test Employer",
                "password": "TestingPassword!26",
                "role": role,
            },
        )
        assert response.status_code == 201, response.text
        return instance, response.json()

    return create


@pytest.fixture
def pair(register):
    employer, company = register("employer")
    student, person = register()
    assert (
        employer.mutate(
            "PATCH",
            "/employer/profile",
            {
                "company_name": "Test Labs",
                "website": "",
                "industry": "Software",
                "location": "Remote",
                "description": "A fictional testing company",
            },
        ).status_code
        == 200
    )
    assert (
        student.mutate(
            "PATCH",
            "/student/profile",
            {
                "extracted_skills": ["Python", "SQL"],
                "coursework": ["Databases"],
                "projects": [],
                "degree": "Computing",
                "location": "Remote",
                "preferences": {},
                "version": 1,
            },
        ).status_code
        == 200
    )
    # Existing workflow fixtures represent an independently approved employer.
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import EmployerProfile

    with SessionLocal() as db:
        profile = db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == company["id"]))
        profile.verification_status = "approved"
        db.commit()
    return employer, company, student, person


@pytest.fixture
def listing(pair):
    employer, _, _, _ = pair
    response = employer.mutate(
        "POST",
        "/internships",
        {
            "title": "Python Backend Intern",
            "description": "Build APIs with Python and SQL while working alongside a mentor.",
            "required_skills": ["Python", "SQL"],
            "location": "Remote",
            "work_mode": "remote",
            "duration": "3 months",
        },
    )
    assert response.status_code == 201, response.text
    item = employer.get(f"/api/internships/{response.json()['id']}").json()
    assert item["status"] == "active", item
    return item


@pytest.fixture
def application(pair, listing):
    student = pair[2]
    response = student.mutate(
        "POST",
        "/applications",
        {"internship_id": listing["id"], "cover_message": "I built a Python project."},
    )
    assert response.status_code == 201, response.text
    return response.json()
