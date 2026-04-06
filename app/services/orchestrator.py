from __future__ import annotations

from pathlib import Path

from app.models.schemas import (
    AnalysisResult,
    CoverageReport,
    DebugResult,
    ExecutionResult,
    GenerationResult,
    ImprovementReport,
    PlanResult,
    RunReport,
)
from app.db.repository import RunRepository
from app.services.debugger import DebuggerService
from app.services.executor import PytestExecutor
from app.services.planner import PlannerService
from app.services.repository_analyzer import RepositoryAnalyzer
from app.services.test_generator import TestGeneratorService
from app.utils.files import create_run_directory, snapshot_repository_metadata, write_json


class OrchestratorService:
    def __init__(self) -> None:
        self.analyzer = RepositoryAnalyzer()
        self.planner = PlannerService()
        self.generator = TestGeneratorService()
        self.executor = PytestExecutor()
        self.debugger = DebuggerService()
        self.run_repository = RunRepository()

    def analyze(self, repository_path: str) -> AnalysisResult:
        return self.analyzer.analyze(repository_path)

    def plan(self, analysis: AnalysisResult) -> PlanResult:
        return self.planner.create_plan(analysis)

    def orchestrate(
        self,
        repository_path: str,
        max_retries: int,
        user_id: int | None = None,
        model: str | None = None,
    ) -> RunReport:
        run_id, run_dir = create_run_directory()
        repo_path = Path(repository_path).resolve()
        snapshot_repository_metadata(repo_path, run_dir)

        analysis = self.analyze(str(repo_path))
        plan = self.plan(analysis)
        generation_history: list[GenerationResult] = []
        execution_history: list[ExecutionResult] = []
        debug_history: list[DebugResult] = []

        generation_mode = "balanced"
        final_status = "failed"

        for attempt in range(max_retries + 1):
            generation = self.generator.generate(str(repo_path), run_dir, analysis, plan, mode=generation_mode, model=model)
            generation_history.append(generation)
            execution = self.executor.run(str(repo_path), run_dir)
            execution_history.append(execution)

            if execution.status == "passed":
                final_status = "passed"
                break

            if execution.status == "error":
                final_status = "error"

            if attempt == max_retries:
                break

            debug_result = self.debugger.inspect(execution, generation_mode)
            debug_history.append(debug_result)
            generation_mode = debug_result.next_generation_mode

        artifact_paths = {
            "run_dir": str(run_dir),
            "analysis": str(write_json(run_dir / "artifacts" / "analysis.json", analysis.model_dump())),
            "plan": str(write_json(run_dir / "artifacts" / "plan.json", plan.model_dump())),
            "generation_history": str(
                write_json(run_dir / "artifacts" / "generation_history.json", [item.model_dump() for item in generation_history])
            ),
            "execution_history": str(
                write_json(run_dir / "artifacts" / "execution_history.json", [item.model_dump() for item in execution_history])
            ),
            "debug_history": str(
                write_json(run_dir / "artifacts" / "debug_history.json", [item.model_dump() for item in debug_history])
            ),
        }
        coverage_report = self._estimate_coverage(analysis, generation_history, execution_history)
        artifact_paths["coverage_report"] = str(
            write_json(run_dir / "artifacts" / "coverage_report.json", coverage_report.model_dump())
        )
        improvement_report = self._build_improvement_report(analysis, execution_history, debug_history)
        artifact_paths["improvement_report"] = str(
            write_json(run_dir / "artifacts" / "improvement_report.json", improvement_report.model_dump())
        )

        report = RunReport(
            run_id=run_id,
            repository_path=str(repo_path),
            status=final_status,
            iterations=len(execution_history),
            analysis=analysis,
            plan=plan,
            generation_history=generation_history,
            execution_history=execution_history,
            debug_history=debug_history,
            coverage_report=coverage_report,
            improvement_report=improvement_report,
            artifact_paths=artifact_paths,
        )
        report_path = write_json(run_dir / "artifacts" / "final_report.json", report.model_dump())
        report.artifact_paths["final_report"] = str(report_path)
        self.run_repository.upsert_run_report(report, max_retries=max_retries, user_id=user_id)
        return report

    def _estimate_coverage(
        self,
        analysis: AnalysisResult,
        generation_history: list[GenerationResult],
        execution_history: list[ExecutionResult],
    ) -> CoverageReport:
        total_modules = max(len(analysis.modules), 1)
        total_functions = sum(len(module.functions) for module in analysis.modules)
        latest_generation = generation_history[-1] if generation_history else None
        latest_execution = execution_history[-1] if execution_history else None

        generated_module_tests = 0
        if latest_generation:
            generated_module_tests = sum(
                1 for file in latest_generation.generated_files if Path(file.file_path).name != "conftest.py"
            )

        module_ratio = min(generated_module_tests / total_modules, 1.0)
        function_ratio = 1.0 if total_functions == 0 else min(
            sum(1 for module in analysis.modules if module.functions) / total_modules,
            1.0,
        )
        execution_bonus = 0.15 if latest_execution and latest_execution.status == "passed" else 0.05
        estimated_line_coverage = int(min(0.25 + (module_ratio * 0.4) + (function_ratio * 0.2) + execution_bonus, 0.95) * 100)

        covered_areas = [
            f"{generated_module_tests} generated test modules across {total_modules} analyzed modules",
            f"{len(analysis.api_endpoints)} API endpoints detected and available for integration coverage",
            f"{len(analysis.dependency_map)} internal dependency links mapped for module interaction checks",
        ]
        if latest_execution:
            covered_areas.append(
                f"Latest execution status: {latest_execution.status.upper()} with {latest_execution.tests_collected or 0} collected tests"
            )

        missing_edge_cases: list[str] = []
        if any(module.language == "generic" for module in analysis.modules):
            missing_edge_cases.append("Generic-language projects currently receive smoke coverage rather than framework-native assertions.")
        if analysis.api_endpoints:
            missing_edge_cases.append("API endpoints should gain request validation, auth, and error-path assertions.")
        if any(not module.functions for module in analysis.modules):
            missing_edge_cases.append("Some modules expose no detectable public functions and rely on smoke coverage only.")
        if not missing_edge_cases:
            missing_edge_cases.append("Add more invalid-input and boundary assertions for public functions.")

        suggested_additional_tests = [
            "Add boundary-value tests for every public function with required arguments.",
            "Add negative-input coverage for invalid payloads, missing fields, and empty values.",
        ]
        if analysis.api_endpoints:
            suggested_additional_tests.append("Add API integration tests for every discovered endpoint, including auth and error responses.")
        if analysis.dependency_map:
            suggested_additional_tests.append("Add module interaction tests around the busiest dependency links in the codebase.")

        return CoverageReport(
            estimated_line_coverage=estimated_line_coverage,
            covered_areas=covered_areas,
            missing_edge_cases=missing_edge_cases,
            suggested_additional_tests=suggested_additional_tests,
        )

    def _build_improvement_report(
        self,
        analysis: AnalysisResult,
        execution_history: list[ExecutionResult],
        debug_history: list[DebugResult],
    ) -> ImprovementReport:
        latest_execution = execution_history[-1] if execution_history else None
        latest_debug = debug_history[-1] if debug_history else None

        if latest_execution is None:
            rerun_summary = "No execution history is available yet."
        elif latest_execution.status == "passed":
            rerun_summary = f"Tests were re-run successfully after {len(execution_history)} execution cycle(s)."
        elif debug_history:
            rerun_summary = (
                f"Agent completed {len(execution_history)} execution cycle(s) and ended with "
                f"{latest_execution.status.upper()} after applying safer retry logic."
            )
        else:
            rerun_summary = f"Single execution ended with {latest_execution.status.upper()} and no retry was applied."

        optimization_notes = [
            "Prioritize deterministic assertions over broad smoke tests for modules with clearly inferred behavior.",
            "Keep retry depth low for unstable environments and widen only after import stability is proven.",
        ]
        if latest_debug:
            optimization_notes.append(f"Latest retry insight: {latest_debug.diagnosis}")
        if analysis.dependency_map:
            optimization_notes.append(
                f"Focus deeper integration coverage on the {len(analysis.dependency_map)} detected dependency links."
            )

        ci_cd_suggestions = [
            "Run pytest on every pull request and publish the generated test report as a CI artifact.",
            "Use GitHub Actions to run unit, integration, and smoke checks separately for faster failure isolation.",
        ]
        if analysis.api_endpoints:
            ci_cd_suggestions.append("Add API contract checks to CI so endpoint changes fail fast before deployment.")

        advanced_test_suggestions = []
        if analysis.api_endpoints:
            advanced_test_suggestions.append("Add authenticated API negative tests for missing headers, invalid payloads, and error responses.")
            advanced_test_suggestions.append("Add light performance checks around the busiest API endpoints.")
        advanced_test_suggestions.append("Add security-oriented input validation tests for malformed, empty, and boundary-case inputs.")
        if any(language in {"javascript", "typescript"} for language in analysis.detected_languages):
            advanced_test_suggestions.append("Add browser or UI flow checks for JavaScript/TypeScript-driven user journeys.")

        return ImprovementReport(
            rerun_summary=rerun_summary,
            optimization_notes=optimization_notes,
            ci_cd_suggestions=ci_cd_suggestions,
            advanced_test_suggestions=advanced_test_suggestions,
        )
