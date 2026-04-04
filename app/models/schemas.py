from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repository_path: str


class GenerateTestsRequest(BaseModel):
    repository_path: str
    run_id: str | None = None


class RunTestsRequest(BaseModel):
    repository_path: str
    run_id: str


class OrchestrateRequest(BaseModel):
    repository_path: str
    max_retries: int = Field(default=2, ge=0, le=5)


class ModuleFunction(BaseModel):
    name: str
    line_number: int
    arg_count: int
    has_defaults: bool


class ModuleSummary(BaseModel):
    file_path: str
    module_import: str
    functions: list[ModuleFunction] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    repository_path: str
    python_files: list[str]
    modules: list[ModuleSummary]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlannedModule(BaseModel):
    module_import: str
    file_path: str
    priority: Literal["high", "medium", "low"]
    strategy: list[str]
    rationale: str


class PlanResult(BaseModel):
    modules: list[PlannedModule]
    summary: str


class GeneratedFile(BaseModel):
    file_path: str
    strategy: str


class GenerationResult(BaseModel):
    generated_files: list[GeneratedFile]
    mode: Literal["balanced", "safe"]
    summary: str


class FailingTest(BaseModel):
    nodeid: str
    message: str


class ExecutionResult(BaseModel):
    status: Literal["passed", "failed", "error"]
    exit_code: int
    duration_seconds: float
    command: list[str]
    stdout: str
    stderr: str
    failing_tests: list[FailingTest] = Field(default_factory=list)
    tests_collected: int | None = None


class DebugAction(BaseModel):
    action: str
    detail: str


class DebugResult(BaseModel):
    diagnosis: str
    actions: list[DebugAction]
    next_generation_mode: Literal["balanced", "safe"]


class RunReport(BaseModel):
    run_id: str
    repository_path: str
    status: Literal["passed", "failed", "error"]
    iterations: int
    analysis: AnalysisResult
    plan: PlanResult
    generation_history: list[GenerationResult]
    execution_history: list[ExecutionResult]
    debug_history: list[DebugResult]
    artifact_paths: dict[str, Any]
