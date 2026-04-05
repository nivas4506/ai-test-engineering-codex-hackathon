import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
IS_VERCEL = os.getenv("VERCEL") == "1"
DEFAULT_WORKSPACE_ROOT = Path("/tmp/ai-test-engineering") if IS_VERCEL else BASE_DIR / "workspace"
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", str(DEFAULT_WORKSPACE_ROOT)))
WORKSPACE_DIR = WORKSPACE_ROOT / "runs"
UPLOADS_DIR = WORKSPACE_ROOT / "uploads"
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
DEFAULT_MAX_RETRIES = 2
DEFAULT_TEST_TIMEOUT_SECONDS = 60
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "ai_test_engineering_token")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true" if IS_VERCEL else "false").strip().lower() in {"1", "true", "yes", "on"}
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax")
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
SAMPLE_REPOSITORY_PATH = BASE_DIR / "samples" / "demo_repo"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()


def _as_bool(raw: str, default: bool = False) -> bool:
    value = raw.strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(WORKSPACE_ROOT / 'app.db').as_posix()}")
DATABASE_ECHO = _as_bool(os.getenv("DATABASE_ECHO", "false"))
DATABASE_POOL_PRE_PING = _as_bool(os.getenv("DATABASE_POOL_PRE_PING", "true"), default=True)
DATABASE_POOL_RECYCLE = int(os.getenv("DATABASE_POOL_RECYCLE", "1800"))
