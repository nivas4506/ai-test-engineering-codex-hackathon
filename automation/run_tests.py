from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "automation" / "reports"
JUNIT_PATH = REPORTS_DIR / "junit.xml"
COVERAGE_XML_PATH = REPORTS_DIR / "coverage.xml"
SUMMARY_JSON_PATH = REPORTS_DIR / "summary.json"
SUMMARY_MD_PATH = REPORTS_DIR / "summary.md"


def ensure_reports_dir() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def build_pytest_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "--junitxml",
        str(JUNIT_PATH),
        "--cov=app",
        f"--cov-report=xml:{COVERAGE_XML_PATH}",
        "--cov-report=term-missing",
        "--cov-report=html:automation/reports/htmlcov",
    ]


def parse_junit_report() -> dict[str, int]:
    if not JUNIT_PATH.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    root = ElementTree.parse(JUNIT_PATH).getroot()
    testsuite = root if root.tag == "testsuite" else root.find("testsuite")
    if testsuite is None:
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    return {
        "tests": int(testsuite.attrib.get("tests", 0)),
        "failures": int(testsuite.attrib.get("failures", 0)),
        "errors": int(testsuite.attrib.get("errors", 0)),
        "skipped": int(testsuite.attrib.get("skipped", 0)),
    }


def parse_coverage_report() -> dict[str, float]:
    if not COVERAGE_XML_PATH.exists():
        return {"line_rate": 0.0, "line_percent": 0.0}

    root = ElementTree.parse(COVERAGE_XML_PATH).getroot()
    line_rate = float(root.attrib.get("line-rate", 0.0))
    return {"line_rate": line_rate, "line_percent": round(line_rate * 100, 2)}


def collect_detected_issues(junit_stats: dict[str, int], stdout: str, stderr: str) -> list[str]:
    issues: list[str] = []
    if junit_stats["failures"] > 0:
        issues.append(f"{junit_stats['failures']} failing test(s) detected.")
    if junit_stats["errors"] > 0:
        issues.append(f"{junit_stats['errors']} test error(s) detected.")
    if "DeprecationWarning" in stdout or "DeprecationWarning" in stderr:
        issues.append("Deprecation warnings detected during test execution.")
    if not issues:
        issues.append("No blocking issues detected in the current automated run.")
    return issues


def write_summary(result: subprocess.CompletedProcess[str], junit_stats: dict[str, int], coverage: dict[str, float]) -> None:
    detected_issues = collect_detected_issues(junit_stats, result.stdout, result.stderr)
    payload = {
        "status": "passed" if result.returncode == 0 else "failed",
        "command": result.args,
        "exit_code": result.returncode,
        "junit": junit_stats,
        "coverage": coverage,
        "detected_issues": detected_issues,
    }
    SUMMARY_JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    markdown = "\n".join(
        [
            "# Test Report",
            "",
            f"- Status: **{payload['status'].upper()}**",
            f"- Exit code: `{payload['exit_code']}`",
            f"- Tests: `{junit_stats['tests']}`",
            f"- Failures: `{junit_stats['failures']}`",
            f"- Errors: `{junit_stats['errors']}`",
            f"- Skipped: `{junit_stats['skipped']}`",
            f"- Coverage: `{coverage['line_percent']}%`",
            "",
            "## Detected Issues",
            *[f"- {issue}" for issue in detected_issues],
            "",
            "## Coverage Suggestions",
            "- Add more edge-case assertions around upload recovery and unsupported language handling.",
            "- Add route-level regression tests for report views after authenticated upload-based runs.",
            "- Add JavaScript and TypeScript fixture repos to increase cross-language execution coverage.",
        ]
    )
    SUMMARY_MD_PATH.write_text(markdown, encoding="utf-8")


def main() -> int:
    ensure_reports_dir()

    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./workspace/test-automation.db")

    command = build_pytest_command()
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)

    junit_stats = parse_junit_report()
    coverage = parse_coverage_report()
    write_summary(result, junit_stats, coverage)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
