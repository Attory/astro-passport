# SPDX-License-Identifier: AGPL-3.0-only
"""Every accepted failure row is classified; no coarse-to-granular guessing."""

import pytest

from conformance.comparator import Mismatch, compare_error_path, error_rules


def envelope(code):
    return {"schema_version": "AstroPassportError.v1", "contract_version": "1.0.0", "code": code}


DIRECT = [row for row in error_rules()["rows"] if row.get("new_code")]


@pytest.mark.parametrize("row", DIRECT, ids=lambda row: row["path"])
def test_every_direct_error_mapping_accepts_only_exact_code_status(row):
    body = envelope(row["new_code"])
    for status in error_rules()["wire_status"][body["code"]]:
        compare_error_path(row["path"], body, status)
    with pytest.raises(Mismatch, match="ERROR_MAPPING"):
        compare_error_path(row["path"], body, 200)
    wrong = envelope("internal_error" if body["code"] != "internal_error" else "invalid_request")
    with pytest.raises(Mismatch, match="ERROR_MAPPING"):
        compare_error_path(row["path"], wrong, 500)


@pytest.mark.parametrize("outcome", ["boundary", "ambiguous", "no_match"])
def test_geography_dispatch_requires_actual_old_outcome(outcome):
    path = "/errors/CalculationFailure/UNRESOLVED_GEOGRAPHY"
    body = envelope("boundary_" + outcome)
    with pytest.raises(Mismatch, match="retained_stage"):
        compare_error_path(path, body, 422)
    compare_error_path(path, body, 422, retained_boundary_outcome=outcome)
    with pytest.raises(Mismatch, match="retained_stage"):
        compare_error_path(path, body, 422, retained_boundary_outcome="resolved")


def test_collapsed_unavailable_is_not_a_granular_error_without_old_evidence():
    path = "/errors/CalculationFailure/UNAVAILABLE"
    body = envelope("artifact_integrity")
    for evidence in (None, path, "/errors/CalculationFailure/INVALID_INPUT", "/unknown"):
        with pytest.raises(Mismatch, match="retained_stage"):
            compare_error_path(path, body, 500, retained_underlying_error=evidence)
    compare_error_path(
        path, body, 500, retained_underlying_error="/errors/EphemerisFailure/DATA_INTEGRITY"
    )
    with pytest.raises(Mismatch, match="ERROR_MAPPING"):
        compare_error_path(
            path, body, 500, retained_underlying_error="/errors/EphemerisFailure/DATA_UNAVAILABLE"
        )


def test_all_46_rows_have_an_exercised_disposition():
    special = {row["path"] for row in error_rules()["rows"] if not row.get("new_code")}
    assert len(DIRECT) == 41
    assert special == {
        "/errors/CalculationFailure/UNRESOLVED_GEOGRAPHY",
        "/errors/CalculationFailure/UNAVAILABLE",
        "/boundary/status/resolved",
        "/error/person",
        "/error/stage",
    }
    for path in ("/boundary/status/resolved", "/error/person", "/error/stage"):
        with pytest.raises(Mismatch, match="retained_stage"):
            compare_error_path(path, envelope("internal_error"), 500)
    with pytest.raises(Mismatch, match="unclassified_error"):
        compare_error_path("/new/unapproved/error", envelope("internal_error"), 500)


@pytest.mark.parametrize("mutation", ["missing", "null", "extra", "unknown", "wrong_version"])
def test_error_envelope_missing_null_extra_and_unapproved_changes_fail(mutation):
    body = envelope("invalid_request")
    if mutation == "missing":
        del body["code"]
    elif mutation == "null":
        body["code"] = None
    elif mutation == "extra":
        body["warning"] = "unapproved"
    elif mutation == "unknown":
        body["code"] = "unapproved"
    else:
        body["contract_version"] = "2.0.0"
    with pytest.raises(ValueError):
        compare_error_path("/errors/CivilTimeFailure/INVALID_INPUT", body, 422)
