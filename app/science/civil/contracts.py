# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/timezone/resolution/contracts.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 57623b8cb3895f5a5b0c246f25093fb597e97328ba1342b97d59c10fa53879e2
"""Immutable pinned-rule civil-time results, distinct from geography and astronomy."""

import datetime as dt
from enum import StrEnum
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.science.boundaries.contracts import TimezoneBoundaryResult
from app.science.raw_input import RawBirthInput

BUILD_POLICY: Final = "main-backzone-zone.tab-posix-slim.v1"
ARCHIVE_NAME = "tzdb-2026c-packrat-zone-tab.v1.zip"
ARCHIVE_SHA256 = "ff4d43e00b4de4ca68a892c0361a071af3a05583fac315a5f0b6c5490d4a58fa"
ARCHIVE_BYTES = 470_044
TZDATA_SHA256 = "e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4"
TZCODE_SHA256 = "b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8"


class CivilTimeFailure(StrEnum):
    INVALID_INPUT = "invalid_input"
    UNRESOLVED_ZONE = "unresolved_zone"
    INVALID_FOLD = "invalid_fold"
    AMBIGUOUS_LOCAL_TIME = "ambiguous_local_time"
    NONEXISTENT_LOCAL_TIME = "nonexistent_local_time"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    ARTIFACT_INTEGRITY = "artifact_integrity"
    ARTIFACT_INVALID = "artifact_invalid"
    UNSUPPORTED_RUNTIME = "unsupported_runtime"


class CivilTimeError(Exception):
    def __init__(self, category: CivilTimeFailure) -> None:
        self.category = category
        super().__init__(f"Civil time failure: {category.value}")


class CivilTimeProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    iana_version: Literal["2026c"]
    build_policy: Literal["main-backzone-zone.tab-posix-slim.v1"]
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tzdata_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tzcode_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tzif_sha256: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)
    resolver: Literal["zoneinfo-roundtrip.v1"]
    python_runtime: Literal["CPython-3.12.14"]
    calendar: Literal["proleptic-gregorian"]
    utc_convention: Literal["posix-no-leap-seconds"]
    historical_assurance: Literal["pinned-dataset-rules-only"]


def limitations_for(date: dt.date) -> tuple[str, ...]:
    values = ["modern-geography-not-date-specific-jurisdiction"]
    if date < dt.date(1970, 1, 1):
        values.append("pre1970-records-have-limited-assurance")
    if date > dt.date(2026, 7, 8):
        values.append("post-release-rules-are-not-a-prediction-guarantee")
    return tuple(values)


class ResolvedCivilTime(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    schema_version: Literal["civil-time.v1"]
    local_date: dt.date = Field(repr=False)
    local_time: dt.time = Field(repr=False)
    boundary: TimezoneBoundaryResult = Field(repr=False)
    utc: dt.datetime = Field(repr=False)
    offset_seconds: int = Field(strict=True, gt=-86400, lt=86400, repr=False)
    resolution: Literal["unique", "explicit_fold"] = Field(repr=False)
    fold_choice: int | None = Field(default=None, strict=True, ge=0, le=1, repr=False)
    provenance: CivilTimeProvenance
    limitations: tuple[str, ...] = Field(repr=False)

    @field_validator("boundary", "provenance", mode="before")
    @classmethod
    def copy_nested(cls, value: object) -> object:
        return value.model_dump(warnings=False) if isinstance(value, BaseModel) else value

    @field_validator("local_date", mode="before")
    @classmethod
    def date_shape(cls, value: object) -> object:
        return RawBirthInput.require_civil_date_input(value)

    @field_validator("local_time", mode="before")
    @classmethod
    def time_shape(cls, value: object) -> object:
        return RawBirthInput.require_civil_time_input(value)

    @field_validator("utc", mode="before")
    @classmethod
    def utc_shape(cls, value: object) -> object:
        if not isinstance(value, str | dt.datetime):
            raise ValueError("invalid UTC representation")
        return value

    @model_validator(mode="after")
    def coherent(self) -> Self:
        RawBirthInput.require_naive_local_time(self.local_time)
        if not 1900 <= self.local_date.year <= 2100 or self.boundary.status != "resolved":
            raise ValueError("invalid civil-time source")
        if self.utc.utcoffset() != dt.timedelta(0) or self.utc.fold != 0:
            raise ValueError("UTC must have zero offset")
        local = dt.datetime.combine(self.local_date, self.local_time)
        if self.utc.replace(tzinfo=None) + dt.timedelta(seconds=self.offset_seconds) != local:
            raise ValueError("inconsistent civil-time result")
        if (self.resolution == "unique") != (self.fold_choice is None):
            raise ValueError("inconsistent fold resolution")
        if self.limitations != limitations_for(self.local_date):
            raise ValueError("missing civil-time limitations")
        return self
