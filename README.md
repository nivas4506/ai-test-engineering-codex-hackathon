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

## Testing Architecture

The test suite is isolated from production code and does not modify application endpoints, UI, or business logic.

Testing structure:

```text
tests/
  conftest.py
  unit/
    test_auth_service.py
    test_debugger_service.py
    test_executor_service.py
    test_planner_service.py
  integration/
    test_orchestrator_flow.py
  e2e/
    test_user_journey.py
  test_auth_api.py
  test_smoke.py
  test_upload_support.py
```

What is covered:

- Unit tests for core functions and service classes
  - auth hashing, token creation, and current-user resolution
  - planner strategy and module prioritization
  - debugger diagnosis paths
  - executor command building, timeout handling, and output parsing
- Integration tests for module interaction
  - analyzer -> planner -> generator -> executor orchestration flow
- Optional end-to-end style flow
  - Google login -> authenticated API access -> system status

Safety and isolation:

- Tests run under `pytest`
- Temporary repositories and run directories are created under pytest temp folders
- External AI generation is not required for tests
- External services are mocked where needed
- Tests do not mutate production UI code or deployed data structures

## Running Tests

Install test dependencies with the main app requirements:

```powershell
pip install -r requirements.txt
```

Run the full suite:

```powershell
pytest
```

Run only unit tests:

```powershell
pytest -m unit
```

Run only integration tests:

```powershell
pytest -m integration
```

Run the optional end-to-end style flow:

```powershell
pytest -m e2e
```

Run a single module:

```powershell
pytest tests/unit/test_executor_service.py
```

## Environment

Set these locally or in `.env`:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:OPENAI_MODEL="gpt-5-mini"
$env:OPENAI_REASONING_EFFORT="low"
$env:GOOGLE_CLIENT_ID="your_google_client_id.apps.googleusercontent.com"
```

Optional local database:

```powershell
$env:DATABASE_URL="sqlite:///./workspace/app.db"
```

## OAuth2 and Sessions

The app now uses Google OAuth 2.0 in the browser and verifies Google ID tokens on the backend before creating a DB-backed session cookie.

Google Cloud Console values for this project:

- Authorized JavaScript origins:
  - `http://127.0.0.1:8000`
  - `http://localhost:8000`
  - `https://ai-test-engineering-codex-hackathon.vercel.app`
- Authorized redirect URIs:
  - none required for the current popup-based Google Sign-In flow

For deployed environments, cookies should be secure and the database must be external.

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

## Demo Video
https://github.com/user-attachments/assets/6496206c-f654-42d1-8dbd-268c217dd288
## Language Support

- Python: analysis, test generation, and `pytest` execution
- JavaScript: analysis, test generation, and `node --test` execution
- TypeScript: analysis and generation, with execution depending on project tooling
