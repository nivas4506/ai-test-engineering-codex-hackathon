# AI Test Engineer MVP

Minimal FastAPI prototype for automated repository analysis, pytest generation, execution, retry orchestration, and a liquid-style frontend for AI Test Engineering.

Current language support:

- Python: analyze, generate tests, execute with `pytest`
- JavaScript: analyze, generate tests, execute with Node's built-in test runner
- TypeScript: analyze and generate tests; execution requires a project dependency such as `tsx`, `vitest`, or `jest`

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/agents`
- `http://127.0.0.1:8000/playbooks`
- `http://127.0.0.1:8000/reports`

## OpenAI Integration

The product now supports OpenAI-backed test generation through the Responses API.

Copy [.env.example](C:\Users\A\OneDrive\Documents\Codex%20hackathon\.env.example) to `.env` or set these environment variables before starting the app:

```powershell
$env:OPENAI_API_KEY="your_api_key"
$env:OPENAI_MODEL="gpt-5-mini"
$env:OPENAI_REASONING_EFFORT="low"
```

`OPENAI_MODEL` is optional. If omitted, the app defaults to `gpt-5-mini`.
If no API key is present, the generator falls back to the built-in heuristic path.
When configured, the dashboard shows the active provider and model so you can confirm the app is actually using OpenAI generation.

## Example

```powershell
curl -X POST http://127.0.0.1:8000/orchestrate `
  -H "Content-Type: application/json" `
  -d "{\"repository_path\":\"C:\\Users\\A\\OneDrive\\Documents\\Codex hackathon\\samples\\demo_repo\",\"max_retries\":2}"
```
