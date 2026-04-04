# AI Test Engineer MVP

Minimal FastAPI prototype for automated repository analysis, pytest generation, execution, retry orchestration, and a liquid-style frontend for AI Test Enigneering.

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

## Example

```powershell
curl -X POST http://127.0.0.1:8000/orchestrate `
  -H "Content-Type: application/json" `
  -d "{\"repository_path\":\"C:\\Users\\A\\OneDrive\\Documents\\Codex hackathon\\samples\\demo_repo\",\"max_retries\":2}"
```
