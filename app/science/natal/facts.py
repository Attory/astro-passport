# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/engines/western/natal.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 4075b0d26d814c66cd29db48d85b2fee41d922b1acb7394479c14061c94a18a4
"""Minimal immutable tropical natal facts; not a chart, score or authenticity receipt."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.science.ephemeris.contracts import EphemerisResult


class NatalFacts(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, hide_input_in_errors=True, revalidate_instances="always"
    )

    astronomy: EphemerisResult = Field(repr=False)

    @field_validator("astronomy", mode="before")
    @classmethod
    def copy_validated_astronomy(cls, value: object) -> EphemerisResult:
        if isinstance(value, EphemerisResult):
            value = value.model_dump(warnings=False)
        checked = EphemerisResult.model_validate(value)
        # Revalidate even nested constructed/copied model instances inside a supplied dict.
        return EphemerisResult.model_validate(checked.model_dump(warnings=False))
