import pytest

from app.models.schemas import ExecutionResult
from app.services.debugger import DebuggerService


def _execution(stdout: str = "", stderr: str = "", status: str = "failed") -> ExecutionResult:
    return ExecutionResult(
        status=status,
        exit_code=1,
        duration_seconds=0.2,
        command=["pytest"],
        stdout=stdout,
        stderr=stderr,
        failing_tests=[],
        tests_collected=1,
    )


@pytest.mark.unit
def test_debugger_detects_import_errors() -> None:
    result = DebuggerService().inspect(_execution(stderr="ModuleNotFoundError: No module named 'x'"), "balanced")

    assert result.next_generation_mode == "safe"
    assert "Import path" in result.diagnosis
    assert result.actions[0].action == "preserve_import_bootstrap"


@pytest.mark.unit
def test_debugger_detects_overeager_execution_tests() -> None:
    result = DebuggerService().inspect(_execution(stderr="TypeError: add() takes 2 positional arguments"), "balanced")

    assert "execution smoke test" in result.diagnosis
    assert result.actions[0].action == "disable_function_execution_tests"


@pytest.mark.unit
def test_debugger_stops_escalation_in_safe_mode() -> None:
    result = DebuggerService().inspect(_execution(stderr="AssertionError"), "safe")

    assert result.next_generation_mode == "safe"
    assert "Safe-mode tests still fail" in result.diagnosis
    assert result.actions[0].action == "stop_escalation"
