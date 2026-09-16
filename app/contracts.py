# SPDX-License-Identifier: AGPL-3.0-only
"""AAC-accepted contract 1.0.0 revision 2; wire validation is not authenticity."""

import datetime as dt
import math
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.science.boundaries.identity import pinned_provenance, registered_zone_ids
from app.science.civil.contracts import limitations_for
from app.science.ephemeris.contracts import longitude_decimal

CONTRACT_VERSION = "1.0.0"
SCHEMA_ID = (
    "https://raw.githubusercontent.com/Attory/astro-passport/"
    "astropassport-schema-v1.0.0/contracts/astropassport/v1/schema.json"
)
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[str, Field(min_length=1, max_length=128)]


class Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)

    def __repr_args__(self) -> list[tuple[str, object]]:
        return []  # Birth facts and provenance are not safe repr/logging content.


class SelectedPlace(Wire):
    schema_version: Literal["SelectedPlaceInput.v1"]
    provider: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", max_length=64)
    source_id: str = Field(min_length=1, max_length=256)
    display_name: str = Field(min_length=1, max_length=512)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    attribution: str | None = Field(min_length=1, max_length=512)
    query: str = Field(min_length=1, max_length=256)
    requested_limit: int = Field(ge=1, le=10)
    selected_index: int = Field(ge=0, le=9)
    result_count: int = Field(ge=1, le=10)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if not self.selected_index < self.result_count <= self.requested_limit:
            raise ValueError("invalid selection bounds")
        if any(not v.strip() for v in (self.source_id, self.display_name, self.query)):
            raise ValueError("blank selection value")
        return self


class CivilInput(Wire):
    date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    time: str = Field(pattern=r"^[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?$")
    fold: Literal[0, 1] | None

    @model_validator(mode="after")
    def valid_clock(self) -> Self:
        date = dt.date.fromisoformat(self.date)
        time = dt.time.fromisoformat(self.time)
        if not 1900 <= date.year <= 2100 or time.tzinfo is not None:
            raise ValueError("unsupported civil input")
        return self

    @field_validator("fold", mode="before")
    @classmethod
    def exact_fold(cls, value: object) -> object:
        if value is not None and type(value) is not int:
            raise ValueError("fold requires an integer")
        return value


class AstroPassportRequestV1(Wire):
    schema_version: Literal["AstroPassportRequest.v1"]
    contract_version: Literal["1.0.0"]
    profile: Literal["sun-moon.v1"]
    selected_place: SelectedPlace
    civil: CivilInput


class BoundaryProvenance(Wire):
    dataset: Literal["timezone-boundary-builder"]
    release: Literal["2026c"]
    variant: Literal["comprehensive-no-oceans"]
    manifest_sha256: Digest
    archive_sha256: Digest
    geometry_sha256: Digest
    catalog_sha256: Digest
    resolver: Literal["tbb-planar.v1"]
    shapely_version: Literal["2.1.2"]
    geos_version: Literal["3.13.1"]
    numpy_version: Literal["2.5.3"]
    python_version: Literal["3.12.14"]
    execution_target: Literal["linux-amd64"]
    license: Literal["ODbL-1.0"]
    attribution: str = Field(min_length=1, max_length=512)
    license_url: Literal["https://opendatacommons.org/licenses/odbl/1-0/"]

    @model_validator(mode="after")
    def pinned(self) -> Self:
        if self.model_dump() != pinned_provenance().model_dump():
            raise ValueError("unregistered boundary provenance")
        return self


class BoundaryFact(Wire):
    schema_version: Literal["timezone-boundary.v1"]
    outcome: Literal["unique"]
    iana_zone: str = Field(min_length=1, max_length=128)
    provenance: BoundaryProvenance

    @field_validator("iana_zone")
    @classmethod
    def registered(cls, value: str) -> str:
        if value not in registered_zone_ids():
            raise ValueError("unregistered zone")
        return value


class CivilProvenance(Wire):
    iana_version: Literal["2026c"]
    build_policy: Literal["main-backzone-zone.tab-posix-slim.v1"]
    archive_sha256: Digest
    tzdata_source_sha256: Digest
    tzcode_source_sha256: Digest
    tzif_sha256: Digest
    resolver: Literal["zoneinfo-roundtrip.v1"]
    python_runtime: Literal["CPython-3.12.14"]
    calendar: Literal["proleptic-gregorian"]
    utc_convention: Literal["posix-no-leap-seconds"]
    historical_assurance: Literal["pinned-dataset-rules-only"]


class CivilFact(Wire):
    schema_version: Literal["civil-time.v1"]
    utc: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$")
    offset_seconds: int = Field(gt=-86400, lt=86400)
    resolution: Literal["unique", "explicit_fold"]
    fold: Literal[0, 1] | None
    provenance: CivilProvenance
    limitations: tuple[str, ...] = Field(min_length=1, max_length=2)

    @field_validator("fold", mode="before")
    @classmethod
    def exact_fold(cls, value: object) -> object:
        return CivilInput.exact_fold(value)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        dt.datetime.fromisoformat(self.utc)
        if (self.resolution == "unique") != (self.fold is None):
            raise ValueError("inconsistent fold")
        return self


class Longitude(Wire):
    body: Literal["sun", "moon"]
    binary64_hex: str = Field(min_length=8, max_length=32)
    decimal_degrees: str = Field(pattern=r"^(?:0|[1-9][0-9]?|[12][0-9]{2}|3[0-5][0-9])\.[0-9]{9}$")

    @model_validator(mode="after")
    def representation(self) -> Self:
        value = float.fromhex(self.binary64_hex)
        if not math.isfinite(value) or not 0 <= value < 360 or value.hex() != self.binary64_hex:
            raise ValueError("invalid longitude representation")
        if Decimal(self.decimal_degrees) != longitude_decimal(value):
            raise ValueError("invalid decimal longitude")
        return self


class SunLongitude(Longitude):
    body: Literal["sun"]


class MoonLongitude(Longitude):
    body: Literal["moon"]


class ProvenanceV1(Wire):
    schema_version: Literal["AstroPassportProvenance.v1"]
    source_repository: Literal["https://github.com/Attory/astro-passport"]
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    ephemeris_schema: Literal["ephemeris.v1"]
    adapter: Literal["swiss-isolated.v1"]
    binding: Literal["pysweph-2.10.3.6"]
    library: Literal["2.10.03"]
    binary_sha256: Digest
    binding_source_sha256: Digest
    planet_data_sha256: Digest
    moon_data_sha256: Digest
    data_origin: Literal["DE441"]
    requested_flags: Literal[2]
    returned_flags: tuple[Literal[2], Literal[2]]
    projection: Literal["geocentric-tropical-apparent-ecliptic-of-date"]
    numerical_policy: Literal["binary64-to-decimal-9dp-half-even.v1"]
    time_policy: Literal["pinned-leaps-2016-pre1972-ut1-proxy.v1"]
    delta_t_policy: Literal["swiss-2.10.03-auto-model-tidal-DE441"]
    runtime: Literal["CPython-3.12.14-Linux-x86_64"]
    tt_jd_binary64: str = Field(min_length=8, max_length=32)
    ut1_jd_binary64: str = Field(min_length=8, max_length=32)
    limitations: tuple[str, ...] = Field(min_length=1, max_length=2)

    @field_validator("requested_flags", mode="before")
    @classmethod
    def exact_flags(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("flags require an integer")
        return value

    @field_validator("returned_flags", mode="before")
    @classmethod
    def exact_returned(cls, value: object) -> object:
        if not isinstance(value, list | tuple) or any(type(v) is not int for v in value):
            raise ValueError("flags require integers")
        return tuple(value)

    @field_validator("tt_jd_binary64", "ut1_jd_binary64")
    @classmethod
    def finite_hex(cls, value: str) -> str:
        number = float.fromhex(value)
        if not math.isfinite(number) or number.hex() != value or not 2400000 < number < 2490000:
            raise ValueError("invalid Julian representation")
        return value


class AstroPassportResponseV1(Wire):
    schema_version: Literal["AstroPassportResponse.v1"]
    contract_version: Literal["1.0.0"]
    profile: Literal["sun-moon.v1"]
    selected_place: SelectedPlace
    civil_input: CivilInput
    boundary: BoundaryFact
    civil: CivilFact
    bodies: tuple[SunLongitude, MoonLongitude]
    provenance: ProvenanceV1
    serialization: Literal["astro-passport-json.v1"]
    authenticity: Literal["unsigned-direct-client-only"]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if tuple(body.body for body in self.bodies) != ("sun", "moon"):
            raise ValueError("required body order")
        local = dt.datetime.fromisoformat(self.civil_input.date + "T" + self.civil_input.time)
        utc = dt.datetime.fromisoformat(self.civil.utc).replace(tzinfo=None)
        if utc + dt.timedelta(seconds=self.civil.offset_seconds) != local:
            raise ValueError("inconsistent civil representation")
        if self.civil.fold != self.civil_input.fold:
            raise ValueError("inconsistent fold choice")
        if self.civil_input.time != local.strftime("%H:%M:%S.%f"):
            raise ValueError("response requires normalized local time")
        if self.civil.limitations != limitations_for(local.date()):
            raise ValueError("inconsistent civil limitations")
        expected = ["modelled-ut1-not-measured-earth-orientation"]
        if utc.year < 1972:
            expected.append("pre1972-proleptic-utc-used-as-ut1-proxy")
        elif utc.year >= 2017:
            expected.append("leap-table-frozen-after-2016-not-a-future-prediction")
        if self.provenance.limitations != tuple(expected):
            raise ValueError("inconsistent astronomical limitations")
        return self


ErrorCode = Literal[
    "disabled",
    "unauthorized",
    "forbidden",
    "invalid_request",
    "unsupported_version",
    "too_large",
    "unsupported_media_type",
    "rate_limited",
    "busy",
    "state_unavailable",
    "science_unavailable",
    "timeout",
    "internal_error",
    "boundary_ambiguous",
    "boundary_no_match",
    "civil_ambiguous",
    "civil_nonexistent",
    "artifact_unavailable",
    "artifact_integrity",
    "boundary_boundary",
    "invalid_fold",
    "unsupported_runtime",
    "artifact_invalid",
    "native_failure",
    "fallback_rejected",
    "invalid_result",
]


class ErrorEnvelopeV1(Wire):
    schema_version: Literal["AstroPassportError.v1"]
    contract_version: Literal["1.0.0"]
    code: ErrorCode
