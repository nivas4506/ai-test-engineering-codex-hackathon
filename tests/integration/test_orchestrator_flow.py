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
    assert (temp_run_dir / "artifacts" / "final_report.json").exists()
    assert any(path.name == "test_math_utils.py" for path in (temp_run_dir / "generated_tests").iterdir())
