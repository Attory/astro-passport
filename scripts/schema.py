# SPDX-License-Identifier: AGPL-3.0-only
"""Render/check the candidate schema; canonical release still requires AAC approval."""

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


def render() -> bytes:
    schema = TypeAdapter(
        AstroPassportRequestV1 | AstroPassportResponseV1 | ProvenanceV1 | ErrorEnvelopeV1
    ).json_schema()
    schema.update({"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID})
    return (json.dumps(schema, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


if __name__ == "__main__":
    data = render()
    if sys.argv[1:] == ["--check"]:
        assert Path("contracts/astropassport/v1/schema.json").read_bytes() == data
        manifest = json.loads(Path("contracts/manifest.json").read_text())
        assert manifest["sha256"] == hashlib.sha256(data).hexdigest()
        assert manifest["status"] == "candidate_not_released"
    elif not sys.argv[1:]:
        sys.stdout.buffer.write(data)
    else:
        raise SystemExit("usage: python -m scripts.schema [--check]")
