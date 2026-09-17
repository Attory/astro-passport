# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic comparator adversaries. No private fixtures or private method values."""

import copy
import datetime as dt
import json

import pytest
from test_contracts import response

from conformance.comparator import (
    OLD_MANIFEST,
    OLD_REPOSITORY,
    OLD_SHA,
    Mismatch,
    compare_pair,
    equal,
    leaves,
    legacy_manifest_digest,
    legacy_request,
    rules,
)


def nested(flat):
    result = {}
    for path, value in flat.items():
        parts = path.strip("/").split("/")
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def arrays(value):
        if not isinstance(value, dict):
            return value
        if all(k.isdecimal() for k in value):
            return [arrays(value[str(i)]) for i in range(len(value))]
        return {k: arrays(v) for k, v in value.items()}

    return arrays(result)


def synthetic_pair():
    new = response()
    request = {
        k: v for k, v in new.items() if k in ("contract_version", "profile", "selected_place")
    }
    request.update(schema_version="AstroPassportRequest.v1", civil=new["civil_input"])
    newflat = leaves({"request": request, "response": new, "provenance": new["provenance"]})
    oldflat = {}
    for row in rules():
        if row["side"] != "old":
            continue
        path, kind = row["path"], row["classification"]
        targets = [t for t in row["targets"] if t in newflat]
        value = copy.deepcopy(newflat[targets[0]]) if targets else "synthetic-retained-only"
        if kind == "DERIVED_RECOMPUTE":
            if path.endswith("/manifest_sha256"):
                value = OLD_MANIFEST
            elif path.endswith("/utc"):
                value = dt.datetime.fromisoformat(value).isoformat()
            elif path.startswith("/manifest/"):
                value = "0" * 64
        elif kind == "EXPECTED_IDENTITY_SUBSTITUTION":
            value = (
                OLD_REPOSITORY
                if path.endswith("/source_repository")
                else OLD_SHA
                if path.endswith("/ace_git_sha")
                else "selected-place.v1"
            )
        elif kind == "ERROR_MAPPING":
            value = "resolved"
        elif path.endswith("/reason"):
            value = None
        elif path.endswith("/candidate_ids"):
            value = []
        oldflat[path] = value
    old = nested(oldflat)
    return (
        [copy.deepcopy(old), copy.deepcopy(old)],
        [copy.deepcopy(request), copy.deepcopy(request)],
        [copy.deepcopy(new), copy.deepcopy(new)],
    )


def test_all_classifications_and_exact_success():
    rows = rules()
    assert len([r for r in rows if r["side"] == "old"]) == 185
    assert len([r for r in rows if r["side"] == "new"]) == 125
    old, requests, responses = synthetic_pair()
    counts = compare_pair(
        old,
        requests,
        responses,
        new_revision="0" * 40,
        retained_manifest_sha256=legacy_manifest_digest(old[0]["manifest"]),
    )
    assert sum(counts.values()) == 370


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "null",
        "order",
        "float",
        "decimal",
        "source",
        "limit",
        "manifest",
        "limitations",
        "old_extra",
        "old_missing",
    ],
)
def test_unapproved_changes_fail(mutation):
    old, requests, responses = synthetic_pair()
    digest = legacy_manifest_digest(old[0]["manifest"])
    if mutation == "missing":
        del responses[0]["selected_place"]["attribution"]
    elif mutation == "extra":
        responses[0]["warning"] = None
    elif mutation == "null":
        responses[0]["selected_place"]["attribution"] = "not-null"
    elif mutation == "order":
        responses[0]["bodies"].reverse()
    elif mutation == "float":
        responses[0]["selected_place"]["latitude"] += 1e-15
    elif mutation == "decimal":
        responses[0]["bodies"][0]["decimal_degrees"] = "10.000000001"
    elif mutation == "source":
        responses[0]["provenance"]["source_revision"] = "1" * 40
    elif mutation == "limit":
        responses[0]["selected_place"]["requested_limit"] = 2
    elif mutation == "manifest":
        old[0]["manifest"]["result_sha256"] = "1" * 64
    elif mutation == "limitations":
        responses[0]["civil"]["limitations"].append("unapproved")
    elif mutation == "old_extra":
        old[0]["facts"]["extra"] = None
    elif mutation == "old_missing":
        del old[0]["facts"]["boundary"]["reason"]
    with pytest.raises(ValueError):
        compare_pair(
            old, requests, responses, new_revision="0" * 40, retained_manifest_sha256=digest
        )


def test_legacy_coherence_rejected_before_http():
    old, _, _ = synthetic_pair()
    old[0]["selected"]["raw"]["place_query"] = "different"
    with pytest.raises(Mismatch, match="legacy_query_coherence"):
        legacy_request(old[0]["selected"])


def test_equality_is_not_numeric_epsilon_or_python_bool_coercion():
    assert not equal(0.0, -0.0)
    assert not equal(1, True)
    assert not equal(1, 1.0)
    assert not equal([1, 2], [2, 1])
    assert not equal(None, [])
    assert not equal(float("nan"), float("nan"))
    assert equal(json.loads("0.125"), json.loads("0.125"))


def test_manifest_civil_participant_indices_are_not_collapsed():
    old, requests, responses = synthetic_pair()
    different = "1" * 64
    responses[1]["civil"]["provenance"]["tzif_sha256"] = different
    old[1]["facts"]["civil"]["provenance"]["tzif_sha256"] = different
    for record in old:
        record["manifest"]["civil"][1]["tzif_sha256"] = different
    digest = legacy_manifest_digest(old[0]["manifest"])
    compare_pair(old, requests, responses, new_revision="0" * 40, retained_manifest_sha256=digest)
    responses[1]["civil"]["provenance"]["tzif_sha256"] = "0" * 64
    with pytest.raises(Mismatch):
        compare_pair(
            old, requests, responses, new_revision="0" * 40, retained_manifest_sha256=digest
        )
