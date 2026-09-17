# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed API scaffold; no engine, provider, birth persistence or implicit retries."""

import asyncio
import datetime as dt
import json
from typing import Protocol

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from app.contracts import (
    AstroPassportRequestV1,
    AstroPassportResponseV1,
    ErrorCode,
    ErrorEnvelopeV1,
)
from app.science.errors import STATUS, ScienceFailure
from app.security import SecurityStateError, Settings, authenticate, reserve_quota, unique_json

MAX_BODY = 16384
MAX_HEADERS = 16384
BODY_SECONDS = 2.0


class ScienceUnavailable(Exception):
    pass


class SciencePort(Protocol):
    async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1: ...


class UnavailableScience:
    async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
        raise ScienceUnavailable


def error(status: int, code: ErrorCode) -> JSONResponse:
    headers = {"Cache-Control": "no-store", "X-APT-Contract-Version": "1.0.0"}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(
        ErrorEnvelopeV1(
            schema_version="AstroPassportError.v1", contract_version="1.0.0", code=code
        ).model_dump(),
        status_code=status,
        headers=headers,
    )


def install_api(service: FastAPI, settings: Settings, science: SciencePort) -> None:
    slots: asyncio.Queue[None] = asyncio.Queue(maxsize=4)
    for _ in range(4):
        slots.put_nowait(None)

    @service.post("/v1/passports")
    async def calculate(request: Request) -> JSONResponse:
        if not settings.enabled:
            return error(503, "disabled")
        if request.url.scheme != "https" or request.scope.get("query_string"):
            return error(400, "invalid_request")
        headers = request.scope["headers"]
        if sum(len(k) + len(v) for k, v in headers) > MAX_HEADERS:
            return error(413, "too_large")
        for name in ("authorization", "content-length", "content-type", "x-apt-contract-version"):
            if len(request.headers.getlist(name)) > 1:
                return error(400, "invalid_request")
        try:
            slots.get_nowait()
        except asyncio.QueueEmpty:
            return error(503, "busy")
        try:
            try:
                now = dt.datetime.now(dt.UTC)
                key = await asyncio.to_thread(
                    authenticate, settings.keys_file, request.headers.get("authorization", ""), now
                )
                if key is None:
                    return error(401, "unauthorized")
                if request.headers.get("x-apt-contract-version") != "1.0.0":
                    return error(406, "unsupported_version")
                if request.headers.get("content-type", "").lower() != "application/json":
                    return error(415, "unsupported_media_type")
                if request.headers.get("content-encoding") not in (None, "identity"):
                    return error(415, "unsupported_media_type")
                length = request.headers.get("content-length")
                if length is not None and (not length.isascii() or not length.isdecimal()):
                    return error(400, "invalid_request")
                if length is not None and (len(length) > 8 or int(length) > MAX_BODY):
                    return error(413, "too_large")
                if not await asyncio.to_thread(reserve_quota, settings.quota_file, key, now):
                    return error(429, "rate_limited")
                body = bytearray()
                async with asyncio.timeout(BODY_SECONDS):
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > MAX_BODY:
                            return error(413, "too_large")
                        body.extend(chunk)
                if length is not None and len(body) != int(length):
                    return error(400, "invalid_request")
                try:
                    unique_json(bytes(body))
                    value = AstroPassportRequestV1.model_validate_json(body)
                except (ValueError, TypeError, RecursionError):
                    return error(422, "invalid_request")
                async with asyncio.timeout(6):
                    result = await science.calculate(value)
                # Deserialization is shape checking, NOT authenticity; only this trusted port
                # may construct successful facts after its independent scientific acceptance.
                checked = AstroPassportResponseV1.model_validate_json(result.model_dump_json())
                return JSONResponse(
                    json.loads(checked.model_dump_json()),
                    headers={"X-APT-Contract-Version": "1.0.0"},
                )
            except SecurityStateError:
                return error(503, "state_unavailable")
            except ScienceUnavailable:
                return error(503, "science_unavailable")
            except ScienceFailure as failure:
                return error(STATUS[failure.code], failure.code)
            except TimeoutError:
                return error(408, "timeout")
            except Exception:
                # Never log traceback, locals, input, URLs or native messages.
                return error(500, "internal_error")
        finally:
            slots.put_nowait(None)
