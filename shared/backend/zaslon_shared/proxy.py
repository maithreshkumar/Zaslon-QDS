from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .auth import API_KEY_HEADER_NAME
from .config import settings


ProxyRole = Literal["ALICE", "BOB", "ATTACK"]
_HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


def _role_key(role: ProxyRole) -> str:
    return {
        "ALICE": settings.alice_api_key,
        "BOB": settings.bob_api_key,
        "ATTACK": settings.attack_api_key,
    }[role]


def _allowed_path(role: ProxyRole, path: str) -> bool:
    prefixes = {
        "ALICE": ("/api/v1/alice/", "/api/v1/sessions/"),
        "BOB": ("/api/v1/bob/", "/api/v1/sessions/"),
        "ATTACK": ("/api/v1/attacks/", "/api/v1/results/"),
    }[role]
    if path.startswith("/api/v1/jobs/"):
        return True
    if role == "ATTACK" and path == "/api/v1/sessions":
        return True
    return any(path.startswith(prefix) for prefix in prefixes)


def create_role_proxy(*, role: ProxyRole, browser_origin: str) -> FastAPI:
    key = _role_key(role)
    if len(key) < 32 or key.startswith("replace-with-"):
        raise RuntimeError(
            f"The {role} proxy requires a non-template server-side role credential of at least 32 characters."
        )
    core_url = os.getenv("ZASLON_CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    app = FastAPI(
        title=f"ZASLON-QDS {role.title()} localhost proxy",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            browser_origin,
            browser_origin.replace("127.0.0.1", "localhost"),
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
        expose_headers=["Content-Disposition"],
    )

    @app.get("/proxy-health")
    def proxy_health() -> dict:
        return {
            "status": "ok",
            "role": role,
            "credential_location": "SERVER_SIDE_ONLY",
            "core": core_url,
        }

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def proxy(path: str, request: Request) -> Response:
        request_path = "/" + path
        if not _allowed_path(role, request_path):
            raise HTTPException(403, "This role proxy does not expose that core endpoint.")
        inbound_headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() not in _HOP_BY_HOP_HEADERS
            and name.lower() != API_KEY_HEADER_NAME.lower()
            and name.lower() != "origin"
        }
        inbound_headers[API_KEY_HEADER_NAME] = key
        try:
            import httpx

            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                upstream = await client.request(
                    request.method,
                    f"{core_url}{request_path}",
                    params=request.query_params,
                    headers=inbound_headers,
                    content=await request.body(),
                )
        except Exception as exc:
            raise HTTPException(502, "The trusted core API is unavailable.") from exc
        response_headers = {
            name: value
            for name, value in upstream.headers.items()
            if name.lower() in {"content-type", "content-disposition", "retry-after"}
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )

    return app
