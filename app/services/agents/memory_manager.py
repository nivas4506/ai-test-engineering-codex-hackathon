from __future__ import annotations

from pathlib import Path

from app.db.repository import RunRepository
from app.models.schemas import AgentMemoryRecord, AgentTraceEntry, RunReport


class MemoryManager:
    def __init__(self, run_repository: RunRepository | None = None) -> None:
        self.run_repository = run_repository or RunRepository()

    def retrieve_context(self, repository_path: str, user_id: int | None = None, limit: int = 5) -> tuple[list[AgentMemoryRecord], AgentTraceEntry]:
        runs = self.run_repository.list_runs(limit=limit, user_id=user_id)
        current_name = Path(repository_path).name.lower()
        memory: list[AgentMemoryRecord] = []

        for run in runs:
            report = self.run_repository.get_run_report(run.run_id, user_id=user_id)
            if report is None:
                continue
            memory.extend(self._report_to_memory(report, current_name))
            if len(memory) >= limit:
                break

        memory = sorted(memory, key=lambda item: item.relevance_score, reverse=True)[:limit]
        trace = AgentTraceEntry(
            agent="memory",
            status="completed",
            summary=f"Retrieved {len(memory)} memory item(s) for repository context.",
            details=[item.content for item in memory[:3]],
        )
        return memory, trace

    def _report_to_memory(self, report: RunReport, current_name: str) -> list[AgentMemoryRecord]:
        relevance_base = 0.45
        if Path(report.repository_path).name.lower() == current_name:
            relevance_base += 0.35
        if report.status != "passed":
            relevance_base += 0.1

        items: list[AgentMemoryRecord] = [
            AgentMemoryRecord(
                type="history",
                content=f"Previous run {report.run_id} ended with {report.status.upper()} after {report.iterations} iteration(s).",
                relevance_score=min(relevance_base, 1.0),
                severity="medium" if report.status != "passed" else "low",
                source_run_id=report.run_id,
            )
        ]

        if report.debug_history:
            latest_debug = report.debug_history[-1]
            for finding in latest_debug.findings[:2]:
                items.append(
                    AgentMemoryRecord(
                        type="bug",
                        content=f"{finding.title}: {finding.root_cause}",
                        relevance_score=min(relevance_base + 0.1, 1.0),
                        severity=finding.severity,
                        source_run_id=report.run_id,
                    )
                )

        if report.test_plan:
            items.append(
                AgentMemoryRecord(
                    type="test",
                    content=f"Recent plan emphasized {report.test_plan[0].category} coverage for {report.test_plan[0].target}.",
                    relevance_score=min(relevance_base - 0.05, 1.0),
                    severity="low",
                    source_run_id=report.run_id,
                )
            )

        return items
