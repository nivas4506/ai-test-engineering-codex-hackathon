from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.google_auth import GoogleIdentity


@pytest.mark.e2e
def test_google_login_and_sample_repository_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.routes as routes

    client = TestClient(app)
    monkeypatch.setattr(
        routes,
        "verify_google_credential",
        lambda credential: GoogleIdentity(
            email=f"journey-{uuid4().hex[:8]}@example.com",
            full_name="Journey User",
            google_sub=f"journey-{credential}",
        ),
    )

    login_response = client.post("/auth/google", json={"credential": "journey-credential"})
    sample_response = client.get("/sample-repository")
    status_response = client.get("/system/status")

    assert login_response.status_code == 200
    assert sample_response.status_code == 200
    assert "repository_path" in sample_response.json()
    assert status_response.status_code == 200
