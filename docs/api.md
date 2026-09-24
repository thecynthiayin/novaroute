# API usage and contract

Trust/administration schemas are in `backend/app/schemas/trust.py`. All decisions require CSRF and an administrator session; public signup accepts only student/employer roles. The full generated contract is `docs/openapi.json`.

| Method | Path (under `/api`) | Access / behavior |
| --- | --- | --- |
| GET / POST | `/employer/verification` | Own private details / submit with version |
| GET | `/admin/summary` | Admin review counts |
| GET | `/admin/employers` | Admin paginated verification queue; status filter |
| POST | `/admin/employers/{id}/decision` | Approve, reject, suspend, reopen; version/reason/evidence |
| GET | `/admin/listings` | Admin paginated content queue; status/hidden filter |
| GET | `/admin/listings/{id}` | Admin content inspection, including unavailable listings |
| POST | `/admin/listings/{id}/decision` | Approve, hide, restore; version/reason/evidence |
| POST | `/internships/{id}/report` | Student report of available or previously applied listing |
| GET | `/student/reports` | Own paginated reports |
| GET | `/admin/reports` | Admin paginated reports; status filter |
| POST | `/admin/reports/{id}/decision` | Resolve/dismiss with version and public response |
| GET | `/admin/audit` | Admin-only paginated audit history |

See `docs/admin-and-verification.md` for transition rules, publication gates, notifications, and first-admin setup.

Interactive schemas: `http://127.0.0.1:8000/docs`; machine-readable contract: `/openapi.json`. Explicit Pydantic response models are in `backend/app/schemas/responses.py`; request/AI schemas are in `backend/app/schemas/__init__.py`. TypeScript client/types are in `frontend/lib/`.

Every mutation uses the same-origin Next proxy with `credentials: include`, a valid Origin, and `X-CSRF-Token`. Bootstrap before signup/login; bootstrap again after session rotation. Never store session credentials in localStorage. CORS permits only configured exact origins with credentials. All API responses disable shared caching. Swagger is useful for schema inspection; mutation requests from its origin also require that origin in `ALLOWED_ORIGINS` and the session CSRF header.

Browser example:

```javascript
const csrf = await fetch('/api/auth/csrf', { credentials: 'include', cache: 'no-store' }).then(r => r.json());
const response = await fetch('/api/auth/login', {
  method: 'POST', credentials: 'include',
  headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token },
  body: JSON.stringify({ email: 'student@novaroute.test', password: 'NovaRouteDemo!2026' })
});
// Login rotates the session. Fetch /api/auth/csrf again before the next mutation.
```

## Routes

All paths below are under `/api`.

| Method | Path | Permission / behavior |
| --- | --- | --- |
| GET | `/auth/csrf` | Anonymous or authenticated session bootstrap |
| POST | `/auth/register` | `name,email,password,role`; password ≥10 chars; creates role profile |
| POST | `/auth/login` | Generic invalid-login error; rotates browser session |
| POST | `/auth/logout` | CSRF protected; revokes browser session |
| GET | `/auth/me` | Current active user |
| PATCH | `/auth/account` | Own name/email/preferences; password for email change; immutable role |
| POST | `/auth/password` | Current/new password; revokes all sessions |
| POST | `/auth/deactivate` | Password confirmation; privacy cleanup and revocation |
| GET, PATCH | `/student/profile` | Own confirmed fields; PATCH requires `version` |
| POST | `/student/profile/clear-resume` | Explicitly remove only tracked resume-derived entries; `version` |
| POST | `/upload-resume` | Student multipart `file`; returns draft/failed state and confirmation flag |
| GET | `/student/resumes` | Own resume records; no private path/raw text |
| GET, DELETE | `/student/resumes/{id}` | Own metadata; delete private bytes/row/raw text |
| GET | `/student/resumes/{id}/download` | Owner-only attachment; never public static storage |
| POST | `/student/resumes/{id}/confirm` | Edited extraction + upload-time profile `version`; merges verified fields |
| GET, PATCH | `/employer/profile` | Own company profile |
| GET | `/internships` | Public active, unexpired, nondeleted listings |
| POST | `/internships`, `/post-internship` | Employer; identical pending-review service |
| GET | `/internships/{id}` | Public active listing; owner can view private states/review |
| PATCH | `/internships/{id}` | Owner; full editable listing + `content_version`; re-review |
| DELETE | `/internships/{id}` | Owner; soft delete preserving applications |
| POST | `/internships/{id}/close` | Owner + `version` (content version) |
| POST | `/internships/{id}/reopen`, `/review` | Owner + `version`; fresh pending review |
| GET | `/employer/internships` | Owner-scoped `q,status,page,page_size` |
| GET | `/student/recommendations` | Current student; bounded `limit,threshold` |
| GET | `/recommendations/{student_id}` | ID must equal current student's user ID |
| POST | `/applications` | Student `internship_id,cover_message`; one per pair |
| GET | `/applications` | Role-scoped; `status,internship_id,page,page_size` |
| GET | `/applications/{id}` | Student owner or listing owner; snapshot/history/feedback/delivery state |
| PATCH | `/applications/{id}` | Student cover message + `version`; only before review |
| PUT | `/applications/{id}/status` | Owning employer `status,version,employer_note?` |
| POST | `/applications/{id}/withdraw` | Owning student `version`; terminal, history preserved |
| GET | `/student/saved` | Paginated saved listings; unavailable listings remain identifiable |
| GET | `/student/internship-states` | Own compact saved/applied ID sets for consistent card states across pages |
| POST, PATCH, DELETE | `/student/saved/{internship_id}` | Save, private `note`, unsave |
| GET | `/notifications` | Own inbox; `read=all|read|unread`, pagination |
| GET | `/notifications/count` | Own unread nondismissed count |
| PATCH | `/notifications/{id}` | Own `read` boolean |
| POST | `/notifications/read-all` | Mark all own notifications read |
| DELETE | `/notifications/{id}` | Dismiss own notification |
| GET | `/dashboard` | Actual database totals and own recent events |
| GET | `/health`, `/ready` | Liveness; database/migration and model readiness without credentials |

Listing search: `q`, `skill`, `location`, `work_mode=remote|hybrid|onsite`, `sort=newest|oldest|title`, `page>=1`, `page_size=1..50`. Text filters are escaped literal substrings; ordering includes listing ID for ties. Pagination returns `{items,total,page,page_size}`. Recommendations default to strict `score > RECOMMENDATION_MIN_SCORE`; an explicitly supplied threshold must be in `[0,1]`, limit in `[1,50]`. The UI never silently lowers it.

Statuses: internship `pending_ai_review → active|flagged`, owner may close; reopening/editing returns to pending. Application `applied → viewed|accepted|rejected|withdrawn`, `viewed → accepted|rejected|withdrawn`. Only students withdraw; only employers view/accept/reject. Terminal transitions reject with 409. Current-state repeats are idempotent. Unique database constraints also reject duplicate applications.

## Error behavior

Errors use `{"detail":"safe message"}` or a bounded validation detail array with field location, message and type—never the submitted password/resume value. Codes: 401 authentication, 403 role/CSRF, 404 inaccessible record, 409 conflict/version/transition, 413 upload size, 422 validation/PDF text error, 429 rate limit, 503 DB/model unavailable. User-facing error responses never contain credentials, raw provider messages or private storage paths.

Create listing returns 201 promptly in pending state; the UI polls owner listings while asynchronous content review finishes. Application status returns promptly after a committed transaction; feedback and email states update separately. Notification polling is approximately every 25 seconds while visible, not instantaneous push.
