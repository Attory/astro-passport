# SPDX-License-Identifier: AGPL-3.0-only
"""CP-014 additive scientific MVP profile; no compatibility rules or meanings."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from app.canonical import canonical, scaled
from app.contracts import CivilInput, SelectedPlace, Wire
from app.lahiri import Ayanamsha, LahiriRequest, LahiriResponse, lahiri_content

PROFILE = "western-synastry-core.v1-mvp"
CONTENT_PROFILE = "apt.western-synastry-core-content.v1-mvp"
BODIES = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_north_node",
)
Body = Literal[
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_north_node",
]


class WesternRequest(Wire):
    schema_version: Literal["AstroPassportRequest.v1"]
    contract_version: Literal["1.0.0"]
    profile: Literal["western-synastry-core.v1-mvp"]
    selected_place: SelectedPlace
    civil: CivilInput

    def lahiri_request(self) -> LahiriRequest:
        data = self.model_dump(mode="json")
        data["profile"] = "sun-moon-lahiri.v1-mvp"
        return LahiriRequest.model_validate_json(json.dumps(data))


class WesternLongitude(Ayanamsha):
    body: Body
    requested_flags: Literal[2]
    returned_flags: Literal[2]

    @model_validator(mode="before")
    @classmethod
    def exact_flags(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            type(value.get(k)) is not int for k in ("requested_flags", "returned_flags")
        ):
            raise ValueError("integer flags required")
        return value


class PlacidusAvailable(Wire):
    status: Literal["available"]
    system: Literal["placidus"]
    policy: Literal["swiss-placidus-ut1-tropical-cusps.v1-mvp"]
    flags: Literal[0]
    cusps: tuple[Ayanamsha, ...] = Field(min_length=12, max_length=12)
    ascendant: Ayanamsha
    mc: Ayanamsha

    @field_validator("flags", mode="before")
    @classmethod
    def exact_flag(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("integer flag required")
        return value

    @model_validator(mode="after")
    def ordered(self) -> Self:
        circle = 360_000_000_000
        points = [scaled(c.decimal_degrees, "angle") for c in self.cusps]
        arcs = [(points[(i + 1) % 12] - points[i]) % circle for i in range(12)]
        if any(not 0 < arc < circle // 2 for arc in arcs) or sum(arcs) != circle:
            raise ValueError("invalid ordered cusp cycle")
        if self.ascendant != self.cusps[0] or self.mc != self.cusps[9]:
            raise ValueError("inconsistent house axes")
        return self


class PlacidusUnavailable(Wire):
    status: Literal["unavailable"]
    system: Literal["placidus"]
    policy: Literal["swiss-placidus-ut1-tropical-cusps.v1-mvp"]
    reason: Literal["placidus_undefined"]


class WesternFacts(Wire):
    schema_version: Literal["WesternCoreFacts.v1-mvp"]
    projection: Literal["geocentric-tropical-apparent-ecliptic-of-date"]
    numerical_policy: Literal["binary64-to-decimal-9dp-half-even.v1"]
    bodies: tuple[WesternLongitude, ...] = Field(min_length=11, max_length=11)
    houses: Annotated[PlacidusAvailable | PlacidusUnavailable, Field(discriminator="status")]

    @model_validator(mode="after")
    def body_order(self) -> Self:
        if tuple(p.body for p in self.bodies) != BODIES:
            raise ValueError("invalid body order")
        return self


class WesternResponse(Wire):
    schema_version: Literal["AstroPassportWesternResponse.v1-mvp"]
    contract_version: Literal["1.0.0"]
    profile: Literal["western-synastry-core.v1-mvp"]
    base: LahiriResponse
    western: WesternFacts
    serialization: Literal["astro-passport-western-json.v1-mvp"]
    authenticity: Literal["unsigned-direct-client-only"]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        for old, new in zip(self.base.tropical.bodies, self.western.bodies[:2], strict=True):
            if old.binary64_hex != new.binary64_hex or old.decimal_degrees != new.decimal_degrees:
                raise ValueError("inconsistent tropical facts")
        return self


def western_content(value: WesternResponse) -> bytes:
    checked = WesternResponse.model_validate_json(value.model_dump_json())
    content = json.loads(lahiri_content(checked.base))[2]
    content.update(schema="APTCanonicalWesternContent.v1-mvp", profile=PROFILE)
    content["western"] = {
        "schema": checked.western.schema_version,
        "projection": checked.western.projection,
        "numerical_policy": checked.western.numerical_policy,
        "bodies": [
            {
                "body": b.body,
                "longitude_e9": scaled(b.decimal_degrees, "angle"),
                "requested_flags": b.requested_flags,
                "returned_flags": b.returned_flags,
            }
            for b in checked.western.bodies
        ],
        "houses": checked.western.houses.model_dump(mode="json"),
    }
    houses = checked.western.houses
    if isinstance(houses, PlacidusAvailable):
        content["western"]["houses"] = {
            "status": houses.status,
            "system": houses.system,
            "policy": houses.policy,
            "flags": houses.flags,
            "cusps_e9": [scaled(c.decimal_degrees, "angle") for c in houses.cusps],
            "ascendant_e9": scaled(houses.ascendant.decimal_degrees, "angle"),
            "mc_e9": scaled(houses.mc.decimal_degrees, "angle"),
        }
    return canonical(["ACEP1", CONTENT_PROFILE, content])


def western_digest(value: WesternResponse) -> str:
    return hashlib.sha256(western_content(value)).hexdigest()
