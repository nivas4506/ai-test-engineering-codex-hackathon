from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.google_auth import GoogleIdentity
from app.utils.files import save_uploaded_bundle, save_uploaded_input


def test_upload_accepts_single_java_file() -> None:
    upload_id, repository_path = save_uploaded_input(
        "HelloWorld.java",
        b"public class HelloWorld { public static void main(String[] args) { System.out.println(\"hi\"); } }",
    )

    assert upload_id
    assert repository_path.is_dir()
    assert (repository_path / "HelloWorld.java").exists()


def test_upload_accepts_single_package_manifest() -> None:
    upload_id, repository_path = save_uploaded_input(
        "package.json",
        b'{ "name": "demo", "version": "1.0.0" }',
    )

    assert upload_id
    assert repository_path.is_dir()
    assert (repository_path / "package.json").exists()


def test_upload_accepts_single_nested_project_file_path() -> None:
    upload_id, repository_path = save_uploaded_input(
        "demo-folder/package.json",
        b'{ "name": "demo", "version": "1.0.0" }',
    )

    assert upload_id
    assert repository_path.is_dir()
    assert (repository_path / "package.json").exists()


def test_upload_accepts_bundle_with_go_files() -> None:
    upload_id, repository_path = save_uploaded_bundle(
        [
            ("cmd/main.go", b"package main\nfunc main() {}\n"),
            ("pkg/util.go", b"package pkg\nfunc Add(a int, b int) int { return a + b }\n"),
        ]
    )

    assert upload_id
    assert repository_path.is_dir()
    assert (repository_path / "cmd" / "main.go").exists()
    assert (repository_path / "pkg" / "util.go").exists()


def test_analyzer_accepts_generic_language_files(tmp_path: Path) -> None:
    repository = tmp_path / "java-repo"
    repository.mkdir()
    (repository / "App.java").write_text("public class App {}", encoding="utf-8")

    analysis = RepositoryAnalyzer().analyze(str(repository))

    assert analysis.detected_languages == ["generic"]
    assert analysis.generic_files == [str(repository / "App.java")]
    assert len(analysis.modules) == 1
    assert analysis.modules[0].language == "generic"


def test_analyzer_accepts_manifest_only_repository(tmp_path: Path) -> None:
    repository = tmp_path / "manifest-repo"
    repository.mkdir()
    (repository / "package.json").write_text('{ "name": "manifest-only", "version": "1.0.0" }', encoding="utf-8")

    analysis = RepositoryAnalyzer().analyze(str(repository))

    assert analysis.detected_languages == ["generic"]
    assert analysis.generic_files == [str(repository / "package.json")]
    assert len(analysis.modules) == 1
    assert analysis.modules[0].module_import == "package.json"


def test_uploaded_repository_is_restored_when_temp_path_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.routes as routes

    client = TestClient(app)
    monkeypatch.setattr(
        routes,
        "verify_google_credential",
        lambda credential: GoogleIdentity(
            email=f"restore-{uuid4().hex[:8]}@example.com",
            full_name="Restore User",
            google_sub=f"restore-{credential}",
        ),
    )

    login_response = client.post("/auth/google", json={"credential": "restore-credential"})
    assert login_response.status_code == 200

    upload_response = client.post(
        "/upload",
        files={
            "file": ("math_utils.py", b"def add(a, b):\n    return a + b\n", "text/x-python"),
        },
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()

    uploaded_repo_path = Path(payload["repository_path"])
    assert uploaded_repo_path.exists()
    for child in uploaded_repo_path.rglob("*"):
        if child.is_file():
            child.unlink()
    uploaded_repo_path.rmdir()

    orchestrate_response = client.post(
        "/orchestrate",
        json={
            "repository_path": payload["repository_path"],
            "upload_id": payload["upload_id"],
            "max_retries": 1,
        },
    )

    assert orchestrate_response.status_code == 200
    assert orchestrate_response.json()["status"] == "passed"


def test_orchestrate_accepts_upload_id_without_repository_path(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.routes as routes

    client = TestClient(app)
    monkeypatch.setattr(
        routes,
        "verify_google_credential",
        lambda credential: GoogleIdentity(
            email=f"upload-only-{uuid4().hex[:8]}@example.com",
            full_name="Upload Only User",
            google_sub=f"upload-only-{credential}",
        ),
    )

    login_response = client.post("/auth/google", json={"credential": "upload-only-credential"})
    assert login_response.status_code == 200

    upload_response = client.post(
        "/upload",
        files={
            "file": ("math_utils.py", b"def add(a, b):\n    return a + b\n", "text/x-python"),
        },
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()

    orchestrate_response = client.post(
        "/orchestrate",
        json={
            "upload_id": payload["upload_id"],
            "max_retries": 1,
        },
    )

    assert orchestrate_response.status_code == 200
    report = orchestrate_response.json()
    assert report["status"] == "passed"
    assert report["repository_path"]
