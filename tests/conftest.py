import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def simple_python_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "math_utils.py").write_text(
        "def add(a, b):\n"
        "    return a + b\n\n"
        "def meaning():\n"
        "    return 42\n",
        encoding="utf-8",
    )
    return repo


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "generated_tests").mkdir(parents=True)
    return run_dir
