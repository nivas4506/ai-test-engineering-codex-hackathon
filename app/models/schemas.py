from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repository_path: str
    upload_id: str | None = None


class GenerateTestsRequest(BaseModel):
    repository_path: str
    run_id: str | None = None
    model: str | None = None
    upload_id: str | None = None


class RunTestsRequest(BaseModel):
    repository_path: str
    run_id: str
    upload_id: str | None = None


class OrchestrateRequest(BaseModel):
    repository_path: str
    max_retries: int = Field(default=2, ge=0, le=5)
    model: str | None = None
    upload_id: str | None = None


class SignUpRequest(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1)


class AuthenticatedUser(BaseModel):
    id: int
    email: str
    full_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser


class FunctionCase(BaseModel):
    description: str
    arguments: list[str] = Field(default_factory=list)
    expected_expression: str


class ModuleFunction(BaseModel):
    name: str
    line_number: int
    arg_count: int
    required_arg_count: int
    parameter_names: list[str] = Field(default_factory=list)
    has_defaults: bool
    inferred_cases: list[FunctionCase] = Field(default_factory=list)


class DependencyLink(BaseModel):
    source_module: str
    target_module: str
    relation: str = "imports"


class ApiEndpoint(BaseModel):
    method: str
    path: str
    handler: str
    file_path: str
    line_number: int


class CodebaseSummary(BaseModel):
    total_files: int = 0
    total_modules: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_api_endpoints: int = 0
    detected_languages: list[str] = Field(default_factory=list)


class ModuleSummary(BaseModel):
    file_path: str
    module_import: str
    language: Literal["python", "javascript", "typescript", "generic"]
    functions: list[ModuleFunction] = Field(default_factory=list)
    class_names: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    repository_path: str
    python_files: list[str]
    javascript_files: list[str] = Field(default_factory=list)
    typescript_files: list[str] = Field(default_factory=list)
    generic_files: list[str] = Field(default_factory=list)
    detected_languages: list[Literal["python", "javascript", "typescript", "generic"]] = Field(default_factory=list)
    modules: list[ModuleSummary]
    dependency_map: list[DependencyLink] = Field(default_factory=list)
    api_endpoints: list[ApiEndpoint] = Field(default_factory=list)
    summary: CodebaseSummary = Field(default_factory=CodebaseSummary)
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
    provider: Literal["openai", "heuristic"]
    model: str | None = None
    summary: str


class SystemStatusResponse(BaseModel):
    ai_provider: Literal["openai", "heuristic"]
    ai_model: str | None = None
    openai_configured: bool
    reasoning_effort: str | None = None


class AvailableModel(BaseModel):
    id: str
    label: str
    provider: Literal["openai", "heuristic"]
    category: Literal["balanced", "budget", "coding", "fallback"]
    description: str
    available: bool = True
    recommended: bool = False


class GoogleAuthConfigResponse(BaseModel):
    enabled: bool
    client_id: str | None = None


class UserProfileStats(BaseModel):
    total_runs: int
    passed_runs: int
    runs_needing_attention: int
    latest_run_id: str | None = None
    latest_run_status: Literal["passed", "failed", "error"] | None = None


class UserProfileSummaryResponse(BaseModel):
    id: int
    email: str
    full_name: str
    member_since: datetime | None = None
    last_login_at: datetime | None = None
    stats: UserProfileStats


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


class BugFinding(BaseModel):
    title: str
    error_message: str
    root_cause: str
    file_path: str | None = None
    line_number: int | None = None
    severity: Literal["low", "medium", "high"] = "medium"


class FixSuggestion(BaseModel):
    title: str
    summary: str
    patch: str
    file_path: str | None = None
    line_number: int | None = None


class DebugResult(BaseModel):
    diagnosis: str
    actions: list[DebugAction]
    next_generation_mode: Literal["balanced", "safe"]
    findings: list[BugFinding] = Field(default_factory=list)
    fix_suggestions: list[FixSuggestion] = Field(default_factory=list)


class CoverageReport(BaseModel):
    estimated_line_coverage: int = 0
    covered_areas: list[str] = Field(default_factory=list)
    missing_edge_cases: list[str] = Field(default_factory=list)
    suggested_additional_tests: list[str] = Field(default_factory=list)


class ImprovementReport(BaseModel):
    rerun_summary: str = ""
    optimization_notes: list[str] = Field(default_factory=list)
    ci_cd_suggestions: list[str] = Field(default_factory=list)
    advanced_test_suggestions: list[str] = Field(default_factory=list)


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
    coverage_report: CoverageReport = Field(default_factory=CoverageReport)
    improvement_report: ImprovementReport = Field(default_factory=ImprovementReport)
    artifact_paths: dict[str, Any]


class RunListItem(BaseModel):
    run_id: str
    repository_path: str
    status: Literal["passed", "failed", "error"]
    iterations: int
    created_at: datetime
    latest_test_count: int | None = None


class UploadResponse(BaseModel):
    upload_id: str
    repository_path: str
    original_filename: str


class UpdateRunRequest(BaseModel):
    status: Literal["passed", "failed", "error"] | None = None
    notes: str | None = None
