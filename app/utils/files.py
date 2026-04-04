from __future__ import annotations

import json
import shutil
import tarfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import UPLOADS_DIR, WORKSPACE_DIR
from app.models.schemas import RunListItem


SUPPORTED_SOURCE_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".jsx", ".ts", ".tsx"}
UNSUPPORTED_ARCHIVE_SUFFIXES = {".rar", ".7z", ".bz2", ".xz"}


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


def get_run_report_path(run_id: str) -> Path:
    return WORKSPACE_DIR / run_id / "artifacts" / "final_report.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def list_run_reports(limit: int = 20) -> list[RunListItem]:
    ensure_directory(WORKSPACE_DIR)
    items: list[RunListItem] = []
    for run_dir in sorted(
        [path for path in WORKSPACE_DIR.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        report_path = run_dir / "artifacts" / "final_report.json"
        if not report_path.exists():
            continue
        report = read_json(report_path)
        latest_execution = report.get("execution_history", [])
        latest_test_count = latest_execution[-1].get("tests_collected") if latest_execution else None
        items.append(
            RunListItem(
                run_id=report["run_id"],
                repository_path=report["repository_path"],
                status=report["status"],
                iterations=report["iterations"],
                created_at=datetime.fromisoformat(report["analysis"]["created_at"]),
                latest_test_count=latest_test_count,
            )
        )
        if len(items) >= limit:
            break
    return items


def save_uploaded_input(filename: str, content: bytes) -> tuple[str, Path]:
    upload_id = uuid.uuid4().hex[:12]
    upload_root = ensure_directory(UPLOADS_DIR / upload_id)
    archive_path = upload_root / filename
    archive_path.write_bytes(content)

    extracted_dir = upload_root / "repo"
    ensure_directory(extracted_dir)

    suffixes = {suffix.lower() for suffix in Path(filename).suffixes}
    if suffixes & UNSUPPORTED_ARCHIVE_SUFFIXES:
        raise ValueError("Unsupported archive format. Please upload a .zip, .tar, .tar.gz, or .tgz file.")

    if zipfile.is_zipfile(archive_path):
        _extract_zip_archive(archive_path, extracted_dir)
        normalized_root = _normalize_extracted_root(extracted_dir)
        _validate_uploaded_repository(normalized_root)
        return upload_id, normalized_root

    if tarfile.is_tarfile(archive_path):
        _extract_tar_archive(archive_path, extracted_dir)
        normalized_root = _normalize_extracted_root(extracted_dir)
        _validate_uploaded_repository(normalized_root)
        return upload_id, normalized_root

    target_file = extracted_dir / Path(filename).name
    target_file.write_bytes(content)
    _validate_uploaded_repository(target_file)
    return upload_id, extracted_dir


def _extract_zip_archive(archive_path: Path, extracted_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Archive contains unsafe paths.")
            archive.extract(member, extracted_dir)


def _extract_tar_archive(archive_path: Path, extracted_dir: Path) -> None:
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Archive contains unsafe paths.")
            archive.extract(member, extracted_dir)


def _normalize_extracted_root(extracted_dir: Path) -> Path:
    children = [child for child in extracted_dir.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted_dir


def _validate_uploaded_repository(path: Path) -> None:
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
            raise ValueError(
                "Uploaded file is not a supported source file. Use Python, JavaScript, or TypeScript files, or upload a supported archive."
            )
        return

    if not path.exists() or not path.is_dir():
        raise ValueError("Uploaded content could not be prepared as a repository.")

    has_supported_files = any(file_path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES for file_path in path.rglob("*") if file_path.is_file())
    if not has_supported_files:
        raise ValueError(
            "No supported source files found in upload. Include .py, .js, .ts, .tsx, .jsx, .cjs, or .mjs files."
        )
