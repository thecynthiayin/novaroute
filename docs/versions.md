# Verified dependency versions

Resolved from the official npm/PyPI registries on 2026-09-20. Python 3.12.14, Node 24.14.0, npm 11.9.0.

## Backend runtime

```text
fastapi==0.141.1
uvicorn==0.53.0
pydantic==2.13.5
pydantic-settings==2.15.0
SQLAlchemy==2.0.54
alembic==1.20.0
PyMySQL[rsa]==1.2.3
argon2-cffi==25.1.0
email-validator==2.3.0
python-multipart==0.0.32
pdfplumber==0.11.10
sentence-transformers==5.7.0
openai==2.54.0
pandas==2.3.3
httpx==0.28.1
```

Full installed Python environment: `backend/requirements-lock.txt`.

## Frontend

| Package | Version |
| --- | --- |
| @hookform/resolvers | 5.9.1 |
| @radix-ui/react-dialog | 1.1.23 |
| @tanstack/react-query | 5.103.1 |
| lucide-react | 0.577.0 |
| next | 16.3.5 |
| next-themes | 0.4.6 |
| react | 19.3.0 |
| react-dom | 19.3.0 |
| react-hook-form | 7.88.0 |
| sonner | 2.0.8 |
| zod | 4.6.5 |
| @eslint/js | 10.0.1 |
| @next/eslint-plugin-next | 16.3.5 |
| @playwright/test | 1.63.0 |
| @tailwindcss/postcss | 4.3.3 |
| @types/node | 24.13.6 |
| @types/react | 19.3.0 |
| @types/react-dom | 19.3.0 |
| eslint | 10.11.0 |
| prettier | 3.9.8 |
| tailwindcss | 4.3.3 |
| typescript | 5.9.3 |
| typescript-eslint | 8.70.0 |

MySQL 8.4.11 and Mailpit 1.31.2 were tested natively. Compose pins those versions. ESLint 10 uses the supported TypeScript ESLint and Next rule packages directly; incompatible legacy React rule bundles are not installed. `npm audit` reported zero vulnerabilities at installation; this is a point-in-time result.
