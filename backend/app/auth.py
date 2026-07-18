from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def auth_enabled() -> bool:
    return bool(os.getenv("APP_AUTH_TOKEN"))


def require_session(authorization: str | None = Header(default=None)) -> dict[str, str]:
    expected = os.getenv("APP_AUTH_TOKEN")
    if not expected:
        return {"mode": "local", "subject": "local-demo"}
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    supplied = authorization[len(prefix) :]
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Invalid bearer token.")
    return {"mode": "token", "subject": "authenticated-user"}
