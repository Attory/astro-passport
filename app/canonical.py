# SPDX-License-Identifier: AGPL-3.0-only
"""Accepted partial ACEP1 encoding; not full NCF/NAD or an authenticity proof."""

import datetime as dt
import hashlib
import json
import math
import re
import unicodedata
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

from app.contracts import AstroPassportResponseV1

PROFILE = "apt.sun-moon-content.v1-proposed"


def scaled(text: str, kind: str) -> int:
    if not re.fullmatch(r"-?[0-9]{1,3}(?:\.[0-9]{1,18})?", text):
        raise ValueError("bounded decimal required")
    number = Decimal(text)
    places, low, high = {
        "latitude": (7, -90, 90),
        "longitude": (7, -180, 180),
        "angle": (9, 0, 360),
    }[kind]
    if not low <= number <= high or (kind == "angle" and number == 360):
        raise ValueError("out of range")
    with localcontext(Context(prec=40, rounding=ROUND_HALF_EVEN)):
        value = int((number * (10**places)).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    if kind == "angle":
        value %= 360_000_000_000
    if kind == "longitude" and value == 1_800_000_000:
        value = -1_800_000_000
    return value


def timestamp(value: str) -> str:
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", value
    ):
        raise ValueError("invalid UTC")
    result = dt.datetime.fromisoformat(value)
    if (
        not dt.datetime(1899, 12, 31, tzinfo=dt.UTC)
        <= result
        < dt.datetime(2101, 1, 2, tzinfo=dt.UTC)
    ):
        raise ValueError("UTC out of range")
    return result.strftime("%Y-%m-%dT%H:%M:%S.") + f"{result.microsecond:06d}Z"


def canonical(value: object) -> bytes:
    """Restricted JCS: safe integers only; NFC pre-transform; never raw binary64 JSON."""

    def normalize(item: object) -> object:
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")
            return unicodedata.normalize("NFC", item)
        if item is None or type(item) is bool:
            return item
        if type(item) in (int, float):
            assert isinstance(item, int | float)
            if isinstance(item, float) and (not math.isfinite(item) or not item.is_integer()):
                raise ValueError("safe integer required")
            if abs(item) > 9_007_199_254_740_991:
                raise ValueError("unsafe integer")
            return int(item)
        if isinstance(item, list):
            return [normalize(v) for v in item]
        if isinstance(item, dict):
            out = {}
            for key, v in item.items():
                if not isinstance(key, str):
                    raise ValueError("string key required")
                k = normalize(key)
                assert isinstance(k, str)
                if k in out:
                    raise ValueError("normalized key collision")
                out[k] = normalize(v)
            return dict(sorted(out.items(), key=lambda pair: pair[0].encode("utf-16-be")))
        raise ValueError("unsupported canonical type")

    return json.dumps(
        normalize(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def passport_content(value: AstroPassportResponseV1) -> bytes:
    """Partial content identity excludes personal labels and execution provenance.

    Decimal(str(float)) is the accepted shortest-roundtrip decimal, not Decimal(float).
    Scientific lookup retained full coordinates before this separate E7 projection.
    """
    checked = AstroPassportResponseV1.model_validate_json(value.model_dump_json())

    def coordinate(number: float, kind: str) -> int:
        # Include subnormal binary64 coordinates: the conformance vector text parser's
        # bounded decimal spelling is not a restriction on valid wire coordinates.
        with localcontext(Context(prec=40, rounding=ROUND_HALF_EVEN)):
            result = int((Decimal(str(number)) * 10**7).quantize(Decimal(1)))
        return -1_800_000_000 if kind == "longitude" and result == 1_800_000_000 else result

    content = {
        "schema": "APTCanonicalSunMoonContent.v1-proposed",
        "profile": checked.profile,
        "numerical_policy": checked.provenance.numerical_policy,
        "utc": timestamp(checked.civil.utc),
        "latitude_e7": coordinate(checked.selected_place.latitude, "latitude"),
        "longitude_e7": coordinate(checked.selected_place.longitude, "longitude"),
        "frame": checked.provenance.projection,
        "bodies": [
            {"body": body.body, "longitude_e9": scaled(body.decimal_degrees, "angle")}
            for body in checked.bodies
        ],
    }
    return canonical(["ACEP1", PROFILE, content])


def passport_digest(value: AstroPassportResponseV1) -> str:
    return hashlib.sha256(passport_content(value)).hexdigest()
