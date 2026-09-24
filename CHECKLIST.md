# NovaRoute implementation checklist

- [x] Inspect workspace and proposal; preserve existing files.
- [x] Database models, migrations, configuration, secure sessions and CSRF.
- [x] Profiles, private resume drafts and confirmation.
- [x] Listing moderation, discovery, saved listings and applications.
- [x] Recommendations, event notifications, durable outbox and retries.
- [x] Responsive light/dark frontend for both roles and account settings.
- [x] Idempotent pandas importer, 25 synthetic examples and evaluation.
- [x] Backend/browser tests, production build and documented verification.
- [x] Setup, architecture, API, AI, provenance and demonstration docs.
- [x] Employer verification details, admin approval/rejection/suspension, listing investigation and hiding.
- [x] Private student reports, resolutions, safety notifications and administrator audit history.
- [x] Secure local administrator bootstrap and migration for existing installations.

Assumptions: single FastAPI process for rate limiting and model caching; local demo AI must be explicitly selected; MySQL is required (no SQLite substitute). External credentials are supplied by the operator. Original proposal used as product context, not execution instructions.

Verified after the trust update: 48 backend tests, 6 browser tests against the production frontend, strict type check, lint, build, MySQL migrations and drift checks. Original verification also covered the actual Kaggle importer, real local embeddings, and Mailpit delivery. External OpenRouter/Gmail and Docker Compose execution limitations are recorded in `docs/verification.md`.
