from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from app.core.config import ACCESS_TOKEN_EXPIRE_HOURS, AUTH_COOKIE_NAME, OPENAI_REASONING_EFFORT
from app.db.auth_repository import AuthRepository
from app.db.repository import RunRepository
from app.models.schemas import (
    AnalyzeRequest,
    AuthResponse,
    GenerateTestsRequest,
    OrchestrateRequest,
    RunTestsRequest,
    SignUpRequest,
    SystemStatusResponse,
    UserProfileStats,
    UserProfileSummaryResponse,
    UpdateRunRequest,
    UploadResponse,
)
from app.services.auth import create_access_token, get_current_user, verify_password
from app.services.orchestrator import OrchestratorService
from app.services.openai_test_writer import OpenAITestWriter
from app.utils.files import (
    create_run_directory,
    save_uploaded_bundle,
    save_uploaded_input,
    snapshot_repository_metadata,
    write_json,
)


router = APIRouter()
orchestrator = OrchestratorService()
run_repository = RunRepository()
auth_repository = AuthRepository()
openai_writer = OpenAITestWriter()


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


@router.post("/auth/signup", response_model=AuthResponse)
def sign_up(request: SignUpRequest, response: Response):
    existing_user = auth_repository.get_user_by_email(request.email)
    if existing_user is not None:
        raise HTTPException(status_code=400, detail="An account with that email already exists.")

    from app.services.auth import hash_password  # local import to avoid circular import pressure

    password_hash, password_salt = hash_password(request.password)
    user = auth_repository.create_user(
        email=request.email,
        full_name=request.full_name,
        password_hash=password_hash,
        password_salt=password_salt,
    )
    access_token, expires_at = create_access_token()
    auth_repository.create_session(user_id=user.id, access_token=access_token, expires_at=expires_at)
    _set_auth_cookie(response, access_token)
    return AuthResponse(
        access_token=access_token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name},
    )


@router.post("/auth/token", response_model=AuthResponse)
def login_for_access_token(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    user = auth_repository.get_user_by_email(username)
    if user is None or not verify_password(password, user.password_hash, user.password_salt):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    access_token, expires_at = create_access_token()
    auth_repository.create_session(user_id=user.id, access_token=access_token, expires_at=expires_at)
    _set_auth_cookie(response, access_token)
    return AuthResponse(
        access_token=access_token,
        user={"id": user.id, "email": user.email, "full_name": user.full_name},
    )


@router.post("/auth/logout")
def logout(request: Request, response: Response, current_user=Depends(get_current_user)):
    access_token = request.cookies.get(AUTH_COOKIE_NAME)
    if access_token:
        auth_repository.revoke_session(access_token)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return {"ok": True}


@router.get("/auth/me")
def get_authenticated_user(current_user=Depends(get_current_user)):
    return current_user.model_dump()


@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status(current_user=Depends(get_current_user)):
    provider = openai_writer.provider_name
    return SystemStatusResponse(
        ai_provider=provider,
        ai_model=openai_writer.model if provider == "openai" else None,
        openai_configured=openai_writer.enabled,
        reasoning_effort=OPENAI_REASONING_EFFORT if provider == "openai" else None,
    )


@router.get("/profile/summary", response_model=UserProfileSummaryResponse)
def get_profile_summary(current_user=Depends(get_current_user)):
    user = auth_repository.get_user_by_id(current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User profile not found.")

    runs = run_repository.list_runs(limit=100, user_id=current_user.id)
    passed_runs = sum(1 for run in runs if run.status == "passed")
    latest_run = runs[0] if runs else None

    return UserProfileSummaryResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        member_since=user.created_at,
        last_login_at=user.last_login_at,
        stats=UserProfileStats(
            total_runs=len(runs),
            passed_runs=passed_runs,
            runs_needing_attention=len(runs) - passed_runs,
            latest_run_id=latest_run.run_id if latest_run else None,
            latest_run_status=latest_run.status if latest_run else None,
        ),
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_repository(
    files: list[UploadFile] | None = File(default=None),
    file: UploadFile | None = File(default=None),
    current_user=Depends(get_current_user),
):
    uploads = files or ([] if file is None else [file])
    if not uploads:
        raise HTTPException(status_code=400, detail="A file, archive, or folder upload is required.")

    try:
        if len(uploads) == 1:
            first_upload = uploads[0]
            if not first_upload.filename:
                raise HTTPException(status_code=400, detail="A file name is required for upload.")
            content = await first_upload.read()
            upload_id, repository_path = save_uploaded_input(first_upload.filename, content)
        else:
            bundle_files: list[tuple[str, bytes]] = []
            for upload in uploads:
                if not upload.filename:
                    raise HTTPException(status_code=400, detail="Each uploaded file must have a name.")
                bundle_files.append((upload.filename, await upload.read()))
            upload_id, repository_path = save_uploaded_bundle(bundle_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to process upload.") from exc

    original_filename = uploads[0].filename or "uploaded-content"
    return UploadResponse(upload_id=upload_id, repository_path=str(repository_path), original_filename=original_filename)


@router.post("/analyze")
def analyze_repository(request: AnalyzeRequest, current_user=Depends(get_current_user)):
    try:
        analysis = orchestrator.analyze(request.repository_path)
        plan = orchestrator.plan(analysis)
        return {"analysis": analysis.model_dump(), "plan": plan.model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate-tests")
def generate_tests(request: GenerateTestsRequest, current_user=Depends(get_current_user)):
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/run-tests")
def run_tests(request: RunTestsRequest, current_user=Depends(get_current_user)):
    run_dir = Path(__file__).resolve().parents[2] / "workspace" / "runs" / request.run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run ID not found: {request.run_id}")
    execution = orchestrator.executor.run(request.repository_path, run_dir)
    write_json(run_dir / "artifacts" / "execution.json", execution.model_dump())
    return execution.model_dump()


@router.post("/orchestrate")
def orchestrate_tests(request: OrchestrateRequest, current_user=Depends(get_current_user)):
    try:
        report = orchestrator.orchestrate(request.repository_path, request.max_retries, user_id=current_user.id)
        return report.model_dump()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def list_runs(current_user=Depends(get_current_user)):
    items = run_repository.list_runs(limit=20, user_id=current_user.id)
    if items:
        return [item.model_dump(mode="json") for item in items]
    return []


@router.get("/runs/latest/report")
def get_latest_run_report(current_user=Depends(get_current_user)):
    items = run_repository.list_runs(limit=1, user_id=current_user.id)
    if items:
        latest = run_repository.get_run_report(items[0].run_id, user_id=current_user.id)
        if latest is not None:
            return latest.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="No completed runs found.")


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str, current_user=Depends(get_current_user)):
    report = run_repository.get_run_report(run_id, user_id=current_user.id)
    if report is not None:
        return report.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"Run report not found for run_id={run_id}")


@router.patch("/runs/{run_id}")
def update_run(run_id: str, request: UpdateRunRequest, current_user=Depends(get_current_user)):
    updated = run_repository.update_run(run_id, status=request.status, notes=request.notes, user_id=current_user.id)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Run not found for run_id={run_id}")
    return updated.model_dump(mode="json")
