from __future__ import annotations

from pathlib import Path

from app.models.schemas import AgentTraceEntry, CoverageReport, ImprovementReport
from app.services.agents.critic_agent import CriticAgent
from app.services.agents.executor_agent import ExecutorAgent
from app.services.agents.memory_manager import MemoryManager
from app.services.agents.planner_agent import PlannerAgent
from app.services.agents.types import MultiAgentRunOutput


class MultiAgentController:
    def __init__(
        self,
        planner_agent: PlannerAgent | None = None,
        executor_agent: ExecutorAgent | None = None,
        critic_agent: CriticAgent | None = None,
        memory_manager: MemoryManager | None = None,
    ) -> None:
        self.planner_agent = planner_agent or PlannerAgent()
        self.executor_agent = executor_agent or ExecutorAgent()
        self.critic_agent = critic_agent or CriticAgent()
        self.memory_manager = memory_manager or MemoryManager()

    def run(
        self,
        repository_path: str,
        run_dir: Path,
        max_retries: int,
        model: str | None = None,
        user_id: int | None = None,
        target_input: str | None = None,
        testing_objective: str | None = None,
        coverage_builder=None,
        improvement_builder=None,
    ) -> MultiAgentRunOutput:
        memory_context, memory_trace = self.memory_manager.retrieve_context(repository_path, user_id=user_id)
        planner_output = self.planner_agent.create_plan(
            repository_path=repository_path,
            testing_objective=testing_objective,
            target_input=target_input,
            memory_context=memory_context,
        )

        traces: list[AgentTraceEntry] = [
            AgentTraceEntry(
                agent="controller",
                status="ready",
                summary="Controller started the multi-agent testing loop.",
                details=[f"Max retries: {max_retries}", f"Model: {model or 'heuristic'}"],
            ),
            memory_trace,
            planner_output.trace,
        ]

        generation_history = []
        execution_history = []
        debug_history = []
        observations = []
        generation_mode = "balanced"
        final_critic = None

        for attempt in range(max_retries + 1):
            executor_output = self.executor_agent.execute(
                repository_path=repository_path,
                run_dir=run_dir,
                analysis=planner_output.analysis,
                plan=planner_output.plan,
                mode=generation_mode,
                model=model,
            )
            generation_history.append(executor_output.generation)
            execution_history.append(executor_output.execution)
            traces.append(executor_output.trace)

            critic_output = self.critic_agent.review(
                execution_result=executor_output.execution,
                generation_mode=generation_mode,
                memory_context=memory_context,
                include_retry_guidance=attempt < max_retries,
            )
            observations.extend(critic_output.observations)
            traces.append(critic_output.trace)
            final_critic = critic_output

            if executor_output.execution.status == "passed":
                break

            if critic_output.debug_result is None:
                break

            if attempt == max_retries:
                break

            debug_history.append(critic_output.debug_result)
            generation_mode = critic_output.debug_result.next_generation_mode

        if final_critic and final_critic.debug_result and (not debug_history or debug_history[-1] is not final_critic.debug_result):
            if execution_history and execution_history[-1].status != "passed":
                debug_history.append(final_critic.debug_result)

        coverage_report = coverage_builder(planner_output.analysis, generation_history, execution_history) if coverage_builder else CoverageReport()
        improvement_report = improvement_builder(planner_output.analysis, execution_history, debug_history) if improvement_builder else ImprovementReport()

        traces.append(
            AgentTraceEntry(
                agent="controller",
                status="completed",
                summary=f"Controller finished after {len(execution_history)} execution cycle(s).",
                details=[f"Final status: {execution_history[-1].status.upper() if execution_history else 'UNKNOWN'}"],
            )
        )

        return MultiAgentRunOutput(
            planner_output=planner_output,
            generation_history=generation_history,
            execution_history=execution_history,
            debug_history=debug_history,
            observations=observations,
            final_structured_report=final_critic.final_structured_report if final_critic else None,
            coverage_report=coverage_report,
            improvement_report=improvement_report,
            agent_trace=traces,
        )
