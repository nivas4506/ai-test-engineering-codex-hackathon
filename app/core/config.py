from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = BASE_DIR / "workspace" / "runs"
DEFAULT_MAX_RETRIES = 2
DEFAULT_TEST_TIMEOUT_SECONDS = 60
