import pytest

from app.models.schemas import AnalysisResult, ModuleFunction, ModuleSummary
from app.services.planner import PlannerService


@pytest.mark.unit
def test_planner_assigns_priorities_and_language_strategies() -> None:
    analysis = AnalysisResult(
        repository_path="repo",
        python_files=["repo/math_utils.py"],
        javascript_files=["repo/index.js"],
        typescript_files=[],
        detected_languages=["python", "javascript"],
        modules=[
            ModuleSummary(
                file_path="repo/math_utils.py",
                module_import="math_utils",
                language="python",
                functions=[
                    ModuleFunction(
                        name="meaning",
                        line_number=1,
                        arg_count=0,
                        required_arg_count=0,
                        parameter_names=[],
                        has_defaults=False,
                        inferred_cases=[],
                    ),
                    ModuleFunction(
                        name="add",
                        line_number=4,
                        arg_count=2,
                        required_arg_count=2,
                        parameter_names=["a", "b"],
                        has_defaults=False,
                        inferred_cases=[],
                    ),
                ],
            ),
            ModuleSummary(
                file_path="repo/index.js",
                module_import="index.js",
                language="javascript",
                functions=[],
            ),
        ],
    )

    plan = PlannerService().create_plan(analysis)

    assert len(plan.modules) == 2
    python_module = plan.modules[0]
    javascript_module = plan.modules[1]

    assert python_module.priority == "medium"
    assert "callable existence test" in python_module.strategy
    assert "zero-argument execution smoke test" in python_module.strategy

    assert javascript_module.priority == "low"
    assert "import smoke test" in javascript_module.strategy
    assert "node-compatible module load test" in javascript_module.strategy
    assert "Javascript" in plan.summary or "JavaScript" in plan.summary
