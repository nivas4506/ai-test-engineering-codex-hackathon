# 🚀 AI Test Engineering Platform

The **AI Test Engineering** platform is an advanced, automated agentic system designed for repository analysis, pytest generation, execution, and retry orchestration. It features a modern liquid-style dashboard built with FastAPI.

---

## 📋 Core Process: Step-by-Step

Follow these steps to get the platform up and running and start generating AI-driven tests.

### 1️⃣ Environment Setup
Ensure you have Python installed, then set up the virtual environment:

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### 2️⃣ Configuration
The platform uses OpenAI for intelligent test generation. Set your credentials in your environment or a `.env` file:

```powershell
# Required: Your OpenAI API key
$env:OPENAI_API_KEY="your_api_key_here"

# Optional: Preferred model (defaults to gpt-5-mini if omitted)
$env:OPENAI_MODEL="gpt-5-mini"

# Optional: Reasoning effort (if using reasoning models)
$env:OPENAI_REASONING_EFFORT="low"
```
> [!TIP]
> If no API key is present, the platform automatically falls back to a rule-based heuristic test generator.

### 3️⃣ Launching the Application
Start the FastAPI development server:

```powershell
uvicorn app.main:app --reload
```

### 4️⃣ Repository Analysis & Test Generation
Once the server is running, navigate to the web interface or use the API to trigger orchestration.

**Dashboard Access:**
- 🏠 **Main Dashboard:** `http://127.0.0.1:8000/`
- 🤖 **Agent View:** `http://127.0.0.1:8000/agents`
- 📖 **Playbooks:** `http://127.0.0.1:8000/playbooks`
- 📊 **Reports:** `http://127.0.0.1:8000/reports`

**Triggering via API (Example):**
```powershell
curl -X POST http://127.0.0.1:8000/orchestrate `
  -H "Content-Type: application/json" `
  -d "{\"repository_path\":\"C:\\path\\to\\your\\repo\",\"max_retries\":2}"
```

### 5️⃣ Execution & Execution Monitoring
The orchestrator will:
1.  **Analyze** the target repository structure.
2.  **Generate** `pytest` cases using OpenAI (or heuristics).
3.  **Execute** the tests.
4.  **Retry** failing tests with AI-assisted fixes (up to `max_retries`).
5.  **Finalize** results and generate a visual report in the `/reports` section.

---

## 🛠️ Language Support
The platform currently supports:
- ✅ **Python:** Analysis, test generation, and `pytest` execution.
- ✅ **JavaScript:** Analysis, test generation, and Node.js built-in test runner execution.
- 🚧 **TypeScript:** Analysis and test generation (Execution requires local `tsx`, `vitest`, or `jest` dependencies).

## 📽️ Demo Video
[Watch the platform in action](https://github.com/user-attachments/assets/9b67132b-9399-41cf-b637-cf238055cc40)

---
*Created with ❤️ by the AI Test Engineering Team*


