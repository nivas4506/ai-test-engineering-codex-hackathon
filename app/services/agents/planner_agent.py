from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentMemoryRecord, AgentTraceEntry, ExecutionStep, TestPlanItem
from app.services.planner import PlannerService
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.agents.types import PlannerAgentOutput


class PlannerAgent:
    def __init__(
        self,
        analyzer: RepositoryAnalyzer | None = None,
        planner_service: PlannerService | None = None,
    ) -> None:
        self.analyzer = analyzer or RepositoryAnalyzer()
        self.planner_service = planner_service or PlannerService()

    def create_plan(
        self,
        repository_path: str,
        testing_objective: str | None = None,
        target_input: str | None = None,
        memory_context: list[AgentMemoryRecord] | None = None,
    ) -> PlannerAgentOutput:
        analysis = self.analyzer.analyze(repository_path)
        plan = self.planner_service.create_plan(analysis)
        test_plan = self._build_test_plan(analysis, plan, testing_objective, memory_context or [])
        execution_steps = self._build_execution_steps(repository_path, analysis, testing_objective, target_input)
        trace = AgentTraceEntry(
            agent="planner",
            status="completed",
            summary=f"Planned {len(test_plan)} scenario(s) across {len(plan.modules)} module(s).",
            details=[plan.summary, *(item.title for item in test_plan[:2])],
        )
        return PlannerAgentOutput(
            analysis=analysis,
            plan=plan,
            test_plan=test_plan,
            execution_steps=execution_steps,
            trace=trace,
        )

    def _build_test_plan(
        self,
        analysis,
        plan,
        testing_objective: str | None,
        memory_context: list[AgentMemoryRecord],
    ) -> list[TestPlanItem]:
        objective = testing_objective or "validate the application like a QA engineer"
        items: list[TestPlanItem] = []
        memory_focus = next((item.content for item in memory_context if item.type == "bug"), None)

        for planned_module in plan.modules[:6]:
            items.extend(
                [
                    TestPlanItem(
                        title=f"Positive flow for {planned_module.module_import}",
                        category="positive",
                        target=planned_module.module_import,
                        rationale=f"Confirm valid behavior while pursuing the objective: {objective}.",
                    ),
                    TestPlanItem(
                        title=f"Invalid input handling for {planned_module.module_import}",
                        category="negative",
                        target=planned_module.module_import,
                        rationale="Probe malformed, missing, or unsupported inputs without changing business logic.",
                    ),
                    TestPlanItem(
                        title=f"Boundary and empty-state behavior for {planned_module.module_import}",
                        category="boundary",
                        target=planned_module.module_import,
                        rationale="Exercise empty, minimum, and maximum-like conditions for the module surface.",
                    ),
                ]
            )

        if analysis.api_endpoints:
            for endpoint in analysis.api_endpoints[:3]:
                items.append(
                    TestPlanItem(
                        title=f"Security probe for {endpoint.method} {endpoint.path}",
                        category="security",
                        target=f"{endpoint.method} {endpoint.path}",
                        rationale="Check malformed payloads and input validation around exposed API handlers.",
                    )
                )

        if memory_focus:
            items.append(
                TestPlanItem(
                    title="Regression guard from memory",
                    category="edge",
                    target=Path(analysis.repository_path).name,
                    rationale=f"Revisit a previously observed issue: {memory_focus}",
                )
            )

        if not items:
            items.append(
                TestPlanItem(
                    title="Generic smoke validation",
                    category="edge",
                    target=analysis.repository_path,
                    rationale=f"Use smoke validation to support the objective: {objective}.",
                )
            )

        return items

    def _build_execution_steps(
        self,
        repository_path: str,
        analysis,
        testing_objective: str | None,
        target_input: str | None,
    ) -> list[ExecutionStep]:
        objective = testing_objective or "run exploratory QA coverage"
        steps: list[ExecutionStep] = []
        target_value = target_input or repository_path

        if target_input and target_input.startswith(("http://", "https://")):
            steps.append(ExecutionStep(action="open_url", value=target_input))
        elif target_input and " " in target_input and target_input.split(" ", 1)[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            steps.append(ExecutionStep(action="open_api", value=target_input))
        else:
            steps.append(ExecutionStep(action="open_repository", value=repository_path))

        steps.extend(
            [
                ExecutionStep(action="analyze", value=f"{len(analysis.modules)} modules detected"),
                ExecutionStep(action="plan_tests", value=objective),
                ExecutionStep(action="generate_tests", value="unit, integration, edge, boundary, security"),
                ExecutionStep(action="execute", value="pytest", expected="real pass/fail results"),
                ExecutionStep(action="assert", expected=f"Primary target remains stable: {target_value}"),
            ]
        )
        return steps
