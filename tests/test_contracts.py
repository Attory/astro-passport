# SPDX-License-Identifier: AGPL-3.0-only
"""Candidate shape tests only; synthetic numbers are NOT scientific golden answers."""

import json
from pathlib import Path

import pytest

from app.contracts import AstroPassportResponseV1
from scripts.schema import render


def response() -> dict:
    artifact = {
        "identity": "synthetic",
        "version": "test-only",
        "sha256": "0" * 64,
        "license": "test-only",
    }
    return {
        "schema_version": "AstroPassportResponse.v1",
        "contract_version": "1.0.0",
        "profile": "sun-moon.v1",
        "selected_place": {
            "schema_version": "SelectedPlaceInput.v1",
            "provider": "synthetic",
            "source_id": "synthetic",
            "display_name": "Not a person",
            "latitude": 0.125,
            "longitude": 0.25,
            "attribution": None,
            "query": "test",
            "requested_limit": 1,
            "selected_index": 0,
            "result_count": 1,
        },
        "civil_input": {"date": "2000-01-02", "time": "03:04:05", "fold": None},
        "boundary": {
            "outcome": "unique",
            "iana_zone": "Etc/UTC",
            "dataset": artifact,
            "resolver": "test-only",
        },
        "civil": {
            "utc": "2000-01-02T03:04:05Z",
            "offset_seconds": 0,
            "resolution": "unique",
            "fold": None,
            "tzdata": artifact,
            "tzif_sha256": "0" * 64,
            "resolver": "test-only",
        },
        "bodies": [
            {"body": name, "binary64_hex": value.hex(), "decimal_degrees": f"{value:.9f}"}
            for name, value in [("sun", 10.0), ("moon", 20.0)]
        ],
        "provenance": {
            "schema_version": "AstroPassportProvenance.v1",
            "source_repository": "https://github.com/Attory/astro-passport",
            "source_revision": "0" * 40,
            "runtime_identity": "test-only",
            "binding": artifact,
            "native_version": "test-only",
            "native_binary_sha256": "0" * 64,
            "data_files": [artifact],
            "ephemeris_flags": 2,
            "projection": "geocentric-tropical-apparent-ecliptic-of-date",
            "numerical_policy": "test-only",
            "time_scale_policy": "test-only",
            "tt_jd_binary64": (1.0).hex(),
            "ut1_jd_binary64": (1.0).hex(),
            "limitations": ["not-a-scientific-answer"],
        },
        "serialization": "astro-passport-json.v1",
        "authenticity": "unsigned-direct-client-only",
    }


def test_response_shape_roundtrip_and_hidden_repr() -> None:
    value = AstroPassportResponseV1.model_validate_json(json.dumps(response()))
    assert AstroPassportResponseV1.model_validate_json(value.model_dump_json()) == value
    assert "2000" not in repr(value) and "Not a person" not in str(value)


@pytest.mark.parametrize(
    "case", ["order", "utc", "fold", "nan", "range", "hex", "flags", "unknown", "source"]
)
def test_response_invalid(case: str) -> None:
    data = response()
    if case == "order":
        data["bodies"].reverse()
    if case == "utc":
        data["civil"]["utc"] = "2000-01-02T03:04:06Z"
    if case == "fold":
        data["civil"]["fold"] = 0
    if case == "nan":
        data["bodies"][0]["binary64_hex"] = "nan"
    if case == "range":
        data["bodies"][0]["decimal_degrees"] = "360.000000000"
    if case == "hex":
        data["provenance"]["tt_jd_binary64"] = "1"
    if case == "flags":
        data["provenance"]["ephemeris_flags"] = True
    if case == "unknown":
        data["score"] = 42
    if case == "source":
        data["provenance"]["source_repository"] = "https://private.invalid"
    with pytest.raises(ValueError):
        AstroPassportResponseV1.model_validate_json(json.dumps(data))


def test_schema_is_reproducible_and_references_closed() -> None:
    raw = Path("contracts/astropassport/v1/schema.json").read_bytes()
    assert raw == render()
    schema = json.loads(raw)

    def walk(value: object) -> None:
        if isinstance(value, dict):
            if "$ref" in value:
                ref = value["$ref"]
                assert (
                    ref.startswith("#/$defs/") and ref.removeprefix("#/$defs/") in schema["$defs"]
                )
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
