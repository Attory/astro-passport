# SPDX-License-Identifier: AGPL-3.0-only
"""Preserve accepted bytes and prove runtime shape conformance without rewriting authority."""

import hashlib
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from app.contracts import (
    SCHEMA_ID,
    AstroPassportRequestV1,
    AstroPassportResponseV1,
    ErrorEnvelopeV1,
    ProvenanceV1,
)

ACCEPTED_SHA256 = "6d02118dd7b5ed16f52e1a67d2b270da53d070afe83c58e934484a0db5e8467c"


def normalized(value: object) -> object:
    if isinstance(value, list):
        return [normalized(child) for child in value]
    if not isinstance(value, dict):
        return value
    result = {k: normalized(v) for k, v in value.items() if k not in ("title", "description")}
    if "enum" in result and len(result["enum"]) == 1:
        result["const"] = result.pop("enum")[0]
    if "const" in result:
        result.pop("type", None)
    if "required" in result:
        result["required"] = sorted(result["required"])
    return result


def render() -> bytes:
    raw = Path("contracts/accepted/schema.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ACCEPTED_SHA256
    accepted = json.loads(raw)
    assert accepted["$id"] == SCHEMA_ID
    schema = TypeAdapter(
        AstroPassportRequestV1 | AstroPassportResponseV1 | ProvenanceV1 | ErrorEnvelopeV1
    ).json_schema()
    assert normalized(schema["anyOf"]) == normalized(accepted["anyOf"])
    for name, definition in schema["$defs"].items():
        assert normalized(definition) == normalized(accepted["$defs"][name]), name
    # Accepted schema includes one unused generic Longitude base as well as the fixed
    # Sun/Moon tuple. Preserve it, but do not make it an alternate success profile.
    assert set(accepted["$defs"]) - set(schema["$defs"]) == {"Longitude"}
    return raw


if __name__ == "__main__":
    data = render()
    if sys.argv[1:] == ["--check"]:
        assert Path("contracts/astropassport/v1/schema.json").read_bytes() == data
        manifest = json.loads(Path("contracts/manifest.json").read_text())
        assert manifest["sha256"] == hashlib.sha256(data).hexdigest()
        assert manifest["status"] == "accepted_semantics_not_released"
    elif not sys.argv[1:]:
        sys.stdout.buffer.write(data)
    else:
        raise SystemExit("usage: python -m scripts.schema [--check]")
