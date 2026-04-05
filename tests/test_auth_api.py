from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import init_database
from app.main import app
from app.services.google_auth import GoogleIdentity


init_database()
client = TestClient(app)


def test_sample_repository_requires_authentication() -> None:
    response = client.get("/sample-repository", follow_redirects=False)

    assert response.status_code == 401


def test_signup_page_is_available() -> None:
    response = client.get("/signup", follow_redirects=False)

    assert response.status_code == 200
    assert "Create your account" in response.text


def test_signup_then_read_sample_repository() -> None:
    email = f"test-{uuid4().hex[:8]}@example.com"
    signup_response = client.post(
        "/auth/signup",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "supersecure123",
        },
    )

    assert signup_response.status_code == 200

    client.cookies.update(signup_response.cookies)
    sample_response = client.get("/sample-repository")

    assert sample_response.status_code == 200
    assert "samples" in sample_response.json()["repository_path"]


def test_google_auth_config(monkeypatch) -> None:
    import app.api.routes as routes

    monkeypatch.setattr(routes, "google_sign_in_enabled", lambda: True)
    monkeypatch.setattr(routes, "GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")

    response = client.get("/auth/google/config")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "client_id": "test-google-client-id.apps.googleusercontent.com",
    }


def test_google_login_then_read_sample_repository(monkeypatch) -> None:
    import app.api.routes as routes

    monkeypatch.setattr(
        routes,
        "verify_google_credential",
        lambda credential: GoogleIdentity(
            email=f"google-{uuid4().hex[:8]}@example.com",
            full_name="Google User",
            google_sub=f"sub-{credential}",
        ),
    )

    login_response = client.post("/auth/google", json={"credential": "fake-credential"})

    assert login_response.status_code == 200

    client.cookies.update(login_response.cookies)
    sample_response = client.get("/sample-repository")

    assert sample_response.status_code == 200
