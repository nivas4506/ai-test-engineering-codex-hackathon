from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from app.core.config import WORKSPACE_DIR


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_run_directory() -> tuple[str, Path]:
    run_id = uuid.uuid4().hex[:12]
    run_dir = ensure_directory(WORKSPACE_DIR / run_id)
    ensure_directory(run_dir / "artifacts")
    ensure_directory(run_dir / "generated_tests")
    return run_id, run_dir


def snapshot_repository_metadata(repository_path: Path, run_dir: Path) -> Path:
    metadata = {
        "repository_path": str(repository_path.resolve()),
        "entries": sorted(str(path.relative_to(repository_path)) for path in repository_path.rglob("*")),
    }
    output_path = run_dir / "artifacts" / "repository_snapshot.json"
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output_path


def write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def reset_generated_tests_dir(run_dir: Path) -> Path:
    target = run_dir / "generated_tests"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    return target
