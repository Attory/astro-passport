# SPDX-License-Identifier: AGPL-3.0-only
"""Inactive public scaffold. Scientific readiness always fails closed."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from app.api import SciencePort, UnavailableScience, install_api
from app.build import identity
from app.security import Settings


def create_app(settings: Settings | None = None, science: SciencePort | None = None) -> FastAPI:
    service = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, debug=False)

    @service.middleware("http")
    async def privacy_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @service.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @service.get("/health/ready")
    async def ready() -> JSONResponse:
        return JSONResponse(
            {"status": "not_ready", "reason": "science_unavailable"}, status_code=503
        )

    @service.get("/source")
    @service.get("/health/version")
    async def version() -> JSONResponse:
        data = identity()
        return JSONResponse(data, status_code=200 if data["git_sha"] else 503)

    install_api(service, settings or Settings.environment(), science or UnavailableScience())
    return service


app = create_app()
