from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentTraceEntry
from app.services.executor import PytestExecutor
from app.services.test_generator import TestGeneratorService
from app.services.agents.types import ExecutorAgentOutput


class ExecutorAgent:
    def __init__(
        self,
        generator: TestGeneratorService | None = None,
        executor: PytestExecutor | None = None,
    ) -> None:
        self.generator = generator or TestGeneratorService()
        self.executor = executor or PytestExecutor()

    def execute(
        self,
        repository_path: str,
        run_dir: Path,
        analysis,
        plan,
        mode: str,
        model: str | None = None,
    ) -> ExecutorAgentOutput:
        generation = self.generator.generate(repository_path, run_dir, analysis, plan, mode=mode, model=model)
        execution = self.executor.run(repository_path, run_dir)
        toolbox = ["pytest"]
        if any(language in {"javascript", "typescript"} for language in analysis.detected_languages):
            toolbox.append("node-compatible runner selection")

        trace = AgentTraceEntry(
            agent="executor",
            status="completed" if execution.status == "passed" else "failed",
            summary=f"Generated {len(generation.generated_files)} file(s) and executed tests with status {execution.status.upper()}.",
            details=[
                generation.summary,
                f"Exit code {execution.exit_code}",
                f"Toolbox: {', '.join(toolbox)}",
            ],
        )
        return ExecutorAgentOutput(
            generation=generation,
            execution=execution,
            trace=trace,
        )
