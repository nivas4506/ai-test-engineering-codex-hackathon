from __future__ import annotations

import re

from app.models.schemas import BugFinding, DebugAction, DebugResult, ExecutionResult, FixSuggestion


class DebuggerService:
    def inspect(self, execution_result: ExecutionResult, current_mode: str) -> DebugResult:
        text = f"{execution_result.stdout}\n{execution_result.stderr}"
        actions = []
        diagnosis = "Generated tests failed for reasons that need a safer retry."
        next_mode = "safe"
        findings: list[BugFinding] = []
        fix_suggestions: list[FixSuggestion] = []

        if "ModuleNotFoundError" in text:
            diagnosis = "Import path or module packaging issue detected during pytest execution."
            actions.append(
                DebugAction(
                    action="preserve_import_bootstrap",
                    detail="Retry with minimal tests while keeping repository path injection in conftest.py.",
                )
            )
            findings.append(
                self._build_finding(
                    title="Import path issue",
                    error_message=self._first_error_line(text, "ModuleNotFoundError"),
                    root_cause="Generated tests could not import the target module because the runtime path or package layout was not resolved correctly.",
                    severity="high",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
                )
            )
            fix_suggestions.append(
                FixSuggestion(
                    title="Stabilize import bootstrap",
                    summary="Keep repository root injection and avoid path-sensitive execution tests until imports succeed.",
                    patch="@@ conftest.py\n-if str(REPO_ROOT) not in sys.path:\n-    sys.path.insert(0, str(REPO_ROOT))\n+if str(REPO_ROOT) not in sys.path:\n+    sys.path.insert(0, str(REPO_ROOT))\n",
                    file_path="generated_tests/conftest.py",
                    line_number=1,
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
            findings.append(
                self._build_finding(
                    title="Overeager invocation",
                    error_message=self._first_error_line(text, "TypeError"),
                    root_cause="A generated test called a function with the wrong argument shape or unsupported assumptions.",
                    severity="medium",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
                )
            )
            fix_suggestions.append(
                FixSuggestion(
                    title="Reduce execution aggressiveness",
                    summary="Keep callable existence checks and remove direct invocation tests for uncertain functions.",
                    patch="@@ generated test\n-    function()\n+    assert callable(function)\n",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
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
            findings.append(
                self._build_finding(
                    title="Safe-mode failure",
                    error_message=self._first_error_line(text),
                    root_cause="Minimal smoke tests still failed, which usually means the source, environment, or imports are genuinely broken.",
                    severity="high" if execution_result.status == "error" else "medium",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
                )
            )
            fix_suggestions.append(
                FixSuggestion(
                    title="Inspect source or environment",
                    summary="At this point the issue is likely in the project or runtime rather than in aggressive generated tests.",
                    patch="@@ next steps\n- Review runtime dependencies and source imports\n- Re-run the minimal smoke test after fixing the environment\n",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
                )
            )
        else:
            actions.append(
                DebugAction(
                    action="fallback_to_safe_generation",
                    detail="Reduce test aggressiveness and retry once with import and existence checks only.",
                )
            )
            findings.extend(
                [
                    self._build_finding(
                        title=failing.nodeid or "Assertion failure",
                        error_message=failing.message,
                        root_cause="A generated or source-facing test assertion failed during execution.",
                        severity="medium",
                    )
                    for failing in execution_result.failing_tests[:3]
                ]
            )
            fix_suggestions.append(
                FixSuggestion(
                    title="Retry with safer tests",
                    summary="Remove aggressive execution checks and keep import, existence, and smoke coverage first.",
                    patch="@@ generation mode\n-balanced\n+safe\n",
                    file_path="generated_tests",
                    line_number=1,
                )
            )

        if not findings:
            findings.append(
                self._build_finding(
                    title="Execution failure",
                    error_message=self._first_error_line(text),
                    root_cause="The current run failed during test execution and needs either safer generation or a source/environment fix.",
                    severity="medium",
                    file_path=self._extract_file_path(text),
                    line_number=self._extract_line_number(text),
                )
            )

        return DebugResult(
            diagnosis=diagnosis,
            actions=actions,
            next_generation_mode=next_mode,
            findings=findings,
            fix_suggestions=fix_suggestions,
        )

    def _extract_file_path(self, text: str) -> str | None:
        match = re.search(r'File "([^"]+)"', text)
        if match:
            return match.group(1)
        return None

    def _extract_line_number(self, text: str) -> int | None:
        match = re.search(r'line (\d+)', text)
        if match:
            return int(match.group(1))
        return None

    def _first_error_line(self, text: str, preferred: str | None = None) -> str:
        for line in text.splitlines():
            if preferred and preferred in line:
                return line.strip()
        for line in text.splitlines():
            if line.strip():
                return line.strip()
        return "No detailed error output was captured."

    def _build_finding(
        self,
        title: str,
        error_message: str,
        root_cause: str,
        severity: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> BugFinding:
        return BugFinding(
            title=title,
            error_message=error_message,
            root_cause=root_cause,
            file_path=file_path,
            line_number=line_number,
            severity=severity,
        )
