from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.db import init_database
from app.services.auth import resolve_current_user


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="AI Test Engineering", version="0.1.0", lifespan=lifespan)
app.include_router(router)
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def render_template(template_name: str) -> str:
    return (BASE_DIR / "templates" / template_name).read_text(encoding="utf-8")


def require_authenticated_page(request: Request) -> RedirectResponse | None:
    user = resolve_current_user(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return None


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    redirect = require_authenticated_page(request)
    if redirect is not None:
        return redirect
    return render_template("index.html")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if resolve_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)
    return render_template("login.html")


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    if resolve_current_user(request) is not None:
        return RedirectResponse(url="/", status_code=303)
    return render_template("signup.html")


@app.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request):
    redirect = require_authenticated_page(request)
    if redirect is not None:
        return redirect
    return render_template("agents.html")


@app.get("/playbooks", response_class=HTMLResponse)
def playbooks_page(request: Request):
    redirect = require_authenticated_page(request)
    if redirect is not None:
        return redirect
    return render_template("playbooks.html")


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    redirect = require_authenticated_page(request)
    if redirect is not None:
        return redirect
    return render_template("reports.html")


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    redirect = require_authenticated_page(request)
    if redirect is not None:
        return redirect
    return render_template("profile.html")


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
