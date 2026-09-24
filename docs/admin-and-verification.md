# Employer verification and administration

## Upgrade an existing installation

Stop the NovaRoute backend and frontend before upgrading. Preserve your `.env`, uploads, model cache and database. With MySQL running, use PowerShell:

```powershell
Set-Location D:\Project\novaroute\backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.jobs.create_admin --email admin@example.com --name "Platform Administrator"
```

Replace the email and name with yours. The command privately prompts twice for a password of at least 10 characters. It refuses to overwrite or promote an existing account. No administrator credentials are bundled or available through public registration. Creating administrators requires local access to the application database configuration.

Start the backend in the same terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
Set-Location D:\Project\novaroute\frontend
npm run dev
```

For production-style local preview use `npm run build` followed by `npm start`. Sign in at `http://localhost:3000/login` using the administrator account. It redirects to `/admin/dashboard`.

Migration `0002_employer_trust` adds verification fields, private reports, audit history, and the admin role. Existing employers become **pending** and their listings disappear from public discovery until reviewed. Nothing is deleted. Fresh synthetic seed accounts have an explicitly labelled demo approval only; they never claim independent identity verification. Re-running the seed does not override existing verification decisions.

## Employer workflow

1. Save company name, website, location, industry and description under **Company profile**.
2. Open **Verification**. Submit legal name, business registration number (or a meaningful explanation if not applicable), recruiter name/position, company contact email and phone.
3. The submission becomes pending. The employer can prepare listings while waiting; no listing is public until company approval and content clearance are both satisfied.
4. The employer sees the administrator's decision reason and receives a notification. Rejected employers may correct and resubmit. Suspended employers must be reopened by an administrator first.
5. Company profile changes or recruiter account name/email changes invalidate approval. Reopening an account returns it to pending, never directly to approved.

Email ownership confirmation (step 1 of the proposed verification plan) is deliberately not part of this update. A supplied email is not represented as verified.

## Administrator workflow

- **Review overview:** counts of submitted pending employers, suspended employers, flagged/pending listings, and open reports.
- **Employer verification:** status filters, paginated private details, approve/reject/suspend/reopen decisions. Approval requires two attestations: independent company checks and confirmation of recruiting authority. Record sources and investigation notes. Approval is unavailable until the employer submits a complete application.
- **Content review:** inspect listing text and automated signals. A human can approve a false positive with a documented investigation, hide content, or restore a hidden active listing belonging to an approved employer. Employer edits cannot remove an admin hide. New content edits always trigger automated review.
- **Student reports:** inspect report details and the referenced listing, hide it if needed, and resolve or dismiss the report with a reason shared with the reporter. Resolving a report alone does not unpublish content; hiding and suspension are deliberate, separately audited actions.
- **Audit history:** append-only API history with actor ID, target ID/type, action, reason, private evidence and timestamp. Student/employer APIs cannot read this history. Database administrators still retain database-level control.

Use an official registry appropriate to the company's jurisdiction, then contact the company using independently obtained contact details. The supplied website, registration number, contact address and recruiter claims are evidence to investigate, not proof by themselves. Small businesses without registration can explain their situation for manual review. Do not record identity-document scans, passwords, full bank details, or unnecessary personal information in notes. The system does not automatically query registries or contact companies on the administrator's behalf.

## Publication and safety behavior

Public browse/detail, recommendations, high-match evaluation, saved-listing availability and new applications require an approved, active employer and an active, unexpired, nondeleted listing without an admin hide. Suspension immediately blocks employer actions and applicant access. Existing applicants retain their application history and receive safety notifications when the listing is hidden or the employer suspended. Notifications and preference-respecting emails use the existing transactional outbox and retry workflow.

Students can report from a listing or their application history, including applications to now-hidden listings. One report per student/listing is enforced, requests are rate limited, and students can track only their own reports. Employers cannot read reporter identities or private report descriptions through any report API. Report status and admin actions use version checks to reject stale decisions.

Automated content review uses payment/credential/fake-check/guarantee signals in both AI modes and adds structured Qwen review in live mode. False positives can occur; flags request investigation, not a fraud verdict. Human approval does not erase the automated risk reasons. Public badges show a review date and explicitly distinguish fictional demo employers. Approval never guarantees safety.

## Browser-test setup

Create a separate local test administrator using the same CLI. Set `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` in the test terminal, then run `npm run test:e2e` from `frontend`. `E2E_BASE_URL` defaults to `http://localhost:3000`; alternate ports require a matching allowed Origin and frontend backend rewrite. Browser fixtures use clearly marked synthetic companies and reports; do not run them against production data.

Do not distribute the test credentials. Admin authorization is enforced by FastAPI on every admin endpoint, alongside session cookies and CSRF checks for decisions. Hiding the admin navigation is not the authorization mechanism.

For repeated local browser-test runs, start the isolated test backend with `LOGIN_RATE_LIMIT=10000` to avoid exhausting the normal 20-attempt development limit across all synthetic accounts sharing localhost. Do not apply this test setting to a public deployment.
