# SPDX-License-Identifier: AGPL-3.0-only
"""Generate CP-014 opt-in MVP schema, not an AAC canonical schema release."""

import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from app.western import WesternRequest, WesternResponse


def render() -> bytes:
    schema = TypeAdapter(WesternRequest | WesternResponse).json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://github.com/Attory/astro-passport/contracts/mvp/western-v1/schema.json"
    schema["title"] = "CP-014 Western scientific MVP candidate; not an AAC canonical release"
    return (json.dumps(schema, sort_keys=True, indent=2) + "\n").encode()


if __name__ == "__main__":
    target = Path("contracts/mvp/western-v1/schema.json")
    if sys.argv[1:] == ["--write"]:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(render())
    elif sys.argv[1:] == ["--check"]:
        assert target.read_bytes() == render()
    else:
        raise SystemExit("use --write or --check")
