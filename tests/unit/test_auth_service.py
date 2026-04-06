from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import AUTH_COOKIE_NAME
from app.services import auth


@pytest.mark.unit
def test_hash_and_verify_password_round_trip() -> None:
    password_hash, salt = auth.hash_password("supersecure123")

    assert password_hash
    assert salt
    assert auth.verify_password("supersecure123", password_hash, salt) is True
    assert auth.verify_password("wrong-password", password_hash, salt) is False


@pytest.mark.unit
def test_create_access_token_returns_future_expiry() -> None:
    token, expires_at = auth.create_access_token()

    assert token
    assert isinstance(expires_at, datetime)
    assert expires_at > datetime.now(timezone.utc)


@pytest.mark.unit
def test_get_bearer_token_prefers_explicit_token_over_cookie() -> None:
    request = SimpleNamespace(cookies={AUTH_COOKIE_NAME: "cookie-token"})

    assert auth.get_bearer_token(request, "header-token") == "header-token"
    assert auth.get_bearer_token(request, None) == "cookie-token"


@pytest.mark.unit
def test_resolve_current_user_returns_none_for_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(cookies={})
    monkeypatch.setattr(auth.auth_repository, "get_user_by_token", lambda token: None)

    assert auth.resolve_current_user(request) is None


@pytest.mark.unit
def test_resolve_current_user_maps_repository_user(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(cookies={AUTH_COOKIE_NAME: "cookie-token"})
    fake_user = SimpleNamespace(id=7, email="user@example.com", full_name="Example User")
    monkeypatch.setattr(auth.auth_repository, "get_user_by_token", lambda token: fake_user)

    current_user = auth.resolve_current_user(request)

    assert current_user is not None
    assert current_user.id == 7
    assert current_user.email == "user@example.com"


@pytest.mark.unit
def test_get_current_user_raises_401_when_not_authenticated(monkeypatch: pytest.MonkeyPatch) -> None:
    request = SimpleNamespace(cookies={})
    monkeypatch.setattr(auth, "resolve_current_user", lambda request, token=None: None)

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(request, token=None)

    assert exc_info.value.status_code == 401
