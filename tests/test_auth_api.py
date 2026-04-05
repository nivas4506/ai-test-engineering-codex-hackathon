from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_sample_repository_requires_authentication() -> None:
    response = client.get("/sample-repository", follow_redirects=False)

    assert response.status_code == 401


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
