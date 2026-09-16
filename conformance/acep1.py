# SPDX-License-Identifier: AGPL-3.0-only
"""Public independent vectors also exercise the production partial ACEP1 encoder."""

import hashlib

from app.canonical import PROFILE, canonical, scaled, timestamp


def evaluate(case: dict) -> dict:
    try:
        if case["operation"] == "scale":
            value = scaled(case["input"], case["kind"])
        elif case["operation"] == "timestamp":
            value = timestamp(case["input"])
        elif case["operation"] == "canonical":
            value = case["input"]
        else:
            raise ValueError("unknown operation")
        raw = canonical(["ACEP1", PROFILE, value])
        return {"value": value, "utf8_hex": raw.hex(), "sha256": hashlib.sha256(raw).hexdigest()}
    except (ValueError, UnicodeError, KeyError):
        return {"error": "invalid_canonical_input"}
