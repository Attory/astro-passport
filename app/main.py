# SPDX-License-Identifier: AGPL-3.0-only
"""Default-disabled service; science is initialized only from explicit local artifacts."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from app.api import SciencePort, ScienceUnavailable, UnavailableScience, install_api
from app.build import identity
from app.contracts import AstroPassportRequestV1, AstroPassportResponseV1, SelectedPlace
from app.lahiri import LahiriRequest, LahiriResponse
from app.portable import PortableIssuer
from app.security import Settings
from app.western import WesternRequest, WesternResponse


def create_app(settings: Settings | None = None, science: SciencePort | None = None) -> FastAPI:
    configured = settings or Settings.environment()

    class Runtime:
        delegate: SciencePort = science or UnavailableScience()
        ready = False

        async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
            return await self.delegate.calculate(request)

        async def calculate_lahiri(self, request: LahiriRequest) -> LahiriResponse:
            method = getattr(self.delegate, "calculate_lahiri", None)
            if method is None:
                raise ScienceUnavailable
            result = await method(request)
            return LahiriResponse.model_validate_json(result.model_dump_json())

        async def calculate_western(self, request: WesternRequest) -> WesternResponse:
            method = getattr(self.delegate, "calculate_western", None)
            if method is None:
                raise ScienceUnavailable
            result = await method(request)
            return WesternResponse.model_validate_json(result.model_dump_json())

        async def calculate_portable(
            self, request: WesternRequest
        ) -> tuple[WesternResponse, dict[int, Any] | None]:
            method = getattr(self.delegate, "calculate_portable", None)
            if method is None:
                raise ScienceUnavailable
            result = await method(request)
            return WesternResponse.model_validate_json(result[0].model_dump_json()), result[1]

        async def describe_unknown(self, selected: SelectedPlace) -> dict[str, Any]:
            method = getattr(self.delegate, "describe_unknown", None)
            if method is None:
                raise ScienceUnavailable
            result: dict[str, Any] = await method(selected)
            return result

    runtime = Runtime()
    issuer = None
    if configured.signing_key_file is not None and configured.signing_key_id is not None:
        try:
            issuer = PortableIssuer(configured.signing_key_file, configured.signing_key_id)
        except Exception:
            # Legacy consumers remain available; signed issuance fails closed.
            issuer = None

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

    @service.get("/v2/health/ready")
    async def portable_ready() -> JSONResponse:
        available = runtime.ready and issuer is not None
        return JSONResponse(
            {"status": "ready" if available else "not_ready", "contract_version": "2.0.0"},
            status_code=200 if available else 503,
        )

    @service.get("/source")
    @service.get("/health/version")
    @service.get("/v2/source")
    @service.get("/v2/health/version")
    async def version() -> JSONResponse:
        data = identity()
        return JSONResponse(data, status_code=200 if data["git_sha"] else 503)

    install_api(service, configured, runtime, issuer)
    return service


app = create_app()
