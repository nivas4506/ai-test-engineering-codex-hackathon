from pathlib import Path

import pytest

from app.models.schemas import AnalysisResult, ModuleSummary, PlanResult
from app.services.test_generator import TestGeneratorService as GeneratorService


@pytest.mark.unit
def test_safe_mode_still_generates_smoke_tests_for_modules_without_functions(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    source_file = repository / "package.json"
    source_file.write_text('{ "name": "demo", "version": "1.0.0" }', encoding="utf-8")

    run_dir = tmp_path / "run"
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "generated_tests").mkdir(parents=True)

    analysis = AnalysisResult(
        repository_path=str(repository),
        python_files=[],
        javascript_files=[],
        typescript_files=[],
        generic_files=[str(source_file)],
        detected_languages=["generic"],
        modules=[
            ModuleSummary(
                file_path=str(source_file),
                module_import="package.json",
                language="generic",
                functions=[],
            )
        ],
    )
    plan = PlanResult(modules=[], summary="generic smoke test plan")

    result = GeneratorService().generate(str(repository), run_dir, analysis, plan, mode="safe")

    assert len(result.generated_files) == 1
    generated_path = run_dir / "generated_tests" / "test_package_json.py"
    assert generated_path.exists()
    generated_content = generated_path.read_text(encoding="utf-8")
    assert "def test_source_file_exists()" in generated_content
