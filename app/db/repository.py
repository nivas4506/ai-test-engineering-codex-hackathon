from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.db.models import RunDebugAttempt, RunExecutionAttempt, RunGenerationAttempt, RunRecord
from app.db.session import get_db_session
from app.models.schemas import RunListItem, RunReport


class RunRepository:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def upsert_run_report(self, report: RunReport, max_retries: int, user_id: int | None = None) -> None:
        payload = report.model_dump(mode="json")
        try:
            with get_db_session() as session:
                record = session.scalar(select(RunRecord).where(RunRecord.run_id == report.run_id))
                if record is None:
                    record = RunRecord(
                        run_id=report.run_id,
                        repository_path=report.repository_path,
                        status=report.status,
                        iterations=report.iterations,
                        max_retries=max_retries,
                        owner_user_id=user_id,
                        full_report_json=payload,
                    )
                    session.add(record)
                    session.flush()
                else:
                    if user_id is not None and record.owner_user_id not in {None, user_id}:
                        raise PermissionError(f"run_id={report.run_id} belongs to a different user")
                    record.repository_path = report.repository_path
                    record.status = report.status
                    record.iterations = report.iterations
                    record.max_retries = max_retries
                    if user_id is not None:
                        record.owner_user_id = user_id
                    record.full_report_json = payload
                    record.generation_attempts.clear()
                    record.execution_attempts.clear()
                    record.debug_attempts.clear()
                    session.flush()

                for index, generation in enumerate(report.generation_history):
                    record.generation_attempts.append(
                        RunGenerationAttempt(
                            attempt_index=index,
                            mode=generation.mode,
                            summary=generation.summary,
                            generated_files_json=[item.model_dump(mode="json") for item in generation.generated_files],
                        )
                    )

                for index, execution in enumerate(report.execution_history):
                    record.execution_attempts.append(
                        RunExecutionAttempt(
                            attempt_index=index,
                            status=execution.status,
                            exit_code=execution.exit_code,
                            duration_seconds=execution.duration_seconds,
                            tests_collected=execution.tests_collected,
                            stdout=execution.stdout,
                            stderr=execution.stderr,
                            failing_tests_json=[item.model_dump(mode="json") for item in execution.failing_tests],
                            command_json=execution.command,
                        )
                    )

                for index, debug in enumerate(report.debug_history):
                    record.debug_attempts.append(
                        RunDebugAttempt(
                            attempt_index=index,
                            diagnosis=debug.diagnosis,
                            next_generation_mode=debug.next_generation_mode,
                            actions_json=[item.model_dump(mode="json") for item in debug.actions],
                        )
                    )

                session.commit()
        except Exception as exc:
            self.logger.warning("Skipping DB persistence for run_id=%s due to DB error: %s", report.run_id, exc)

    def get_run_report(self, run_id: str, user_id: int | None = None) -> RunReport | None:
        try:
            with get_db_session() as session:
                query = select(RunRecord).where(RunRecord.run_id == run_id)
                if user_id is not None:
                    query = query.where(RunRecord.owner_user_id == user_id)
                record = session.scalar(query)
                if record is None or record.full_report_json is None:
                    return None
                return RunReport.model_validate(record.full_report_json)
        except Exception as exc:
            self.logger.warning("Failed to fetch run report from DB for run_id=%s: %s", run_id, exc)
            return None

    def list_runs(self, limit: int = 20, user_id: int | None = None) -> list[RunListItem]:
        try:
            with get_db_session() as session:
                query = select(RunRecord)
                if user_id is not None:
                    query = query.where(RunRecord.owner_user_id == user_id)
                query = query.order_by(desc(RunRecord.created_at)).limit(limit)
                records = session.scalars(query).all()
                result: list[RunListItem] = []
                for record in records:
                    latest_test_count = None
                    if record.execution_attempts:
                        latest_execution = max(record.execution_attempts, key=lambda item: item.attempt_index)
                        latest_test_count = latest_execution.tests_collected
                    result.append(
                        RunListItem(
                            run_id=record.run_id,
                            repository_path=record.repository_path,
                            status=record.status,
                            iterations=record.iterations,
                            created_at=record.created_at or datetime.now(timezone.utc),
                            latest_test_count=latest_test_count,
                        )
                    )
                return result
        except Exception as exc:
            self.logger.warning("Failed to list runs from DB: %s", exc)
            return []

    def update_run(
        self,
        run_id: str,
        status: str | None = None,
        notes: str | None = None,
        user_id: int | None = None,
    ) -> RunReport | None:
        try:
            with get_db_session() as session:
                query = select(RunRecord).where(RunRecord.run_id == run_id)
                if user_id is not None:
                    query = query.where(RunRecord.owner_user_id == user_id)
                record = session.scalar(query)
                if record is None:
                    return None

                if status is not None:
                    record.status = status
                if notes is not None:
                    record.notes = notes

                if record.full_report_json:
                    payload = record.full_report_json
                    if status is not None:
                        payload["status"] = status
                    record.full_report_json = payload

                session.commit()
                if record.full_report_json is None:
                    return None
                return RunReport.model_validate(record.full_report_json)
        except Exception as exc:
            self.logger.warning("Failed to update run in DB for run_id=%s: %s", run_id, exc)
            return None
