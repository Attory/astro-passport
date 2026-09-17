# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/timezone/boundaries/contracts.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: b51fbae33a42551299db7f3c45d47b824aab64dbeccbea8175eae1ddff46f78f
"""Immutable geographic boundary facts; never civil time, offsets or participant data."""

from enum import StrEnum
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TimezoneBoundaryFailure(StrEnum):
    INVALID_INPUT = "invalid_input"
    ARTIFACT_UNAVAILABLE = "artifact_unavailable"
    ARTIFACT_INTEGRITY = "artifact_integrity"
    ARTIFACT_INVALID = "artifact_invalid"
    UNSUPPORTED_RUNTIME = "unsupported_runtime"


class TimezoneBoundaryError(Exception):
    def __init__(self, category: TimezoneBoundaryFailure) -> None:
        self.category = category
        super().__init__(f"Timezone boundary failure: {category.value}")


class GeographicCoordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    latitude: float = Field(strict=True, ge=-90, le=90, allow_inf_nan=False, repr=False)
    longitude: float = Field(strict=True, ge=-180, le=180, allow_inf_nan=False, repr=False)


class BoundaryProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    dataset: Literal["timezone-boundary-builder"]
    release: Literal["2026c"]
    variant: Literal["comprehensive-no-oceans"]
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    geometry_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolver: Literal["tbb-planar.v1"]
    shapely_version: Literal["2.1.2"]
    geos_version: Literal["3.13.1"]
    numpy_version: Literal["2.5.3"]
    python_version: Literal["3.12.14"]
    execution_target: Literal["linux-amd64"]
    license: Literal["ODbL-1.0"]
    attribution: str = Field(min_length=1, max_length=512)
    license_url: Literal["https://opendatacommons.org/licenses/odbl/1-0/"]


class TimezoneBoundaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    schema_version: Literal["timezone-boundary.v1"]
    coordinates: GeographicCoordinates = Field(repr=False)
    provenance: BoundaryProvenance
    status: Literal["resolved", "boundary", "ambiguous", "no_match"]
    tzid: str | None = Field(default=None, max_length=128, repr=False)
    reason: (
        Literal[
            "polygon_boundary",
            "coordinate_seam_or_pole",
            "multiple_zone_interiors",
            "outside_dataset",
        ]
        | None
    ) = None
    candidate_ids: tuple[str, ...] = Field(default=(), max_length=419, repr=False)

    @field_validator("coordinates", "provenance", mode="before")
    @classmethod
    def copy_nested(cls, value: object) -> object:
        if isinstance(value, BaseModel):
            return value.model_dump(warnings=False)
        return value

    @model_validator(mode="after")
    def coherent_outcome(self) -> Self:
        ids = self.candidate_ids
        if ids != tuple(sorted(set(ids))) or any(not x or len(x) > 128 for x in ids):
            raise ValueError("invalid boundary diagnostics")
        match self.status:
            case "resolved":
                valid = bool(self.tzid) and self.reason is None and not ids
            case "ambiguous":
                valid = (
                    self.tzid is None and self.reason == "multiple_zone_interiors" and len(ids) >= 2
                )
            case "no_match":
                valid = self.tzid is None and self.reason == "outside_dataset" and not ids
            case "boundary":
                valid = self.tzid is None and (
                    (self.reason == "polygon_boundary" and len(ids) >= 1)
                    or (self.reason == "coordinate_seam_or_pole" and not ids)
                )
        if not valid:
            raise ValueError("inconsistent boundary outcome")
        return self


class TimezoneBoundaryResolver(Protocol):
    def resolve(self, coordinates: GeographicCoordinates) -> TimezoneBoundaryResult: ...
