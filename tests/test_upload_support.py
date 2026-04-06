from pathlib import Path

import pytest

from app.services.repository_analyzer import RepositoryAnalyzer
from app.utils.files import save_uploaded_bundle, save_uploaded_input


def test_upload_accepts_single_java_file() -> None:
    upload_id, repository_path = save_uploaded_input(
        "HelloWorld.java",
        b"public class HelloWorld { public static void main(String[] args) { System.out.println(\"hi\"); } }",
    )

    assert upload_id
    assert repository_path.is_dir()
    assert (repository_path / "HelloWorld.java").exists()


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


def test_analyzer_explains_unsupported_language(tmp_path: Path) -> None:
    repository = tmp_path / "java-repo"
    repository.mkdir()
    (repository / "App.java").write_text("public class App {}", encoding="utf-8")

    with pytest.raises(ValueError, match="currently supports Python, JavaScript, and TypeScript projects only"):
        RepositoryAnalyzer().analyze(str(repository))
