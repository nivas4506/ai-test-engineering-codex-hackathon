from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeRequest,
    GenerateTestsRequest,
    OrchestrateRequest,
    RunTestsRequest,
)
from app.services.orchestrator import OrchestratorService
from app.utils.files import create_run_directory, snapshot_repository_metadata, write_json


router = APIRouter()
orchestrator = OrchestratorService()


@router.post("/analyze")
def analyze_repository(request: AnalyzeRequest):
    try:
        analysis = orchestrator.analyze(request.repository_path)
        plan = orchestrator.plan(analysis)
        return {"analysis": analysis.model_dump(), "plan": plan.model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generate-tests")
def generate_tests(request: GenerateTestsRequest):
    try:
        run_id, run_dir = create_run_directory()
        repo_path = Path(request.repository_path).resolve()
        snapshot_repository_metadata(repo_path, run_dir)
        analysis = orchestrator.analyze(request.repository_path)
        plan = orchestrator.plan(analysis)
        generation = orchestrator.generator.generate(request.repository_path, run_dir, analysis, plan)
        write_json(run_dir / "artifacts" / "analysis.json", analysis.model_dump())
        write_json(run_dir / "artifacts" / "plan.json", plan.model_dump())
        write_json(run_dir / "artifacts" / "generation.json", generation.model_dump())
        return {"run_id": run_id, "generation": generation.model_dump(), "generated_dir": str(run_dir / "generated_tests")}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/run-tests")
def run_tests(request: RunTestsRequest):
    run_dir = Path(__file__).resolve().parents[2] / "workspace" / "runs" / request.run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run ID not found: {request.run_id}")
    execution = orchestrator.executor.run(request.repository_path, run_dir)
    write_json(run_dir / "artifacts" / "execution.json", execution.model_dump())
    return execution.model_dump()


@router.post("/orchestrate")
def orchestrate_tests(request: OrchestrateRequest):
    try:
        report = orchestrator.orchestrate(request.repository_path, request.max_retries)
        return report.model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str):
    report_path = Path(__file__).resolve().parents[2] / "workspace" / "runs" / run_id / "artifacts" / "final_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Run report not found for run_id={run_id}")
    return json.loads(report_path.read_text(encoding="utf-8"))
