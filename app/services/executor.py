from __future__ import annotations

import json
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
        command = self._build_command(Path(repository_path), generated_dir)
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
        except FileNotFoundError as exc:
            return ExecutionResult(
                status="error",
                exit_code=127,
                duration_seconds=time.perf_counter() - started_at,
                command=command,
                stdout="",
                stderr=str(exc),
                failing_tests=[],
                tests_collected=None,
            )

        status = "passed" if completed.returncode == 0 else "failed"
        combined_output = f"{completed.stdout}\n{completed.stderr}"
        return ExecutionResult(
            status=status,
            exit_code=completed.returncode,
            duration_seconds=duration,
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
            failing_tests=self._parse_failing_tests(combined_output),
            tests_collected=self._parse_collected_tests(combined_output),
        )

    def _build_command(self, repository_path: Path, generated_dir: Path) -> list[str]:
        python_tests = sorted(generated_dir.glob("*.py"))
        typescript_tests = sorted(generated_dir.glob("*.test.ts"))
        javascript_tests = sorted(generated_dir.glob("*.test.cjs")) + sorted(generated_dir.glob("*.test.js"))

        if python_tests:
            return [
                sys.executable,
                "-m",
                "pytest",
                str(generated_dir),
                "-q",
                "--maxfail=10",
            ]

        package_json = repository_path / "package.json"
        package = self._read_package_json(package_json)

        if typescript_tests:
            if self._has_package(package, "vitest"):
                return ["npx", "vitest", "run", str(generated_dir)]
            if self._has_package(package, "jest"):
                return ["npx", "jest", str(generated_dir), "--runInBand"]
            if self._has_package(package, "tsx"):
                return ["node", "--import", "tsx", "--test", *[str(path) for path in typescript_tests]]
            raise FileNotFoundError(
                "TypeScript test execution requires a project dependency such as tsx, vitest, or jest."
            )

        if javascript_tests:
            if self._has_package(package, "vitest"):
                return ["npx", "vitest", "run", str(generated_dir)]
            if self._has_package(package, "jest"):
                return ["npx", "jest", str(generated_dir), "--runInBand"]
            return ["node", "--test", *[str(path) for path in javascript_tests]]

        raise FileNotFoundError("No generated tests were found to execute.")

    def _read_package_json(self, package_json: Path) -> dict:
        if not package_json.exists():
            return {}
        try:
            return json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _has_package(self, package_json: dict, name: str) -> bool:
        dependencies = package_json.get("dependencies", {})
        dev_dependencies = package_json.get("devDependencies", {})
        return name in dependencies or name in dev_dependencies

    def _parse_failing_tests(self, text: str) -> list[FailingTest]:
        failing_tests = []
        patterns = [
            r"FAILED\s+([^\s]+)\s+-\s+(.+)",
            r"not ok\s+\d+\s+-\s+(.+)",
            r"●\s+(.+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                if pattern.startswith("FAILED"):
                    failing_tests.append(FailingTest(nodeid=match.group(1), message=match.group(2).strip()))
                else:
                    failing_tests.append(FailingTest(nodeid=match.group(1).strip(), message=match.group(0).strip()))
        return failing_tests

    def _parse_collected_tests(self, text: str) -> int | None:
        patterns = [
            r"(\d+)\s+passed",
            r"(\d+)\s+failed",
            r"# tests\s+(\d+)",
            r"tests\s+(\d+)",
            r"Tests:\s+(\d+)\s+passed",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))

        dot_progress = re.search(r"^([\.FsxE]+)\s+\[\s*\d+%\]$", text, re.MULTILINE)
        if dot_progress:
            return len(dot_progress.group(1))
        return None
