from pathlib import Path

import pytest

from app.services.orchestrator import OrchestratorService


@pytest.mark.integration
def test_orchestrator_generates_executes_and_writes_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    simple_python_repo: Path,
    temp_run_dir: Path,
) -> None:
    monkeypatch.setattr(
        "app.services.orchestrator.create_run_directory",
        lambda: ("integrationrun", temp_run_dir),
    )

    service = OrchestratorService()
    service.generator.openai_writer._client = None

    report = service.orchestrate(str(simple_python_repo), max_retries=1, user_id=None)

    assert report.run_id == "integrationrun"
    assert report.status == "passed"
    assert report.iterations >= 1
    assert report.generation_history
    assert report.execution_history
    assert report.coverage_report.estimated_line_coverage > 0
    assert report.improvement_report.rerun_summary
    assert report.improvement_report.ci_cd_suggestions
    assert (temp_run_dir / "artifacts" / "final_report.json").exists()
    assert (temp_run_dir / "artifacts" / "coverage_report.json").exists()
    assert (temp_run_dir / "artifacts" / "improvement_report.json").exists()
    assert any(path.name == "test_math_utils.py" for path in (temp_run_dir / "generated_tests").iterdir())


@pytest.mark.integration
def test_orchestrator_runs_generic_source_smoke_tests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    temp_run_dir: Path,
) -> None:
    repository = tmp_path / "generic-repo"
    repository.mkdir()
    (repository / "App.java").write_text(
        "public class App { public static void main(String[] args) { System.out.println(\"ok\"); } }\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "app.services.orchestrator.create_run_directory",
        lambda: ("genericrun", temp_run_dir),
    )

    service = OrchestratorService()
    service.generator.openai_writer._client = None

    report = service.orchestrate(str(repository), max_retries=1, user_id=None)

    assert report.run_id == "genericrun"
    assert report.status == "passed"
    assert report.analysis.detected_languages == ["generic"]
    assert report.execution_history
    assert report.execution_history[-1].tests_collected is not None
    assert any(path.name == "test_App_java.py" for path in (temp_run_dir / "generated_tests").iterdir())


@pytest.mark.integration
def test_orchestrator_runs_manifest_only_repository_smoke_tests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    temp_run_dir: Path,
) -> None:
    repository = tmp_path / "manifest-repo"
    repository.mkdir()
    (repository / "package.json").write_text(
        '{ "name": "manifest-repo", "version": "1.0.0" }\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "app.services.orchestrator.create_run_directory",
        lambda: ("manifestrun", temp_run_dir),
    )

    service = OrchestratorService()
    service.generator.openai_writer._client = None

    report = service.orchestrate(str(repository), max_retries=1, user_id=None)

    assert report.run_id == "manifestrun"
    assert report.status == "passed"
    assert report.analysis.detected_languages == ["generic"]
    assert report.execution_history[-1].tests_collected is not None
    assert any(path.name == "test_package_json.py" for path in (temp_run_dir / "generated_tests").iterdir())
