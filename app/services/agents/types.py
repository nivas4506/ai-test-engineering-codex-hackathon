from __future__ import annotations

from dataclasses import dataclass, field

from app.models.schemas import (
    AgentTraceEntry,
    AnalysisResult,
    CoverageReport,
    DebugResult,
    ExecutionResult,
    ExecutionStep,
    FinalStructuredReport,
    GenerationResult,
    ImprovementReport,
    Observation,
    PlanResult,
    TestPlanItem,
)


@dataclass(slots=True)
class PlannerAgentOutput:
    analysis: AnalysisResult
    plan: PlanResult
    test_plan: list[TestPlanItem]
    execution_steps: list[ExecutionStep]
    trace: AgentTraceEntry


@dataclass(slots=True)
class ExecutorAgentOutput:
    generation: GenerationResult
    execution: ExecutionResult
    trace: AgentTraceEntry


@dataclass(slots=True)
class CriticAgentOutput:
    debug_result: DebugResult | None
    observations: list[Observation]
    final_structured_report: FinalStructuredReport
    trace: AgentTraceEntry


@dataclass(slots=True)
class MultiAgentRunOutput:
    planner_output: PlannerAgentOutput
    generation_history: list[GenerationResult]
    execution_history: list[ExecutionResult]
    debug_history: list[DebugResult]
    observations: list[Observation]
    final_structured_report: FinalStructuredReport
    coverage_report: CoverageReport
    improvement_report: ImprovementReport
    agent_trace: list[AgentTraceEntry] = field(default_factory=list)
