# Verification report

## Employer verification and administration update

Verified on 2026-09-20 against MySQL 8.4.11. The complete backend suite passed **48 tests**, including seven trust/safety integration tests. The final trust-only rerun also passed all seven after the last manual-review labeling change. All **six Playwright tests** passed against the production frontend on desktop/light and mobile/dark: existing user journeys, responsive landing, and the new employer submission → admin approval → student report → hide → resolve → suspend workflow. Admin screenshots were visually inspected.

TypeScript, ESLint, Ruff, production build, and Alembic schema drift checks passed. Migration `0002_employer_trust` was applied successfully to existing development/test schemas. Admin access, signup-role escalation denial, CSRF, stale decision rejection, private report/verification data, identity-change re-verification, suspension, hidden saved/recommendation/application gates, manual content approval, restoration, rejection/resubmission, and applicant safety notifications have integration coverage.

Browser testing used isolated app ports 3100/8100 and a private temporary test administrator, with a higher localhost-only login rate limit. The operator's running app on 3000/8000 was not stopped for testing. Independent registry/contact checks remain human actions: automated tests use explicitly fictional evidence, not real business validation. No external verification provider or paid Qwen call was exercised.

The original build verification below is retained as historical evidence; its test counts and initial migration version precede this update.

The verified changes were also copied into the operator's `D:\Project\novaroute` installation after checking the changed files against the delivered baseline. Original changed files were backed up in the task's `work/before-trust-update-*` directory. Its MySQL 8.4.11 database on port 3306 was upgraded from `0001` to `0002_employer_trust`; `alembic check` found no drift. The running API on port 8000 exposed `/api/admin/summary` after hot reload, and its readiness endpoint reported the database ready. The operator creates their own administrator password using the documented CLI.

Performed on 2026-09-20 (Asia/Bangkok), Windows, Python 3.12.14, Node 24.14.0, MySQL 8.4.11, Mailpit 1.31.2.

## Executed successfully

| Check | Actual result |
| --- | --- |
| Isolated Python dependency installation | Passed; `pip check`: no broken requirements |
| npm installation / locked version resolution | Passed; point-in-time npm audit: 0 vulnerabilities |
| Alembic upgrade on fresh MySQL 8.4 schema | Passed, revision `0001` |
| Alembic schema drift check | No new upgrade operations detected |
| Synthetic seed | 25 imported, 0 skipped; second run: 0 imported, 25 duplicates |
| Actual Kaggle CSV import | 25 imported, 65 skipped; second run: 0 imported, 25 duplicates |
| Backend suite with MySQL + real optional integrations | **41 passed** |
| Ruff lint / formatting | Passed |
| TypeScript strict type check | Passed |
| ESLint 10 with TypeScript/Next rules | Passed |
| Next.js production build | Passed |
| Playwright against production Next server | **4 passed**, desktop light and mobile dark |
| Responsive checks | 375, 768, 1440 px; no page overflow in checked flows |
| Real MiniLM download/inference | Loaded on CPU; 384-dimensional vectors |
| Real high-match positive control | Measured cosine `0.958998863547504`; one logical alert across repeated evaluations |
| Real Mailpit SMTP | Viewed, withdrawn, and high-match messages received; outbox recorded sent only after SMTP accepted |
| Academic experiment | Real MiniLM and keyword baseline both executed; full output in `evaluation/results.json` |

The final backend run used:

```powershell
$env:TEST_DATABASE_URL='mysql+pymysql://novaroute:local_dev_password@127.0.0.1:3307/novaroute_test?charset=utf8mb4'
$env:RUN_REAL_MODEL='1'
$env:RUN_MAILPIT='1'
$env:HF_HUB_OFFLINE='1'
python -m pytest -q --tb=short
```

The normal suite mocks paid model calls and routine SMTP. Optional real-model and Mailpit tests run only when explicitly enabled. No SQLite substitutes were used. The isolated DB guard requires the exact `novaroute_test` database name. Tests clean that database's rows, never the working database.

Coverage includes session rotation/logout/expiry, password/email updates, CSRF including login and Origin, cross-role/cross-user permissions, duplicate email/application constraints, all unavailable listing states, application snapshots, version conflicts, concurrent decisions, terminal transitions, withdrawal and retained history, cover editing, private PDF ownership, invalid/empty/corrupt/oversized PDF handling, extraction confirmation/stale drafts/provider failure, manual fallback, moderation tampering/flagged/pending/stale results, strict cosine thresholds/tie ordering/cache invalidation, high-match deduplication/side-effect-free GETs, status event deduplication, feedback fallback, SMTP failure/retries/claim recovery, importer headers/provenance/idempotence, and deactivation cleanup.

Each Playwright journey registers both roles, edits a profile, uploads/confirms a real PDF, creates/edits/deletes an employer listing, saves/applies, changes employer status, reads feedback, edits saved notes, withdraws, logs out/in, changes account preferences/password, and deactivates its student account. Both light desktop and dark mobile runs passed. The landing page was checked at three viewport widths in both themes. Screenshots were visually inspected for layout and legibility; these are not a formal third-party accessibility audit.

## Explicit limitations and unexecuted checks

- **Live Qwen/OpenRouter inference:** not run; no API key supplied. The public catalog and structured-output documentation were consulted. Configuration, schemas, bounded retries and failure handling are implemented; mocked calls do not prove real provider behavior.
- **External SMTP:** not run; no credentials supplied. Mailpit delivery was real and verified. Real recipients are disabled by default.
- **Docker Compose startup:** not run because Docker was not available. The same pinned MySQL/Mailpit versions were downloaded and started natively in a workspace-local test installation. Compose health checks/configuration are provided. The MySQL archive's MD5 matched the publisher's advertised checksum.
- **macOS/Linux setup:** documented equivalent native commands; not executed on those operating systems.
- **Independent model evaluation:** not performed. Three synthetic profiles with proposed relevance labels are not a population-level accuracy estimate. The 0.80 cosine cutoff is not measured accuracy.
- The backend tests emitted two upstream deprecation warnings concerning Starlette's current HTTPX test adapter and an AnyIO alias. They were warnings, not test failures. No warning was hidden to manufacture a clean result.

The local development application is left running at `http://localhost:3000`, backend `127.0.0.1:8000`, Mailpit `127.0.0.1:8025`, and the isolated MySQL instance at `127.0.0.1:3307`. Stopping/restarting the desktop environment may stop these processes; use the README commands to restart. The existing unrelated database on port 3306 was not modified.
