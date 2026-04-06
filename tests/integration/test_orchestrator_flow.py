from pathlib import Path

import pytest

from app.models.schemas import BrowserProbeResult
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
    assert report.architecture == "multi_agent"
    assert report.memory_context
    assert any(entry.agent == "planner" for entry in report.agent_trace)
    assert any(entry.agent == "executor" for entry in report.agent_trace)
    assert any(entry.agent == "critic" for entry in report.agent_trace)
    assert any(entry.agent == "memory" for entry in report.agent_trace)
    assert report.test_plan
    assert report.execution_steps
    assert report.observations
    assert report.final_structured_report.tests_run >= 0
    assert (temp_run_dir / "artifacts" / "final_report.json").exists()
    assert (temp_run_dir / "artifacts" / "coverage_report.json").exists()
    assert (temp_run_dir / "artifacts" / "improvement_report.json").exists()
    assert (temp_run_dir / "artifacts" / "test_plan.json").exists()
    assert (temp_run_dir / "artifacts" / "execution_steps.json").exists()
    assert (temp_run_dir / "artifacts" / "observations.json").exists()
    assert (temp_run_dir / "artifacts" / "final_structured_report.json").exists()
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


@pytest.mark.integration
def test_orchestrator_records_selenium_probe_for_target_url(
    monkeypatch: pytest.MonkeyPatch,
    simple_python_repo: Path,
    temp_run_dir: Path,
) -> None:
    monkeypatch.setattr(
        "app.services.orchestrator.create_run_directory",
        lambda: ("seleniumrun", temp_run_dir),
    )

    service = OrchestratorService()
    service.generator.openai_writer._client = None
    monkeypatch.setattr(
        service.selenium_probe,
        "probe",
        lambda url: BrowserProbeResult(
            status="passed",
            url=url,
            final_url=url,
            title="Demo App",
            forms_detected=1,
            buttons_detected=2,
            links_detected=3,
            notes=["Loaded demo app."],
        ),
    )

    report = service.orchestrate(
        str(simple_python_repo),
        max_retries=1,
        user_id=None,
        target_input="https://example.com",
    )

    assert report.browser_probe is not None
    assert report.browser_probe.status == "passed"
    assert any(observation.title == "Selenium browser probe" for observation in report.observations)
