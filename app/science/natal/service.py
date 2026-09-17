# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/services/western_natal.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 11e99942c114bc3f33df47c23d1a062fb2ec40b48eaaf19984a0b71c513d0910
"""Trusted UTC-to-natal service. Deliberately synchronous, non-exposed and non-persistent."""

import asyncio
from enum import StrEnum

from app.science.ephemeris.contracts import Ephemeris, EphemerisRequest, EphemerisResult
from app.science.natal.facts import NatalFacts


class NatalFailure(StrEnum):
    INVALID_INPUT = "invalid_input"
    INVALID_RESULT = "invalid_result"
    REPLAY_MISMATCH = "replay_mismatch"
    ASYNC_CONTEXT = "async_context"


class NatalError(ValueError):
    def __init__(self, category: NatalFailure) -> None:
        self.category = category
        super().__init__(f"Natal fact failure: {category.value}")


def _require_worker_context() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    # A later async application must use a bounded worker, never block its event loop.
    raise NatalError(NatalFailure.ASYNC_CONTEXT)


class NatalService:
    """Inject only a trusted ephemeris implementation, never a client-supplied result."""

    def __init__(self, ephemeris: Ephemeris) -> None:
        self._ephemeris = ephemeris

    def calculate(self, request: EphemerisRequest) -> NatalFacts:
        _require_worker_context()
        captured = None
        try:
            if isinstance(request, EphemerisRequest):
                captured = EphemerisRequest.model_validate(request.model_dump(warnings=False))
        except (ValueError, TypeError, OverflowError):
            pass
        if captured is None:
            raise NatalError(NatalFailure.INVALID_INPUT)
        # Keep the captured request private even if a faulty injected port mutates its copy.
        astronomy = self._ephemeris.calculate(
            EphemerisRequest.model_validate(captured.model_dump(warnings=False))
        )
        result = None
        try:
            if isinstance(astronomy, EphemerisResult):
                candidate = NatalFacts(astronomy=astronomy)
                if candidate.astronomy.utc == captured.utc:
                    result = candidate
        except (ValueError, TypeError, OverflowError):
            pass
        if result is None:
            raise NatalError(NatalFailure.INVALID_RESULT)
        return result

    def verify_facts(self, facts: NatalFacts) -> NatalFacts:
        """Replay against this exact execution identity; schema validation is not proof."""
        _require_worker_context()
        captured = None
        try:
            if isinstance(facts, NatalFacts):
                captured = NatalFacts.model_validate(facts.model_dump(warnings=False))
        except (ValueError, TypeError, OverflowError):
            pass
        if captured is None:
            raise NatalError(NatalFailure.INVALID_INPUT)
        actual = self.calculate(EphemerisRequest(utc=captured.astronomy.utc))
        if actual != captured:
            raise NatalError(NatalFailure.REPLAY_MISMATCH)
        return actual
