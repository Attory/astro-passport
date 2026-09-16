# SPDX-License-Identifier: AGPL-3.0-only
"""Public candidate wire types, not a scientific implementation or ACEP1 encoder."""

import datetime as dt
import math
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class Artifact(Wire):
    identity: str = Field(min_length=1, max_length=128)
    version: Version
    sha256: Digest
    license: str = Field(min_length=1, max_length=128)


class BoundaryFact(Wire):
    outcome: Literal["unique"]
    iana_zone: str = Field(pattern=r"^[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)+$", max_length=128)
    dataset: Artifact
    resolver: Version


class CivilFact(Wire):
    utc: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
    )
    offset_seconds: int = Field(gt=-86400, lt=86400)
    resolution: Literal["unique", "explicit_fold"]
    fold: Literal[0, 1] | None
    tzdata: Artifact
    tzif_sha256: Digest
    resolver: Version

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
    decimal_degrees: str = Field(pattern=r"^[0-9]{1,3}\.[0-9]{9}$")

    @model_validator(mode="after")
    def representation(self) -> Self:
        value = float.fromhex(self.binary64_hex)
        if not math.isfinite(value) or not 0 <= value < 360 or value.hex() != self.binary64_hex:
            raise ValueError("invalid longitude representation")
        if not 0 <= float(self.decimal_degrees) < 360:
            raise ValueError("invalid decimal longitude")
        return self  # Derivation is checked by the future trusted adapter/comparator, not inferred.


class ProvenanceV1(Wire):
    schema_version: Literal["AstroPassportProvenance.v1"]
    source_repository: Literal["https://github.com/Attory/astro-passport"]
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    runtime_identity: Version
    binding: Artifact
    native_version: Version
    native_binary_sha256: Digest
    data_files: tuple[Artifact, ...] = Field(min_length=1, max_length=8)
    ephemeris_flags: Literal[2]
    projection: Literal["geocentric-tropical-apparent-ecliptic-of-date"]
    numerical_policy: Version
    time_scale_policy: Version
    tt_jd_binary64: str = Field(min_length=8, max_length=32)
    ut1_jd_binary64: str = Field(min_length=8, max_length=32)
    limitations: tuple[Version, ...] = Field(min_length=1, max_length=16)

    @field_validator("ephemeris_flags", mode="before")
    @classmethod
    def exact_flags(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("flags require an integer")
        return value

    @field_validator("tt_jd_binary64", "ut1_jd_binary64")
    @classmethod
    def finite_hex(cls, value: str) -> str:
        number = float.fromhex(value)
        if not math.isfinite(number) or number.hex() != value:
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
    bodies: tuple[Longitude, Longitude]
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
]


class ErrorEnvelopeV1(Wire):
    schema_version: Literal["AstroPassportError.v1"] = "AstroPassportError.v1"
    contract_version: Literal["1.0.0"] = "1.0.0"
    code: ErrorCode
