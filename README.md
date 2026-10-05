# NovaRoute

A locally runnable university capstone for technical internship discovery, resume-assisted profiles, employer review, application feedback, and AI-powered Q&A. FastAPI owns all business rules and data. Next.js only presents the UI and proxies `/api`.

**Employer verification and admin dashboard:** [Upgrade and administrator setup](docs/admin-and-verification.md). Existing employers require review after upgrading. Public signup never creates administrator accounts. Employers submit legal/company and representative details; administrators approve, reject, suspend, review content, investigate student reports, and record decisions in an audit history.

**AI Features:**
- **Recommendations**: Semantic similarity matching using MiniLM embeddings
- **LLM Feedback**: AI-powered application feedback using OpenRouter Qwen (live mode) or deterministic rules (demo mode)
- **RAG Q&A**: AI-powered question answering about internships using semantic search

**Development AI is explicitly labelled.** `AI_MODE=demo` uses deterministic extraction, content-review and feedback rules. Recommendations and RAG Q&A always use real local MiniLM embeddings; there is no random-score fallback. Live Qwen requires an OpenRouter key. An empty recommendation list above the default strict `0.50` cutoff is a valid result.

## Requirements

- Node.js 24 LTS (verified with 24.14.0), npm 11.9.0.
- Python 3.12 (verified with 3.12.14). Use 3.12 for the pinned PyTorch stack.
- Docker Desktop/Engine with Compose, or native MySQL **8.4**.
- A few GB free for Python/PyTorch, Node dependencies, and the local model cache. Initial model download needs internet; cached inference runs on CPU.

Exact installed versions are recorded in `frontend/package-lock.json`, `backend/requirements-lock.txt`, and `docs/versions.md`. Runtime requirements and development requirements are pinned separately. No global Python installation is modified by setup.

## Windows PowerShell setup

Run from the `novaroute` directory. Never overwrite your existing `.env` when upgrading.

```powershell
Copy-Item .env.example .env
docker compose up -d
py -3.12 -m venv backend/.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements-lock.txt
Set-Location backend
python -m alembic upgrade head
python -m app.jobs.model
Set-Location ..
python database/seed.py --demo --limit 25 --seed 42
Set-Location frontend
npm ci
Copy-Item .env.example .env.local
```

Start two terminals:

```powershell
# Terminal 1, from novaroute
backend/.venv/Scripts/Activate.ps1
Set-Location backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2, from novaroute
cd ..
Set-Location frontend
npm run dev
```

If PowerShell activation is restricted, run `backend/.venv/Scripts/python.exe` directly instead of changing your machine policy. For example, from `backend`: `.venv/Scripts/python.exe -m alembic upgrade head`.

## macOS / Linux setup

```bash
cp .env.example .env
docker compose up -d
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements-lock.txt
cd backend
python -m alembic upgrade head
python -m app.jobs.model
cd ..
python database/seed.py --demo --limit 25 --seed 42
cd frontend
npm ci
cp .env.example .env.local
```

Terminal 1: `cd backend && ../backend/.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
Terminal 2: `cd frontend && npm run dev`.

The Windows path was exercised in this workspace. The POSIX commands are equivalent instructions, not an independently executed platform test. Docker was unavailable here; actual integration verification used portable MySQL 8.4.11. See `docs/verification.md` for exact evidence.

## Open the application

| Service | URL |
| --- | --- |
| Application | http://localhost:3000 |
| API/OpenAPI | http://127.0.0.1:8000/docs |
| Liveness/readiness | http://127.0.0.1:8000/api/health · `/api/ready` |
| MySQL | `127.0.0.1:3306`, database/user `novaroute` |

The current workspace's isolated portable MySQL runs on **3307** because an existing database occupied 3306. Its ignored local `.env` is already configured accordingly. Compose clean setups use 3306; choose another host port and update `DATABASE_URL` if occupied. Do not stop or alter an unrelated local database.

Local demo password for all accounts: **`NovaRouteDemo!2026`**

| Email | Role / profile |
| --- | --- |
| `student@novaroute.test` | Student, software |
| `database@novaroute.test` | Student, databases |
| `data@novaroute.test` | Student, data/ML |
| `employer@novaroute.test` | Fictional Nova Labs demo employer |

| `admin@example.com` | System Admninstrator  | password: `admin12345`

Development seeds never overwrite existing profiles or user-edited listings. Production rejects demo-account authentication and demo seeding. All `.test` recipient addresses are used by default; real recipient addresses are blocked unless explicitly enabled.

## Kaggle data

The actual dataset was downloaded and its headers inspected. To import your downloaded CSV:

```bash
python database/seed.py --csv database/data/internship.csv --limit 25 --seed 42
```

Use either that command or `--demo` for your presentation. Imported source examples are labelled historical and belong to the fictional seed employer. Original company names are preserved as provenance, not impersonated accounts. See `docs/dataset.md` for verified headers, download instructions, license metadata, mapping and limitations. Source Kaggle data is not copied into this repository.

## AI, email, and recovery

For live mode, edit root `.env`: set `AI_MODE=live`, `OPENROUTER_API_KEY`, and `OPENROUTER_MODEL`. From `backend`, run `python -m app.jobs.check_provider` to inspect current supported Qwen IDs. The catalog advertised `qwen/qwen3.8-flash` with `response_format` and `structured_outputs` during implementation; provider availability can change. Restart FastAPI after settings changes. No paid OpenRouter request was exercised without credentials.

`python -m app.jobs.model` downloads/loads MiniLM. After a successful download, `HF_HUB_OFFLINE=1` can force cache-only inference. `EMBEDDING_LOAD_ON_START=true` warms each backend process at startup; otherwise the first recommendation request loads it once.

**RAG Q&A:** The simple RAG system uses the same MiniLM embeddings to answer questions about internships. No additional setup required - it works with the existing internship database. Access via `/student/ask-ai` in the UI or `POST /api/simple-rag/query` API endpoint.

External email/Gmail syncing integrations, Mailpit dependencies, and UI failure tags (`Email: failed`) have been removed. For an external SMTP provider, configure host, port, username, password and `SMTP_STARTTLS=true` (or `SMTP_SSL=true` on implicit TLS). Enable `SMTP_ALLOW_REAL_RECIPIENTS=true` only when you intend to send to real people.

After a restart or failure, run from `backend`:

```bash
python -m app.jobs.delivery --limit 50
python -m app.jobs.model --retry-matches
```

Email retries honor bounded exponential delay (up to one hour); active claims expire after ten minutes. Feedback retries also work for notifications whose email preference was disabled. A factual fallback email is not resent just because later feedback succeeds; updated advice appears in the inbox. `BackgroundTasks` is not a durable queue. The persisted outbox plus manual retry handles restart recovery; a crash after SMTP acceptance can still produce a duplicate delivery.

## Verification commands

Create an isolated MySQL database **`novaroute_test`**, grant the development account access, and never point tests at your working database. For Compose:

```bash
docker compose exec mysql mysql -uroot -plocal_root_password -e "CREATE DATABASE IF NOT EXISTS novaroute_test CHARACTER SET utf8mb4; GRANT ALL ON novaroute_test.* TO 'novaroute'@'%';"
```

From `backend`, PowerShell:

```powershell
$env:TEST_DATABASE_URL='mysql+pymysql://novaroute:local_dev_password@127.0.0.1:3306/novaroute_test?charset=utf8mb4'
python -m pytest -q
python -m ruff check app tests
```

POSIX: `TEST_DATABASE_URL='mysql+pymysql://novaroute:local_dev_password@127.0.0.1:3306/novaroute_test?charset=utf8mb4' python -m pytest -q`.

Tests use Alembic, then delete records **only in the isolated test database** between tests. They do not use SQLite. External paid model calls and routine SMTP are mocked. Optional real checks are documented in `docs/verification.md`.

From `frontend`, with backend, frontend, and MySQL running:

```bash
npm run typecheck
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests require a separately created local administrator supplied through `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD`. They create fresh `.test` accounts and synthetic listings/reports in the configured development database. Safety-review fixtures remain hidden/suspended for inspection. For production preview use `npm run build` then `npm start`, instead of `npm run dev`.

From `backend`, run the small academic experiment:

```bash
python -m app.jobs.evaluate
```

See `docs/evaluation.md`: proposed synthetic labels are separate from independently reviewed labels. This project uses pretrained inference and API integration, not training from scratch. The 0.50 similarity cutoff is not 50% accuracy.

## Data and deployment notes

- Alembic is authoritative. Startup never creates, drops or resets tables. For a fresh manual setup, run `database/init.sql`, then `python -m alembic stamp 0002_employer_trust`; do not run initial migrations again over that schema.
- `docker compose stop` preserves volumes. Deleting MySQL volumes destroys local data and is never a routine setup step.
- Frontend `BACKEND_INTERNAL_URL` is server-side configuration, normally `http://127.0.0.1:8000`. If containerizing the application, use `http://backend:8000`; rebuild Next.js after changing a production rewrite destination. Cookies pass through the rewrite with `credentials: include`. No database or AI secret belongs in a `NEXT_PUBLIC_` variable.
- Use a single backend process for the in-memory rate limiter; multi-process deployments need a shared rate-limit strategy outside this MVP. Model cache is per process. No Redis or task queue is included.
- Production requires HTTPS, `COOKIE_SECURE=true`, `ENVIRONMENT=production`, `AI_MODE=live`, unique credentials, and exact trusted `ALLOWED_ORIGINS`. Local Compose credentials are examples only.
- See `docs/architecture.md`, `docs/api.md`, `docs/ai-design.md`, `docs/demo.md`, and `docs/ui-integration.md` for design details and demonstration flow.

## AI Features Summary

| Feature | Description | Mode Support | UI Location |
|---------|-------------|--------------|-------------|
| **Recommendations** | Semantic similarity matching between student profiles and internships using MiniLM embeddings | Demo + Live | Student Dashboard, Listings |
| **LLM Feedback** | AI-powered application feedback with strengths, gaps, next steps, and practice questions | Demo + Live | Notifications, Applications |
| **RAG Q&A** | AI-powered question answering about internships using semantic search | Demo + Live | `/student/ask-ai` |

All three features share the same MiniLM embedding model (`sentence-transformers/all-MiniLM-L6-v2`) and work together seamlessly.

