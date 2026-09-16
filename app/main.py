# SPDX-License-Identifier: AGPL-3.0-only
"""Default-disabled service; science is initialized only from explicit local artifacts."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from app.api import SciencePort, UnavailableScience, install_api
from app.build import identity
from app.contracts import AstroPassportRequestV1, AstroPassportResponseV1
from app.security import Settings


def create_app(settings: Settings | None = None, science: SciencePort | None = None) -> FastAPI:
    configured = settings or Settings.environment()

    class Runtime:
        delegate: SciencePort = science or UnavailableScience()
        ready = False

        async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
            return await self.delegate.calculate(request)

    runtime = Runtime()

    @asynccontextmanager
    async def lifespan(service: FastAPI) -> AsyncIterator[None]:
        if science is None and configured.enabled and configured.science_directory is not None:
            from app.science.pipeline import PassportScience

            try:
                runtime.delegate = await asyncio.to_thread(
                    PassportScience, configured.science_directory
                )
                runtime.ready = True
            except Exception:
                # No traceback, artifact path or scientific input in logs/health output.
                runtime.delegate = UnavailableScience()
                runtime.ready = False
        yield
        runtime.ready = False

    service = FastAPI(
        docs_url=None, redoc_url=None, openapi_url=None, debug=False, lifespan=lifespan
    )

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
        if runtime.ready:
            return JSONResponse({"status": "ready"})
        return JSONResponse(
            {"status": "not_ready", "reason": "science_unavailable"}, status_code=503
        )

    @service.get("/source")
    @service.get("/health/version")
    async def version() -> JSONResponse:
        data = identity()
        return JSONResponse(data, status_code=200 if data["git_sha"] else 503)

    install_api(service, configured, runtime)
    return service


app = create_app()
