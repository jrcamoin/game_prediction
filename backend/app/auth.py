from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

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
    jwt_subject = verify_session_token(supplied)
    if jwt_subject:
        return {"mode": "jwt", "subject": jwt_subject}
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Invalid bearer token.")
    return {"mode": "token", "subject": "authenticated-user"}


def issue_session_token(subject: str, ttl_seconds: int = 86400) -> str:
    secret = os.getenv("APP_AUTH_TOKEN")
    if not secret:
        raise HTTPException(status_code=400, detail="APP_AUTH_TOKEN is not configured.")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "exp": int(time.time()) + ttl_seconds}
    signing_input = f"{_encode(header)}.{_encode(payload)}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}"


def verify_session_token(token: str) -> str | None:
    secret = os.getenv("APP_AUTH_TOKEN")
    if not secret or token.count(".") != 2:
        return None
    header_part, payload_part, signature_part = token.split(".")
    signing_input = f"{header_part}.{payload_part}"
    expected = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    supplied = _decode_bytes(signature_part)
    if supplied is None or not hmac.compare_digest(supplied, expected):
        return None
    payload = _decode_json(payload_part)
    if not payload or int(payload.get("exp", 0)) < int(time.time()):
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def _encode(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_json(value: str) -> dict[str, object] | None:
    raw = _decode_bytes(value)
    if raw is None:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _decode_bytes(value: str) -> bytes | None:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    except (ValueError, TypeError):
        return None
