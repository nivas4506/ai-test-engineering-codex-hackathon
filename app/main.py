from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


app = FastAPI(title="AI Test Enigneering", version="0.1.0")
app.include_router(router)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def render_template(template_name: str) -> str:
    return (BASE_DIR / "templates" / template_name).read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index():
    return render_template("index.html")


@app.get("/agents", response_class=HTMLResponse)
def agents_page():
    return render_template("agents.html")


@app.get("/playbooks", response_class=HTMLResponse)
def playbooks_page():
    return render_template("playbooks.html")


@app.get("/reports", response_class=HTMLResponse)
def reports_page():
    return render_template("reports.html")


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
