from __future__ import annotations

from app.models.schemas import DebugAction, DebugResult, ExecutionResult


class DebuggerService:
    def inspect(self, execution_result: ExecutionResult, current_mode: str) -> DebugResult:
        text = f"{execution_result.stdout}\n{execution_result.stderr}"
        actions = []
        diagnosis = "Generated tests failed for reasons that need a safer retry."
        next_mode = "safe"

        if "ModuleNotFoundError" in text:
            diagnosis = "Import path or module packaging issue detected during pytest execution."
            actions.append(
                DebugAction(
                    action="preserve_import_bootstrap",
                    detail="Retry with minimal tests while keeping repository path injection in conftest.py.",
                )
            )
        elif "TypeError" in text or "takes" in text:
            diagnosis = "A generated execution smoke test likely called a function with unsupported assumptions."
            actions.append(
                DebugAction(
                    action="disable_function_execution_tests",
                    detail="Retry in safe mode with import and existence tests only.",
                )
            )
        elif current_mode == "safe":
            diagnosis = "Safe-mode tests still fail, likely indicating source or environment issues."
            actions.append(
                DebugAction(
                    action="stop_escalation",
                    detail="Do not widen generated coverage because the current failure is probably not caused by aggressive test generation.",
                )
            )
            next_mode = "safe"
        else:
            actions.append(
                DebugAction(
                    action="fallback_to_safe_generation",
                    detail="Reduce test aggressiveness and retry once with import and existence checks only.",
                )
            )

        return DebugResult(
            diagnosis=diagnosis,
            actions=actions,
            next_generation_mode=next_mode,
        )
