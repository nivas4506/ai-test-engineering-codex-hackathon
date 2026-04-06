import subprocess
from pathlib import Path

import pytest

from app.services.executor import PytestExecutor


@pytest.mark.unit
def test_build_command_prefers_pytest_for_python_tests(temp_run_dir: Path, simple_python_repo: Path) -> None:
    generated_dir = temp_run_dir / "generated_tests"
    (generated_dir / "test_math_utils.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

    command = PytestExecutor()._build_command(simple_python_repo, generated_dir)

    assert command[1:3] == ["-m", "pytest"]
    assert str(generated_dir) in command


@pytest.mark.unit
def test_build_command_uses_node_test_for_javascript_when_no_runner_dependency(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    test_file = generated_dir / "module.test.cjs"
    test_file.write_text("test('x', () => {})\n", encoding="utf-8")

    command = PytestExecutor()._build_command(repo, generated_dir)

    assert command[:2] == ["node", "--test"]
    assert str(test_file) in command


@pytest.mark.unit
def test_build_command_requires_runner_for_typescript(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    (generated_dir / "module.test.ts").write_text("test('x', async () => {})\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="TypeScript test execution requires"):
        PytestExecutor()._build_command(repo, generated_dir)


@pytest.mark.unit
def test_run_returns_timeout_error(monkeypatch: pytest.MonkeyPatch, simple_python_repo: Path, temp_run_dir: Path) -> None:
    generated_dir = temp_run_dir / "generated_tests"
    (generated_dir / "test_math_utils.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["python", "-m", "pytest"], timeout=1, output="partial", stderr="stalled")

    monkeypatch.setattr("app.services.executor.subprocess.run", raise_timeout)

    result = PytestExecutor().run(str(simple_python_repo), temp_run_dir)

    assert result.status == "error"
    assert result.exit_code == 124
    assert "timed out" in result.stderr.lower()


@pytest.mark.unit
def test_parsers_extract_failures_and_counts() -> None:
    executor = PytestExecutor()
    text = "FAILED tests/test_math.py::test_add - AssertionError: no\n2 passed in 0.12s\n"

    failures = executor._parse_failing_tests(text)
    collected = executor._parse_collected_tests(text)

    assert failures[0].nodeid == "tests/test_math.py::test_add"
    assert collected == 2
