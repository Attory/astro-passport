"""Additive signed delivery; no database, member ID, response log or result cache."""

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Literal, Self

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import Field, field_validator, model_validator

from app.contracts import CivilInput, SelectedPlace, Wire
from app.security import private_file
from app.western import WesternRequest, WesternResponse
from passport_codec import build_payload, sign


class PortableCivil(Wire):
    date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    time: str | None
    fold: Literal[0, 1] | None

    @field_validator("fold", mode="before")
    @classmethod
    def exact_fold(cls, value: object) -> object:
        return CivilInput.exact_fold(value)

    @model_validator(mode="after")
    def existing_normalization(self) -> Self:
        if self.time is not None:
            CivilInput.model_validate_json(self.model_dump_json())
        elif not 1900 <= dt.date.fromisoformat(self.date).year <= 2100 or self.fold is not None:
            raise ValueError("Invalid unknown-time input")
        if self.fold is not None and type(self.fold) is not int:
            raise ValueError("Integer fold required")
        return self


class PortableRequest(Wire):
    schema_version: Literal["AstroPassportCompactRequest.v1"]
    contract_version: Literal["2.0.0"]
    profile: Literal["western-synastry-core.v1-mvp"]
    selected_place: SelectedPlace
    civil: PortableCivil

    def precise(self) -> WesternRequest:
        data = self.model_dump(mode="json")
        data.update(schema_version="AstroPassportRequest.v1", contract_version="1.0.0")
        return WesternRequest.model_validate_json(json.dumps(data))


class PortableIssuer:
    """One configured current key; rotation is an explicit operator restart."""

    def __init__(self, path: Path, kid: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", kid):
            raise ValueError("Invalid signing configuration")
        key = serialization.load_pem_private_key(private_file(path), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Ed25519 signing key required")
        self._key = key
        self.kid = kid.encode("ascii")

    async def issue(self, request: PortableRequest, science: Any) -> str:
        data = request.model_dump(mode="json")
        if request.civil.time is None:
            provenance = await science.describe_unknown(request.selected_place)
            payload = build_payload(data, None, None, provenance)
        else:
            legacy, motion = await science.calculate_portable(request.precise())
            checked = WesternResponse.model_validate_json(legacy.model_dump_json())
            payload = build_payload(data, checked.model_dump(mode="json"), motion)
        return sign(payload, self.kid, self._key)
