from __future__ import annotations

from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import GOOGLE_CLIENT_ID


@dataclass
class GoogleIdentity:
    email: str
    full_name: str
    google_sub: str


def google_sign_in_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID)


def verify_google_credential(credential: str) -> GoogleIdentity:
    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google sign-in is not configured.")

    payload = id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    email = str(payload.get("email", "")).strip().lower()
    full_name = str(payload.get("name", "")).strip() or email
    google_sub = str(payload.get("sub", "")).strip()

    if not email or not google_sub:
        raise ValueError("Google credential is missing required identity claims.")

    return GoogleIdentity(email=email, full_name=full_name, google_sub=google_sub)
