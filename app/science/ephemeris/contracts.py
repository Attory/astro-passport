# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/ephemeris/ports/ephemeris.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 456c4ba5c9e87951ff30f18b70aed1bf974a1a8c02f457270de450746188cced
"""Provider-neutral astronomical boundary; no birth, geography or participant inputs."""

import datetime as dt
import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EphemerisFailure(StrEnum):
    INVALID_INPUT = "invalid_input"
    DATA_UNAVAILABLE = "data_unavailable"
    DATA_INTEGRITY = "data_integrity"
    UNSUPPORTED_RUNTIME = "unsupported_runtime"
    BUSY = "busy"
    TIMEOUT = "timeout"
    NATIVE_FAILURE = "native_failure"
    FALLBACK_REJECTED = "fallback_rejected"
    INVALID_RESULT = "invalid_result"


class EphemerisError(Exception):
    def __init__(self, category: EphemerisFailure) -> None:
        self.category = category
        super().__init__(f"Ephemeris failure: {category.value}")


class EphemerisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    utc: dt.datetime = Field(repr=False)

    @field_validator("utc")
    @classmethod
    def explicit_utc(cls, value: dt.datetime) -> dt.datetime:
        if (
            value.utcoffset() != dt.timedelta(0)
            or value.fold != 0
            or not dt.datetime(1899, 12, 31, tzinfo=dt.UTC)
            <= value
            < dt.datetime(2101, 1, 2, tzinfo=dt.UTC)
        ):
            raise ValueError("an explicit supported UTC instant is required")
        return value.astimezone(dt.UTC)


def longitude_decimal(raw: float) -> Decimal:
    if not math.isfinite(raw) or not 0 <= raw < 360:
        raise ValueError("invalid astronomical longitude")
    # Enforce the existing nine-decimal policy independently of a caller's precision/traps.
    with localcontext(Context(prec=40, rounding=ROUND_HALF_EVEN)):
        return Decimal(str(raw)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN) % 360


class BodyLongitude(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    body: Literal["sun", "moon"]
    longitude: Decimal = Field(ge=0, lt=360, allow_inf_nan=False, repr=False)
    binary64_hex: str = Field(max_length=32, repr=False)

    @field_validator("longitude", mode="before")
    @classmethod
    def bound_decimal_text(cls, value: object) -> object:
        # Normal output needs at most13 characters. Bound redundant untrusted encodings before
        # Pydantic constructs a Decimal; numeric equality alone accepts arbitrarily many zeros.
        if isinstance(value, str) and len(value) > 32:
            raise ValueError("bounded astronomical longitude encoding required")
        return value

    @field_validator("longitude")
    @classmethod
    def bound_decimal_coefficient(cls, value: Decimal) -> Decimal:
        parts = value.as_tuple()
        if (
            len(parts.digits) > 32
            or not isinstance(parts.exponent, int)
            or not -32 <= parts.exponent <= 32
        ):
            raise ValueError("bounded astronomical longitude encoding required")
        return value

    @model_validator(mode="after")
    def exact_projection(self) -> Self:
        raw = float.fromhex(self.binary64_hex)
        if raw.hex() != self.binary64_hex or longitude_decimal(raw) != self.longitude:
            raise ValueError("inconsistent astronomical longitude")
        return self


class EphemerisProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    adapter: Literal["swiss-isolated.v1"]
    binding: Literal["pysweph-2.10.3.6"]
    library: Literal["2.10.03"]
    binary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    planet_data_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    moon_data_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_origin: Literal["DE441"]
    requested_flags: Literal[2]
    returned_flags: tuple[Literal[2], Literal[2]]
    projection: Literal["geocentric-tropical-apparent-ecliptic-of-date"]
    numerical_policy: Literal["binary64-to-decimal-9dp-half-even.v1"]
    time_policy: Literal["pinned-leaps-2016-pre1972-ut1-proxy.v1"]
    delta_t_policy: Literal["swiss-2.10.03-auto-model-tidal-DE441"]
    runtime: Literal["CPython-3.12.14-Linux-x86_64"]
    source_repository: Literal["https://github.com/Attory/astro-passport"]
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")


class EphemerisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["ephemeris.v1"] = "ephemeris.v1"
    utc: dt.datetime = Field(repr=False)
    positions: tuple[BodyLongitude, BodyLongitude] = Field(repr=False)
    jd_tt_hex: str = Field(max_length=32, repr=False)
    jd_ut1_hex: str = Field(max_length=32, repr=False)
    limitations: tuple[
        Literal[
            "modelled-ut1-not-measured-earth-orientation",
            "pre1972-proleptic-utc-used-as-ut1-proxy",
            "leap-table-frozen-after-2016-not-a-future-prediction",
        ],
        ...,
    ] = Field(min_length=1, max_length=2, repr=False)
    provenance: EphemerisProvenance

    @model_validator(mode="after")
    def coherent(self) -> Self:
        EphemerisRequest(utc=self.utc)
        expected = ["modelled-ut1-not-measured-earth-orientation"]
        if self.utc.year < 1972:
            expected.append("pre1972-proleptic-utc-used-as-ut1-proxy")
        elif self.utc.year >= 2017:
            expected.append("leap-table-frozen-after-2016-not-a-future-prediction")
        if self.limitations != tuple(expected):
            raise ValueError("inconsistent astronomical limitations")
        if tuple(position.body for position in self.positions) != ("sun", "moon"):
            raise ValueError("canonical body order required")
        for text in (self.jd_tt_hex, self.jd_ut1_hex):
            value = float.fromhex(text)
            if not math.isfinite(value) or value.hex() != text or not 2400000 < value < 2490000:
                raise ValueError("invalid astronomical Julian date")
        return self


class Ephemeris(Protocol):
    def calculate(self, request: EphemerisRequest) -> EphemerisResult: ...
