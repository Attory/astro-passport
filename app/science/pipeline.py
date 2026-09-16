# SPDX-License-Identifier: AGPL-3.0-only
"""One person's deterministic facts; no provider calls or compatibility methodology."""

import asyncio
import datetime as dt
import threading
from pathlib import Path
from typing import Any

from app.build import require_revision
from app.contracts import AstroPassportRequestV1, AstroPassportResponseV1, ErrorCode
from app.science.boundaries.contracts import GeographicCoordinates, TimezoneBoundaryError
from app.science.boundaries.tbb import TBBTimezoneBoundaryResolver
from app.science.civil.contracts import CivilTimeError
from app.science.civil.tzdb import PinnedCivilTimeResolver
from app.science.ephemeris.adapter import SwissEphemeris
from app.science.ephemeris.contracts import EphemerisError, EphemerisRequest
from app.science.errors import ScienceFailure
from app.science.natal.service import NatalError, NatalService
from app.science.raw_input import RawBirthInput

ERROR_CODES: dict[str, ErrorCode] = {
    "invalid_input": "invalid_request",
    "unresolved_zone": "invalid_result",
    "invalid_fold": "invalid_fold",
    "ambiguous_local_time": "civil_ambiguous",
    "nonexistent_local_time": "civil_nonexistent",
    "artifact_unavailable": "artifact_unavailable",
    "artifact_integrity": "artifact_integrity",
    "artifact_invalid": "artifact_invalid",
    "unsupported_runtime": "unsupported_runtime",
    "data_unavailable": "artifact_unavailable",
    "data_integrity": "artifact_integrity",
    "busy": "busy",
    "timeout": "timeout",
    "native_failure": "native_failure",
    "fallback_rejected": "fallback_rejected",
    "invalid_result": "invalid_result",
    "replay_mismatch": "invalid_result",
    "async_context": "internal_error",
}


class PassportScience:
    """Construct once from operator-owned read-only artifacts, never request paths.

    The thread-held capacity outlives cancellation of an HTTP waiter: timed-out work
    cannot release a slot early and cause an unbounded queue of native processes.
    """

    def __init__(self, directory: Path) -> None:
        self.revision = require_revision()
        self._capacity = threading.BoundedSemaphore(2)
        self.boundaries = TBBTimezoneBoundaryResolver(directory / "boundaries")
        self.civil = PinnedCivilTimeResolver(directory / "civil")
        self.natal = NatalService(SwissEphemeris(directory / "swiss"))
        # Startup checks exercise exact runtime/binary/data/worker prerequisites, not a
        # personal case. Failure prevents the instance from ever becoming ready.
        self.natal.calculate(EphemerisRequest(utc=dt.datetime(2000, 1, 1, tzinfo=dt.UTC)))
        self.ready = True

    def _calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
        try:
            value = AstroPassportRequestV1.model_validate_json(request.model_dump_json())
            boundary = self.boundaries.resolve(
                GeographicCoordinates(
                    latitude=value.selected_place.latitude, longitude=value.selected_place.longitude
                )
            )
            if boundary.status != "resolved":
                code: ErrorCode = {
                    "boundary": "boundary_boundary",
                    "ambiguous": "boundary_ambiguous",
                    "no_match": "boundary_no_match",
                }[boundary.status]  # type: ignore[assignment]
                raise ScienceFailure(code)
            civil = self.civil.resolve(
                RawBirthInput(
                    date=dt.date.fromisoformat(value.civil.date),
                    time=dt.time.fromisoformat(value.civil.time),
                    place_query="selected",
                ),
                boundary,
                fold_choice=value.civil.fold,
            )
            astronomy = self.natal.calculate(EphemerisRequest(utc=civil.utc)).astronomy
            provenance = astronomy.provenance.model_dump(mode="json")
            provenance.update(
                schema_version="AstroPassportProvenance.v1",
                ephemeris_schema=astronomy.schema_version,
                tt_jd_binary64=astronomy.jd_tt_hex,
                ut1_jd_binary64=astronomy.jd_ut1_hex,
                limitations=list(astronomy.limitations),
            )
            response: dict[str, Any] = {
                "schema_version": "AstroPassportResponse.v1",
                "contract_version": "1.0.0",
                "profile": "sun-moon.v1",
                "selected_place": value.selected_place.model_dump(mode="json"),
                "civil_input": {
                    "date": civil.local_date.isoformat(),
                    "time": civil.local_time.isoformat(timespec="microseconds"),
                    "fold": civil.fold_choice,
                },
                "boundary": {
                    "schema_version": boundary.schema_version,
                    "outcome": "unique",
                    "iana_zone": boundary.tzid,
                    "provenance": boundary.provenance.model_dump(mode="json"),
                },
                "civil": {
                    "schema_version": civil.schema_version,
                    "utc": civil.utc.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    "offset_seconds": civil.offset_seconds,
                    "resolution": civil.resolution,
                    "fold": civil.fold_choice,
                    "provenance": civil.provenance.model_dump(mode="json"),
                    "limitations": list(civil.limitations),
                },
                "bodies": [
                    {
                        "body": body.body,
                        "binary64_hex": body.binary64_hex,
                        "decimal_degrees": format(body.longitude if body.longitude else 0, ".9f"),
                    }
                    for body in astronomy.positions
                ],
                "provenance": provenance,
                "serialization": "astro-passport-json.v1",
                "authenticity": "unsigned-direct-client-only",
            }
            # JSON-mode accepts ordered JSON arrays without relaxing scalar strictness.
            import json

            return AstroPassportResponseV1.model_validate_json(json.dumps(response))
        except (TimezoneBoundaryError, CivilTimeError, EphemerisError, NatalError) as exc:
            raise ScienceFailure(ERROR_CODES[exc.category.value]) from None

    async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
        if not self._capacity.acquire(blocking=False):
            raise ScienceFailure("busy")

        def work() -> AstroPassportResponseV1:
            try:
                return self._calculate(request)
            finally:
                self._capacity.release()

        # Submitting before awaiting prevents cancellation before thread start from
        # leaking the capacity token. Cancellation never cancels the native timeout.
        loop = asyncio.get_running_loop()
        try:
            future = loop.run_in_executor(None, work)
        except BaseException:
            self._capacity.release()
            raise
        # Retrieve late failures after disconnected/timed-out waiters without logging
        # request locals or emitting an unhandled-future traceback.
        future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        return await asyncio.shield(future)
