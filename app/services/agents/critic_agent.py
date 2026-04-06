from __future__ import annotations

from app.models.schemas import AgentMemoryRecord, AgentTraceEntry, Observation
from app.services.debugger import DebuggerService
from app.services.agents.types import CriticAgentOutput


class CriticAgent:
    def __init__(self, debugger: DebuggerService | None = None) -> None:
        self.debugger = debugger or DebuggerService()

    def review(
        self,
        execution_result,
        generation_mode: str,
        memory_context: list[AgentMemoryRecord] | None = None,
        include_retry_guidance: bool = True,
    ) -> CriticAgentOutput:
        debug_result = None
        if execution_result.status != "passed":
            debug_result = self.debugger.inspect(execution_result, generation_mode)

        observations = [
            Observation(
                title="Execution status",
                detail=f"Runner returned {execution_result.status.upper()} with exit code {execution_result.exit_code}.",
                status="pass" if execution_result.status == "passed" else "fail",
            )
        ]
        if memory_context:
            observations.append(
                Observation(
                    title="Memory-informed review",
                    detail=f"Critic reviewed the run against {len(memory_context)} prior memory item(s).",
                    status="info",
                )
            )
        if debug_result:
            observations.append(
                Observation(
                    title="Critic diagnosis",
                    detail=debug_result.diagnosis,
                    status="info",
                )
            )

        tests_run = execution_result.tests_collected or 0
        final_report = {
            "tests_run": tests_run,
            "passed": tests_run if execution_result.status == "passed" else 0,
            "failed": tests_run if execution_result.status != "passed" else 0,
            "bugs": [],
        }
        if debug_result:
            final_report["bugs"] = [
                {
                    "issue": finding.title,
                    "severity": finding.severity,
                    "steps_to_reproduce": [
                        "Open the run workspace",
                        "Reuse the same repository input",
                        "Launch the tester agent",
                        f"Observe the error: {finding.error_message}",
                    ],
                }
                for finding in debug_result.findings[:5]
            ]

        trace_status = "completed" if execution_result.status == "passed" else ("completed" if include_retry_guidance else "failed")
        trace = AgentTraceEntry(
            agent="critic",
            status=trace_status,
            summary=debug_result.diagnosis if debug_result else "Execution matched the expected pass state.",
            details=[
                f"Observed {execution_result.tests_collected or 0} collected tests.",
                *(finding.title for finding in (debug_result.findings if debug_result else [])[:2]),
            ],
        )

        from app.models.schemas import FinalStructuredReport, FinalBugReport

        return CriticAgentOutput(
            debug_result=debug_result,
            observations=observations,
            final_structured_report=FinalStructuredReport(
                tests_run=final_report["tests_run"],
                passed=final_report["passed"],
                failed=final_report["failed"],
                bugs=[
                    FinalBugReport(
                        issue=item["issue"],
                        severity=item["severity"],
                        steps_to_reproduce=item["steps_to_reproduce"],
                    )
                    for item in final_report["bugs"]
                ],
            ),
            trace=trace,
        )
