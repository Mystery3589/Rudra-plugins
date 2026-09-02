"""Authentication & Security middleware for Rudra Web UI."""

from __future__ import annotations

import secrets
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

_SERVER_TOKEN: str = ""


def set_server_token(token: str) -> None:
    global _SERVER_TOKEN
    _SERVER_TOKEN = token


def get_server_token() -> str:
    global _SERVER_TOKEN
    if not _SERVER_TOKEN:
        _SERVER_TOKEN = secrets.token_hex(16)
    return _SERVER_TOKEN


def is_local_client(client_host: str | None) -> bool:
    """Return True if request originates from localhost / loopback."""
    if not client_host:
        return True
    return client_host in ("127.0.0.1", "::1", "localhost", "testclient")


def verify_token(req: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Validate client token for non-localhost connections."""
    client_host = req.client.host if req.client else None

    # Localhost requests bypass token requirement
    if is_local_client(client_host):
        return True

    # Check header token
    provided = credentials.credentials if credentials else None
    if not provided:
        # Check query param for WebSockets / direct links
        provided = req.query_params.get("token")

    expected = get_server_token()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing remote access token")

    return True
