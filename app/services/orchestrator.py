from __future__ import annotations

from pathlib import Path

from app.db.repository import RunRepository
from app.models.schemas import CoverageReport, ImprovementReport, RunReport
from app.services.agents.controller import MultiAgentController
from app.services.planner import PlannerService
from app.services.repository_analyzer import RepositoryAnalyzer
from app.utils.files import create_run_directory, snapshot_repository_metadata, write_json


class OrchestratorService:
    def __init__(self) -> None:
        self.analyzer = RepositoryAnalyzer()
        self.planner = PlannerService()
        self.controller = MultiAgentController()
        self.generator = self.controller.executor_agent.generator
        self.executor = self.controller.executor_agent.executor
        self.debugger = self.controller.critic_agent.debugger
        self.run_repository = RunRepository()

    def analyze(self, repository_path: str):
        return self.analyzer.analyze(repository_path)

    def plan(self, analysis):
        return self.planner.create_plan(analysis)

    def orchestrate(
        self,
        repository_path: str,
        max_retries: int,
        user_id: int | None = None,
        model: str | None = None,
        target_input: str | None = None,
        testing_objective: str | None = None,
    ) -> RunReport:
        run_id, run_dir = create_run_directory()
        repo_path = Path(repository_path).resolve()
        snapshot_repository_metadata(repo_path, run_dir)

        multi_agent_output = self.controller.run(
            repository_path=str(repo_path),
            run_dir=run_dir,
            max_retries=max_retries,
            model=model,
            user_id=user_id,
            target_input=target_input,
            testing_objective=testing_objective,
            coverage_builder=self._estimate_coverage,
            improvement_builder=self._build_improvement_report,
        )

        analysis = multi_agent_output.planner_output.analysis
        plan = multi_agent_output.planner_output.plan
        generation_history = multi_agent_output.generation_history
        execution_history = multi_agent_output.execution_history
        debug_history = multi_agent_output.debug_history
        coverage_report = multi_agent_output.coverage_report
        improvement_report = multi_agent_output.improvement_report
        observations = multi_agent_output.observations
        final_structured_report = multi_agent_output.final_structured_report
        memory_context, memory_trace = self.controller.memory_manager.retrieve_context(str(repo_path), user_id=user_id)
        agent_trace = [
            memory_trace if not any(trace.agent == "memory" for trace in multi_agent_output.agent_trace) else None,
            *multi_agent_output.agent_trace,
        ]
        agent_trace = [trace for trace in agent_trace if trace is not None]

        latest_execution = execution_history[-1] if execution_history else None
        if latest_execution is None:
            final_status = "error"
        elif latest_execution.status == "passed":
            final_status = "passed"
        elif latest_execution.status == "error":
            final_status = "error"
        else:
            final_status = "failed"

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
            "memory_context": str(
                write_json(run_dir / "artifacts" / "memory_context.json", [item.model_dump() for item in memory_context])
            ),
            "agent_trace": str(
                write_json(run_dir / "artifacts" / "agent_trace.json", [item.model_dump() for item in agent_trace])
            ),
            "test_plan": str(
                write_json(run_dir / "artifacts" / "test_plan.json", [item.model_dump() for item in multi_agent_output.planner_output.test_plan])
            ),
            "execution_steps": str(
                write_json(run_dir / "artifacts" / "execution_steps.json", [item.model_dump() for item in multi_agent_output.planner_output.execution_steps])
            ),
            "observations": str(
                write_json(run_dir / "artifacts" / "observations.json", [item.model_dump() for item in observations])
            ),
            "coverage_report": str(
                write_json(run_dir / "artifacts" / "coverage_report.json", coverage_report.model_dump())
            ),
            "improvement_report": str(
                write_json(run_dir / "artifacts" / "improvement_report.json", improvement_report.model_dump())
            ),
            "final_structured_report": str(
                write_json(run_dir / "artifacts" / "final_structured_report.json", final_structured_report.model_dump())
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
            coverage_report=coverage_report,
            improvement_report=improvement_report,
            target_input=target_input,
            testing_objective=testing_objective,
            memory_context=memory_context,
            agent_trace=agent_trace,
            test_plan=multi_agent_output.planner_output.test_plan,
            execution_steps=multi_agent_output.planner_output.execution_steps,
            observations=observations,
            final_structured_report=final_structured_report,
            artifact_paths=artifact_paths,
        )
        report_path = write_json(run_dir / "artifacts" / "final_report.json", report.model_dump())
        report.artifact_paths["final_report"] = str(report_path)
        self.run_repository.upsert_run_report(report, max_retries=max_retries, user_id=user_id)
        return report

    def _estimate_coverage(self, analysis, generation_history, execution_history) -> CoverageReport:
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

    def _build_improvement_report(self, analysis, execution_history, debug_history) -> ImprovementReport:
        latest_execution = execution_history[-1] if execution_history else None
        latest_debug = debug_history[-1] if debug_history else None

        if latest_execution is None:
            rerun_summary = "No execution history is available yet."
        elif latest_execution.status == "passed":
            rerun_summary = f"Tests were re-run successfully after {len(execution_history)} execution cycle(s)."
        elif debug_history:
            rerun_summary = (
                f"Multi-agent loop completed {len(execution_history)} execution cycle(s) and ended with "
                f"{latest_execution.status.upper()} after critic-guided retries."
            )
        else:
            rerun_summary = f"Single execution ended with {latest_execution.status.upper()} and no retry was applied."

        optimization_notes = [
            "Planner agent should prioritize deterministic assertions over broad smoke tests where behavior is clearly inferred.",
            "Executor agent should keep retry depth low for unstable environments and widen only after import stability is proven.",
        ]
        if latest_debug:
            optimization_notes.append(f"Latest critic insight: {latest_debug.diagnosis}")
        if analysis.dependency_map:
            optimization_notes.append(
                f"Focus deeper integration coverage on the {len(analysis.dependency_map)} detected dependency links."
            )

        ci_cd_suggestions = [
            "Run the multi-agent pytest workflow on every pull request and publish the generated report as a CI artifact.",
            "Use separate CI jobs for planner, execution smoke tests, and regression coverage for faster failure isolation.",
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
