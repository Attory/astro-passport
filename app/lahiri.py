# SPDX-License-Identifier: AGPL-3.0-only
"""CP-010 opt-in MVP candidate; accepted tropical contract bytes remain untouched."""

import hashlib
import json
import math
from decimal import Decimal
from typing import Literal, Self

from pydantic import Field, model_validator

from app.canonical import canonical, passport_content, scaled
from app.contracts import (
    AstroPassportRequestV1,
    AstroPassportResponseV1,
    CivilInput,
    MoonLongitude,
    SelectedPlace,
    Wire,
)
from app.science.ephemeris.contracts import longitude_decimal

PROFILE = "sun-moon-lahiri.v1-mvp"
CONTENT_PROFILE = "apt.sun-moon-lahiri-content.v1-mvp"
POLICY = "swiss-lahiri-apparent-moon.v1-mvp"


class LahiriRequest(Wire):
    schema_version: Literal["AstroPassportRequest.v1"]
    contract_version: Literal["1.0.0"]
    profile: Literal["sun-moon-lahiri.v1-mvp"]
    selected_place: SelectedPlace
    civil: CivilInput

    def tropical_request(self) -> AstroPassportRequestV1:
        data = self.model_dump(mode="json")
        data["profile"] = "sun-moon.v1"
        return AstroPassportRequestV1.model_validate_json(json.dumps(data))


class Ayanamsha(Wire):
    binary64_hex: str = Field(min_length=8, max_length=32)
    decimal_degrees: str = Field(pattern=r"^(?:0|[1-9][0-9]?|[12][0-9]{2}|3[0-5][0-9])\.[0-9]{9}$")

    @model_validator(mode="after")
    def representation(self) -> Self:
        number = float.fromhex(self.binary64_hex)
        if not math.isfinite(number) or not 0 <= number < 360 or number.hex() != self.binary64_hex:
            raise ValueError("invalid angle")
        if Decimal(self.decimal_degrees) != longitude_decimal(number):
            raise ValueError("invalid canonical angle")
        return self


class LahiriFact(Wire):
    schema_version: Literal["LahiriMoonFact.v1-mvp"]
    system: Literal["lahiri"]
    swiss_sidereal_mode: Literal[1]
    policy: Literal["swiss-lahiri-apparent-moon.v1-mvp"]
    numerical_policy: Literal["binary64-to-decimal-9dp-half-even.v1"]
    requested_flags: Literal[65538]
    returned_flags: Literal[65602]
    ayanamsha_flags: Literal[2]
    ayanamsha_kind: Literal["true-including-nutation"]
    ayanamsha: Ayanamsha
    moon: MoonLongitude

    @model_validator(mode="before")
    @classmethod
    def exact_integers(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            type(value.get(key)) is not int
            for key in (
                "swiss_sidereal_mode",
                "requested_flags",
                "returned_flags",
                "ayanamsha_flags",
            )
        ):
            raise ValueError("integer flags required")
        return value


class LahiriResponse(Wire):
    schema_version: Literal["AstroPassportLahiriResponse.v1-mvp"]
    contract_version: Literal["1.0.0"]
    profile: Literal["sun-moon-lahiri.v1-mvp"]
    tropical: AstroPassportResponseV1
    sidereal: LahiriFact
    serialization: Literal["astro-passport-lahiri-json.v1-mvp"]
    authenticity: Literal["unsigned-direct-client-only"]

    @model_validator(mode="after")
    def coherent(self) -> Self:
        expected = (
            float.fromhex(self.tropical.bodies[1].binary64_hex)
            - float.fromhex(self.sidereal.ayanamsha.binary64_hex)
        ) % 360
        actual = float.fromhex(self.sidereal.moon.binary64_hex)
        if abs((expected - actual + 180) % 360 - 180) > 1e-10:
            raise ValueError("inconsistent sidereal projection")
        return self


def lahiri_content(value: LahiriResponse) -> bytes:
    checked = LahiriResponse.model_validate_json(value.model_dump_json())
    content = json.loads(passport_content(checked.tropical))[2]
    content.update(schema="APTCanonicalLahiriContent.v1-mvp", profile=PROFILE)
    content["sidereal"] = {
        "system": "lahiri",
        "swiss_sidereal_mode": 1,
        "policy": POLICY,
        "ayanamsha_kind": "true-including-nutation",
        "ayanamsha_e9": scaled(checked.sidereal.ayanamsha.decimal_degrees, "angle"),
        "moon_longitude_e9": scaled(checked.sidereal.moon.decimal_degrees, "angle"),
    }
    return canonical(["ACEP1", CONTENT_PROFILE, content])


def lahiri_digest(value: LahiriResponse) -> str:
    return hashlib.sha256(lahiri_content(value)).hexdigest()
