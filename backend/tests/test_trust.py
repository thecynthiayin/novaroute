from sqlalchemy import select

from app.core.security import passwords
from app.db.session import SessionLocal
from app.main import app
from app.models import AdminAudit, Notification, User
from tests.conftest import BrowserClient


def administrator():
    with SessionLocal() as db:
        db.add(
            User(
                role="admin",
                name="Safety Admin",
                email="admin@example.test",
                password_hash=passwords.hash("TestingPassword!26"),
            )
        )
        db.commit()
    client = BrowserClient(app)
    assert (
        client.mutate(
            "POST", "/auth/login", {"email": "admin@example.test", "password": "TestingPassword!26"}
        ).status_code
        == 200
    )
    return client


def submission(employer):
    employer.mutate(
        "PATCH",
        "/employer/profile",
        {"company_name": "Trust Labs", "website": "https://example.org", "location": "Bangkok"},
    )
    version = employer.get("/api/employer/verification").json()["verification_version"]
    return employer.mutate(
        "POST",
        "/employer/verification",
        {
            "version": version,
            "legal_name": "Trust Labs Ltd",
            "registration_number": "TEST-123",
            "recruiter_name": "Robin Test",
            "recruiter_position": "Recruiter",
            "contact_email": "robin@example.test",
            "contact_phone": "0123456789",
        },
    )


def decision(action, version=1, **extra):
    return {
        "action": action,
        "version": version,
        "reason": "Reviewed the submitted evidence carefully.",
        "evidence": "Independently contacted company and checked official registry.",
        **extra,
    }


def test_admin_rbac_and_public_signup_cannot_create_admin(register):
    employer, _ = register("employer")
    student, _ = register()
    for client in [employer, student]:
        assert client.get("/api/admin/summary").status_code == 403
        assert client.mutate("POST", "/admin/employers/1/decision", decision("suspend")).status_code == 403
    assert (
        student.mutate(
            "POST",
            "/auth/register",
            {
                "role": "admin",
                "name": "Attacker",
                "email": "bad@example.test",
                "password": "TestingPassword!26",
            },
        ).status_code
        == 422
    )
    admin = administrator()
    assert admin.get("/api/admin/summary").status_code == 200
    assert admin.post("/api/admin/employers/1/decision", json=decision("suspend")).status_code == 403


def test_verification_gate_private_fields_and_reverification(pair, listing):
    employer, company, student, _ = pair
    admin = administrator()
    response = submission(employer)
    assert response.status_code == 200, response.text
    record = response.json()
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404
    assert student.get("/api/internships").json()["total"] == 0
    assert student.mutate("POST", "/applications", {"internship_id": listing["id"]}).status_code == 409
    path = f"/admin/employers/{company['id']}/decision"
    assert admin.mutate("POST", path, decision("approve", record["verification_version"])).status_code == 422
    approved = admin.mutate(
        "POST",
        path,
        decision(
            "approve", record["verification_version"], company_checked=True, representative_checked=True
        ),
    )
    assert approved.status_code == 200, approved.text
    assert (
        admin.mutate(
            "POST",
            path,
            decision(
                "approve", record["verification_version"], company_checked=True, representative_checked=True
            ),
        ).status_code
        == 409
    )
    public = student.get(f"/api/internships/{listing['id']}").json()
    assert public["company"]["verification_status"] == "approved"
    assert "contact_email" not in public["company"]
    assert "registration_number" not in public["company"]
    employer.mutate(
        "PATCH",
        "/employer/profile",
        {"company_name": "Changed Identity", "website": "https://example.org", "location": "Bangkok"},
    )
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404


def test_reports_hide_suspension_notifications_and_audit(pair, listing, application):
    employer, company, student, person = pair
    admin = administrator()
    path = f"/internships/{listing['id']}/report"
    body = {"category": "payment_request", "details": "They asked me to transfer a training fee."}
    report = student.mutate("POST", path, body)
    assert report.status_code == 201, report.text
    report = report.json()
    assert student.mutate("POST", path, body).status_code == 409
    assert employer.get("/api/admin/reports").status_code == 403
    assert employer.mutate("POST", path, body).status_code == 403
    assert admin.get("/api/admin/reports").json()["total"] == 1
    hidden = admin.mutate(
        "POST", f"/admin/listings/{listing['id']}/decision", decision("hide", listing["content_version"])
    )
    assert hidden.status_code == 200, hidden.text
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404
    # Employer edits and automated review cannot bypass an administrator hide.
    assert (
        employer.mutate(
            "POST", f"/internships/{listing['id']}/review", {"version": hidden.json()["content_version"]}
        ).status_code
        == 200
    )
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404
    version = employer.get("/api/employer/verification").json()["verification_version"]
    suspended = admin.mutate(
        "POST", f"/admin/employers/{company['id']}/decision", decision("suspend", version)
    )
    assert suspended.status_code == 200
    assert employer.get("/api/employer/internships").status_code == 403
    assert employer.get("/api/applications").status_code == 403
    assert submission(employer).status_code == 403
    resolved = admin.mutate(
        "POST", f"/admin/reports/{report['id']}/decision", decision("resolved", report["version"])
    )
    assert resolved.status_code == 200
    assert student.get("/api/student/reports").json()["items"][0]["status"] == "resolved"
    with SessionLocal() as db:
        notices = list(db.scalars(select(Notification).where(Notification.recipient_id == person["id"])))
        assert len([n for n in notices if n.type == "safety_update"]) == 2
        assert len(list(db.scalars(select(AdminAudit)))) == 3
    reopened = admin.mutate(
        "POST",
        f"/admin/employers/{company['id']}/decision",
        decision("reopen", suspended.json()["verification_version"]),
    )
    assert reopened.status_code == 200
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404


def test_content_flags_and_manual_review(pair):
    employer = pair[0]
    admin = administrator()
    result = employer.mutate(
        "POST",
        "/internships",
        {
            "title": "Software Intern",
            "description": "Build Python APIs, then pay for training before you start.",
            "required_skills": ["Python"],
            "location": "Remote",
            "work_mode": "remote",
            "duration": "3 months",
        },
    )
    identifier = result.json()["id"]
    item = admin.get(f"/api/admin/listings/{identifier}").json()
    assert item["status"] == "flagged"
    assert item["moderation"]["risk_reasons"]
    assert pair[2].get(f"/api/internships/{identifier}").status_code == 404
    approved = admin.mutate(
        "POST", f"/admin/listings/{identifier}/decision", decision("approve", item["content_version"])
    )
    assert approved.status_code == 200
    assert pair[2].get(f"/api/internships/{identifier}").status_code == 200
    assert approved.json()["moderation"]["manual_review"]["decision"] == "approved"
    assert approved.json()["moderation"]["risk_reasons"]


def test_hidden_saved_recommendation_and_restore(pair, listing):
    student = pair[2]
    admin = administrator()
    assert (
        student.mutate("POST", f"/student/saved/{listing['id']}", {"note": "Compare later"}).status_code
        == 200
    )
    path = f"/admin/listings/{listing['id']}/decision"
    hidden = admin.mutate("POST", path, decision("hide", listing["content_version"]))
    assert hidden.status_code == 200
    assert student.get("/api/student/saved").json()["items"][0]["available"] is False
    assert student.get("/api/student/recommendations").json()["items"] == []
    assert student.mutate("POST", "/applications", {"internship_id": listing["id"]}).status_code == 409
    assert admin.mutate("POST", path, decision("restore", listing["content_version"])).status_code == 409
    assert (
        admin.mutate("POST", path, decision("restore", hidden.json()["content_version"])).status_code == 200
    )
    assert student.get(f"/api/internships/{listing['id']}").status_code == 200


def test_rejection_resubmit_validation_and_account_identity_change(pair, listing):
    employer, company, student, _ = pair
    admin = administrator()
    submitted = submission(employer).json()
    path = f"/admin/employers/{company['id']}/decision"
    rejected = admin.mutate("POST", path, decision("reject", submitted["verification_version"]))
    assert rejected.status_code == 200
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404
    version = rejected.json()["verification_version"]
    fields = {
        "version": version,
        "legal_name": "Trust Labs Ltd",
        "registration_number": "",
        "registration_explanation": "",
        "recruiter_name": "Robin Test",
        "recruiter_position": "Recruiter",
        "contact_email": "robin@example.test",
        "contact_phone": "0123456789",
    }
    assert employer.mutate("POST", "/employer/verification", fields).status_code == 422
    fields["registration_explanation"] = (
        "Unregistered student venture, review university affiliation instead."
    )
    submitted = employer.mutate("POST", "/employer/verification", fields)
    assert submitted.status_code == 200
    assert (
        admin.mutate(
            "POST",
            path,
            decision(
                "approve",
                submitted.json()["verification_version"],
                company_checked=True,
                representative_checked=True,
            ),
        ).status_code
        == 200
    )
    assert (
        employer.mutate(
            "PATCH",
            "/auth/account",
            {
                "name": "Different Recruiter",
                "email": company["email"],
                "email_matches": True,
                "email_applications": True,
            },
        ).status_code
        == 200
    )
    assert student.get(f"/api/internships/{listing['id']}").status_code == 404


def test_reports_private_and_require_available_or_applied_listing(pair, listing, register):
    employer, _, student, _ = pair
    stranger, _ = register()
    report = student.mutate(
        "POST",
        f"/internships/{listing['id']}/report",
        {"category": "impersonation", "details": "This recruiter may be impersonating the company."},
    )
    assert report.status_code == 201
    assert stranger.get("/api/student/reports").json()["total"] == 0
    assert "reporter_id" not in report.json()
    employer.mutate("POST", f"/internships/{listing['id']}/close", {"version": listing["content_version"]})
    assert (
        stranger.mutate(
            "POST",
            f"/internships/{listing['id']}/report",
            {"category": "other", "details": "Cannot report arbitrary hidden records."},
        ).status_code
        == 404
    )
