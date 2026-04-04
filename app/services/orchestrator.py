from __future__ import annotations

from pathlib import Path

from app.models.schemas import (
    AnalysisResult,
    DebugResult,
    ExecutionResult,
    GenerationResult,
    PlanResult,
    RunReport,
)
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

    def analyze(self, repository_path: str) -> AnalysisResult:
        return self.analyzer.analyze(repository_path)

    def plan(self, analysis: AnalysisResult) -> PlanResult:
        return self.planner.create_plan(analysis)

    def orchestrate(self, repository_path: str, max_retries: int) -> RunReport:
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
            generation = self.generator.generate(str(repo_path), run_dir, analysis, plan, mode=generation_mode)
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
            artifact_paths=artifact_paths,
        )
        report_path = write_json(run_dir / "artifacts" / "final_report.json", report.model_dump())
        report.artifact_paths["final_report"] = str(report_path)
        return report
