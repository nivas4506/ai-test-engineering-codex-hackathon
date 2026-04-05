from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import ACCESS_TOKEN_EXPIRE_HOURS, AUTH_COOKIE_NAME
from app.db.auth_repository import AuthRepository
from app.models.schemas import AuthenticatedUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
auth_repository = AuthRepository()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt=salt)
    return secrets.compare_digest(candidate_hash, password_hash)


def create_access_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return token, expires_at


def get_bearer_token(request: Request, token: str | None) -> str | None:
    if token:
        return token
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    return None


def resolve_current_user(request: Request, token: str | None = None) -> AuthenticatedUser | None:
    bearer_token = get_bearer_token(request, token)
    if not bearer_token:
        return None
    user = auth_repository.get_user_by_token(bearer_token)
    if user is None:
        return None
    return AuthenticatedUser(id=user.id, email=user.email, full_name=user.full_name)


def get_current_user_optional(request: Request, token: str | None = Depends(oauth2_scheme)) -> AuthenticatedUser | None:
    return resolve_current_user(request, token)


def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> AuthenticatedUser:
    user = resolve_current_user(request, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
