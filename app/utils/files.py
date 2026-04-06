from __future__ import annotations

import json
import re
import shutil
import tarfile
import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from app.core.config import UPLOADS_DIR, WORKSPACE_DIR
from app.models.schemas import RunListItem


TESTABLE_SOURCE_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".jsx", ".ts", ".tsx"}
ALLOWED_CODE_SUFFIXES = TESTABLE_SOURCE_SUFFIXES | {
    ".java",
    ".kt",
    ".kts",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".scala",
    ".cs",
    ".fs",
    ".fsi",
    ".fsx",
    ".vb",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".cxx",
    ".hpp",
    ".hh",
    ".m",
    ".mm",
    ".lua",
    ".r",
    ".dart",
    ".ex",
    ".exs",
    ".erl",
    ".hrl",
    ".clj",
    ".cljs",
    ".groovy",
    ".gvy",
    ".pl",
    ".pm",
    ".jl",
    ".nim",
    ".zig",
    ".ml",
    ".mli",
    ".sol",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".psm1",
    ".psd1",
    ".bat",
    ".cmd",
}
PROJECT_MARKER_FILENAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "pipfile",
    "pipfile.lock",
    "poetry.lock",
    "environment.yml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "cargo.toml",
    "go.mod",
    "composer.json",
    "gemfile",
    "rakefile",
    "cmakelists.txt",
    "makefile",
    "mix.exs",
    "rebar.config",
    "project.clj",
    "deps.edn",
    "package.swift",
    "pubspec.yaml",
}
PROJECT_MARKER_SUFFIXES = {
    ".csproj",
    ".fsproj",
    ".vbproj",
    ".sln",
    ".xcodeproj",
    ".xcworkspace",
}
UNSUPPORTED_ARCHIVE_SUFFIXES = {".rar", ".7z", ".bz2", ".xz"}
UPLOAD_PATH_PATTERN = re.compile(r"[/\\]uploads[/\\](?P<upload_id>[a-f0-9]{12})[/\\]repo(?:[/\\]|$)")


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


def save_uploaded_bundle(files: list[tuple[str, bytes]]) -> tuple[str, Path]:
    if not files:
        raise ValueError("No files were uploaded.")

    upload_id = uuid.uuid4().hex[:12]
    upload_root = ensure_directory(UPLOADS_DIR / upload_id)
    repo_root = ensure_directory(upload_root / "repo")

    for relative_name, content in files:
        relative_path = _safe_relative_path(relative_name)
        target_file = repo_root / relative_path
        ensure_directory(target_file.parent)
        target_file.write_bytes(content)

    _validate_uploaded_repository(repo_root)
    return upload_id, repo_root


def package_repository_bytes(path: Path) -> bytes:
    source = path.resolve()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        if source.is_file():
            archive.writestr(source.name, source.read_bytes())
        else:
            for file_path in sorted(source.rglob("*")):
                if file_path.is_file():
                    archive.write(file_path, arcname=file_path.relative_to(source).as_posix())
    return buffer.getvalue()


def restore_uploaded_repository(upload_id: str, bundle_bytes: bytes) -> Path:
    upload_root = ensure_directory(UPLOADS_DIR / upload_id)
    extracted_dir = upload_root / "repo"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    ensure_directory(extracted_dir)

    archive_buffer = BytesIO(bundle_bytes)
    with zipfile.ZipFile(archive_buffer) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("Stored upload contains unsafe paths.")
            archive.extract(member, extracted_dir)

    normalized_root = _normalize_extracted_root(extracted_dir)
    _validate_uploaded_repository(normalized_root)
    return normalized_root


def extract_upload_id_from_repository_path(repository_path: str | None) -> str | None:
    if not repository_path:
        return None
    match = UPLOAD_PATH_PATTERN.search(repository_path)
    return match.group("upload_id") if match else None


def is_supported_project_file(path: Path) -> bool:
    file_name = path.name.lower()
    suffix = path.suffix.lower()
    return suffix in ALLOWED_CODE_SUFFIXES or file_name in PROJECT_MARKER_FILENAMES or suffix in PROJECT_MARKER_SUFFIXES


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


def _safe_relative_path(raw_path: str) -> Path:
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or relative_path.drive or relative_path.root:
        raise ValueError("Uploaded files must not contain absolute paths.")
    if any(part == ".." for part in relative_path.parts):
        raise ValueError("Uploaded files contain unsafe parent paths.")
    return relative_path


def _validate_uploaded_repository(path: Path) -> None:
    if path.is_file():
        if not is_supported_project_file(path):
            raise ValueError(
                "Uploaded file is not recognized as source code or a project file. Upload a project file, code file, repository folder, or supported archive."
            )
        return

    if not path.exists() or not path.is_dir():
        raise ValueError("Uploaded content could not be prepared as a repository.")

    has_supported_project_files = any(is_supported_project_file(file_path) for file_path in path.rglob("*") if file_path.is_file())
    if not has_supported_project_files:
        raise ValueError(
            "No source code or project files were found in upload. Include a repository, archive, or project files from a programming language or framework."
        )
