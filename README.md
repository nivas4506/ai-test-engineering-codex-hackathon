# AI Test Engineering

AI Test Engineering is a FastAPI product that analyzes repositories, generates tests, runs them, retries on failures, and presents the results in a user-facing dashboard.

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The project targets Python `3.13`.

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/agents`
- `http://127.0.0.1:8000/playbooks`
- `http://127.0.0.1:8000/reports`
- `http://127.0.0.1:8000/profile`

## Environment

Set these locally or in `.env`:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_MODEL="gpt-5-mini"
$env:OPENAI_REASONING_EFFORT="low"
```

Optional local database:

```powershell
$env:DATABASE_URL="sqlite:///./workspace/app.db"
```

## OAuth2 and Sessions

The API uses an OAuth2 password-bearer login endpoint at `/auth/token` and stores authenticated browser sessions in the database. For deployed environments, cookies should be secure and the database must be external.

## Vercel Deployment

The repo includes:

- `vercel.json` to disable duplicate Git-triggered deploys when GitHub Actions handles CI/CD
- `app/index.py` as the Vercel Python entrypoint
- GitHub Actions for CI, preview deploys, and production deploys

Recommended Vercel environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_REASONING_EFFORT`
- `DATABASE_URL`
- `AUTH_COOKIE_SECURE=true`

Important:

- Use PostgreSQL or MySQL on Vercel. Do not rely on SQLite for real deployed user data.
- The app writes temporary uploads and generated test artifacts under `/tmp/ai-test-engineering` on Vercel.

## GitHub Actions Secrets

Set these repository secrets before enabling the workflows:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Optional app secrets:

- `OPENAI_API_KEY`
- `DATABASE_URL`

## CI/CD Flow

- `.github/workflows/ci.yml`: runs `pytest`
- `.github/workflows/vercel-preview.yml`: tests, builds, and deploys preview environments for PRs
- `.github/workflows/vercel-production.yml`: tests, builds, and deploys production on `main`
- `.github/workflows/k8s-deploy.yml`: left as manual-only so it no longer conflicts with Vercel

## Language Support

- Python: analysis, test generation, and `pytest` execution
- JavaScript: analysis, test generation, and `node --test` execution
- TypeScript: analysis and generation, with execution depending on project tooling
