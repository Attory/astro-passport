# SPDX-License-Identifier: AGPL-3.0-only
"""Generate only the opt-in CP-010 candidate, never the accepted schema."""

import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from app.lahiri import LahiriRequest, LahiriResponse


def render() -> bytes:
    schema = TypeAdapter(LahiriRequest | LahiriResponse).json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://github.com/Attory/astro-passport/contracts/mvp/lahiri-v1/schema.json"
    schema["title"] = "CP-010 Lahiri MVP candidate; not an AAC canonical release"
    return (json.dumps(schema, sort_keys=True, indent=2) + "\n").encode()


if __name__ == "__main__":
    target = Path("contracts/mvp/lahiri-v1/schema.json")
    if sys.argv[1:] == ["--write"]:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(render())
    elif sys.argv[1:] == ["--check"]:
        assert target.read_bytes() == render()
    else:
        raise SystemExit("use --write or --check")
