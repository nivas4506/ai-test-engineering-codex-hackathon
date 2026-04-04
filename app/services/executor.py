from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

from app.core.config import DEFAULT_TEST_TIMEOUT_SECONDS
from app.models.schemas import ExecutionResult, FailingTest


class PytestExecutor:
    def run(self, repository_path: str, run_dir: Path) -> ExecutionResult:
        generated_dir = run_dir / "generated_tests"
        command = [
            sys.executable,
            "-m",
            "pytest",
            str(generated_dir),
            "-q",
            "--maxfail=10",
        ]
        started_at = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TEST_TIMEOUT_SECONDS,
                check=False,
            )
            duration = time.perf_counter() - started_at
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                status="error",
                exit_code=124,
                duration_seconds=time.perf_counter() - started_at,
                command=command,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nTest execution timed out.",
                failing_tests=[],
                tests_collected=None,
            )

        status = "passed" if completed.returncode == 0 else "failed"
        return ExecutionResult(
            status=status,
            exit_code=completed.returncode,
            duration_seconds=duration,
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            failing_tests=self._parse_failing_tests(completed.stdout + "\n" + completed.stderr),
            tests_collected=self._parse_collected_tests(completed.stdout),
        )

    def _parse_failing_tests(self, text: str) -> list[FailingTest]:
        failing_tests = []
        for match in re.finditer(r"FAILED\s+([^\s]+)\s+-\s+(.+)", text):
            failing_tests.append(FailingTest(nodeid=match.group(1), message=match.group(2).strip()))
        return failing_tests

    def _parse_collected_tests(self, stdout: str) -> int | None:
        match = re.search(r"(\d+)\s+passed", stdout)
        if match:
            return int(match.group(1))
        failed_match = re.search(r"(\d+)\s+failed", stdout)
        if failed_match:
            return int(failed_match.group(1))
        return None
