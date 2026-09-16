# SPDX-License-Identifier: AGPL-3.0-only
"""Executable accepted leaf map; isolated migration tooling, never service imports.

Inputs are retained outputs from two separate processes. This tool has no access to ACE
modules, private repositories, credentials or a network. It never emits scientific values.
The caller must retain and verify the unchanged old pair manifest privately. Downstream
ACE pair-digest recomputation after client cutover is explicitly not an APT fingerprint.
"""

import datetime as dt
import hashlib
import json
import math
import re
import struct
from collections import Counter
from decimal import Decimal
from pathlib import Path

from app.canonical import passport_content
from app.contracts import AstroPassportRequestV1, AstroPassportResponseV1, ErrorEnvelopeV1
from app.science.ephemeris.contracts import longitude_decimal

MAP_SHA = "7e1215f01916b4e0825491c5374423ea372680eef2feb3fa080676cdcc396fdd"
OLD_SHA = "18a3776bc1ab1dc52212b4de48a0df36709d72d2"
OLD_REPOSITORY = "https://github.com/Attory/astrological-compatibility-engine"
NEW_REPOSITORY = "https://github.com/Attory/astro-passport"
OLD_MANIFEST = "621f019c37089c68f7d9f48529965a7e697fd61d5112493966096d0ea74da3a9"
NEW_MANIFEST = "2721941b70ba791ab06052972bbe493d7c7758884dea7ba72f339fb939e106e9"
CLASSES = frozenset(
    {
        "EXACT_EQUAL",
        "EXPECTED_IDENTITY_SUBSTITUTION",
        "DERIVED_RECOMPUTE",
        "DELIVERY_METADATA_ONLY",
        "INTENTIONALLY_ABSENT",
        "ERROR_MAPPING",
        "NOT_COMPARABLE_WITH_REASON",
    }
)


class Mismatch(ValueError):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__("scientific comparison failed: " + category)


def rules() -> list[dict]:
    raw = (Path(__file__).resolve().parents[1] / "contracts/accepted/comparator.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAP_SHA:
        raise Mismatch("classification_integrity")
    rows = json.loads(raw)["rows"]
    identities = [(r["side"], r["path"]) for r in rows]
    if len(set(identities)) != 310 or len(rows) != 310:
        raise Mismatch("duplicate_classification")
    if any(r["classification"] not in CLASSES for r in rows):
        raise Mismatch("unclassified")
    return rows


def leaves(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        if not value or any(not isinstance(k, str) or "/" in k or "~" in k for k in value):
            raise Mismatch("shape")
        result = {}
        for key, child in value.items():
            result.update(leaves(child, prefix + "/" + key))
        return result
    if isinstance(value, list) and any(isinstance(v, dict) for v in value):
        if not all(isinstance(v, dict) for v in value):
            raise Mismatch("shape")
        result = {}
        for index, child in enumerate(value):
            result.update(leaves(child, prefix + "/" + str(index)))
        return result
    return {prefix: value}


def equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, float):
        return math.isfinite(left) and struct.pack("!d", left) == struct.pack("!d", right)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def legacy_manifest_digest(value: dict) -> str:
    """Declared ace-calculation-json.v1 bytes, not ACEP1 and not an APT digest."""
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def legacy_request(selected: dict) -> dict:
    """Map already legacy-validated values. Never repair query incoherence in transit."""
    raw, place = selected["raw"], selected["selected_place"]
    if raw["place_query"] != place["search_request"]["query"]:
        raise Mismatch("legacy_query_coherence")
    candidate = place["candidate"]
    value = {
        "schema_version": "AstroPassportRequest.v1",
        "contract_version": "1.0.0",
        "profile": "sun-moon.v1",
        "civil": {
            "date": raw["date"],
            "time": dt.time.fromisoformat(raw["time"]).isoformat(timespec="microseconds"),
            "fold": selected["fold_choice"],
        },
        "selected_place": {
            "schema_version": "SelectedPlaceInput.v1",
            **candidate,
            "query": place["search_request"]["query"],
            "requested_limit": place["search_request"]["limit"],
            "selected_index": place["selected_index"],
            "result_count": place["result_count"],
        },
    }
    AstroPassportRequestV1.model_validate_json(json.dumps(value))
    return value


def compare_pair(
    old: list[dict],
    requests: list[dict],
    responses: list[dict],
    *,
    new_revision: str,
    retained_manifest_sha256: str,
) -> dict[str, int]:
    """Both participants are required: manifest civil[0] and civil[1] are never collapsed.

    retained_manifest_sha256 comes from separately validated immutable OLD reference
    evidence, not an invented new digest. New ACE-owned composed digests remain a later
    client-cutover gate, exactly as classified in the accepted map.
    """
    if (
        len(old) != 2
        or len(requests) != 2
        or len(responses) != 2
        or not re.fullmatch(r"[0-9a-f]{40}", new_revision)
    ):
        raise Mismatch("shape")
    rows = rules()
    old_rows = [r for r in rows if r["side"] == "old"]
    expected_old = {r["path"] for r in old_rows}
    expected_new = {
        r["path"] for r in rows if r["side"] == "new" and not r["path"].startswith("/error/")
    }
    new_flat = []
    for request, response in zip(requests, responses, strict=True):
        AstroPassportRequestV1.model_validate_json(json.dumps(request))
        AstroPassportResponseV1.model_validate_json(json.dumps(response))
        flat = leaves(
            {"request": request, "response": response, "provenance": response["provenance"]}
        )
        if set(flat) != expected_new:
            raise Mismatch("new_leaf_coverage")
        if response["provenance"]["source_revision"] != new_revision:
            raise Mismatch("EXPECTED_IDENTITY_SUBSTITUTION")
        new_flat.append(flat)
    counts: Counter[str] = Counter()
    for participant, record in enumerate(old):
        flat = leaves(record)
        if set(flat) != expected_old:
            raise Mismatch("old_leaf_coverage")
        if legacy_manifest_digest(record["manifest"]) != retained_manifest_sha256:
            raise Mismatch("retained_manifest_changed")
        if legacy_request(record["selected"]) != requests[participant]:
            raise Mismatch("legacy_request_mapping")
        for row in old_rows:
            path, category = row["path"], row["classification"]
            value = flat[path]
            counts[category] += 1
            index = int(path.split("/")[3]) if path.startswith("/manifest/civil/") else participant
            targets = [t for t in row["targets"] if not t.startswith("/error/")]
            wanted = value
            if category == "EXACT_EQUAL":
                pass
            elif category == "EXPECTED_IDENTITY_SUBSTITUTION":
                if path.endswith("/schema_version"):
                    if value != "selected-place.v1":
                        raise Mismatch(category)
                    wanted = "SelectedPlaceInput.v1"
                elif path.endswith("/source_repository"):
                    if value != OLD_REPOSITORY:
                        raise Mismatch(category)
                    wanted = NEW_REPOSITORY
                elif path.endswith("/ace_git_sha"):
                    if value != OLD_SHA:
                        raise Mismatch(category)
                    wanted = new_revision
                else:
                    raise Mismatch("unimplemented_rule")
            elif category == "DERIVED_RECOMPUTE":
                if path.endswith("/manifest_sha256"):
                    if value != OLD_MANIFEST:
                        raise Mismatch(category)
                    wanted = NEW_MANIFEST
                elif path.endswith(("/time", "/local_time")):
                    clock = dt.time.fromisoformat(value)
                    if clock.tzinfo is not None or clock.fold:
                        raise Mismatch(category)
                    wanted = clock.isoformat(timespec="microseconds")
                elif path.endswith("/utc"):
                    instant = dt.datetime.fromisoformat(value)
                    if instant.utcoffset() != dt.timedelta(0) or instant.fold:
                        raise Mismatch(category)
                    wanted = instant.isoformat(timespec="microseconds").replace("+00:00", "Z")
                elif path.endswith("/longitude"):
                    raw = float.fromhex(flat[path.rsplit("/", 1)[0] + "/binary64_hex"])
                    number = Decimal(value)
                    if number != longitude_decimal(raw):
                        raise Mismatch(category)
                    wanted = format(number if number else 0, ".9f")
                elif path.startswith("/manifest/") and path.endswith("_sha256") and not targets:
                    # Classified deferred downstream digests: exact OLD manifest retention
                    # is checked above. No new ACE pair digest exists before client cutover.
                    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                        raise Mismatch(category)
                else:
                    raise Mismatch("unimplemented_rule")
            elif category == "ERROR_MAPPING":
                if value != "resolved":
                    raise Mismatch(category)
                wanted = "unique"
            elif category == "INTENTIONALLY_ABSENT":
                if path.endswith("/reason") and value is not None:
                    raise Mismatch(category)
                if path.endswith("/candidate_ids") and value != []:
                    raise Mismatch(category)
                # Other explicitly named wrapper/private-context fields remain in the
                # immutable old record, not in a new public envelope. No generic ignore.
                if targets:
                    raise Mismatch("unimplemented_rule")
            elif category == "NOT_COMPARABLE_WITH_REASON":
                if not row["rule"] or targets or not path.startswith("/manifest/"):
                    raise Mismatch("unimplemented_rule")
            else:
                raise Mismatch("unimplemented_rule")
            if any(not equal(wanted, new_flat[index][target]) for target in targets):
                raise Mismatch(category)
    # Every new leaf is either linked by the map or a validated explicit envelope constant.
    for row in rows:
        if row["side"] == "new" and not row["path"].startswith("/error/"):
            if not row["sources"] and row["classification"] != "EXPECTED_IDENTITY_SUBSTITUTION":
                raise Mismatch("unclassified_new_value")
    return dict(counts)


def compare_error(source_enum: str, member: str, body: dict, status: int) -> None:
    ErrorEnvelopeV1.model_validate_json(json.dumps(body))
    path = Path(__file__).resolve().parents[1] / "contracts/accepted/errors.json"
    data = json.loads(path.read_bytes())
    choices = [r for r in data["rows"] if r["path"] == f"/errors/{source_enum}/{member}"]
    if len(choices) != 1 or "new_code" not in choices[0]:
        raise Mismatch("error_requires_retained_stage_evidence")
    if body["code"] != choices[0]["new_code"] or status not in data["wire_status"][body["code"]]:
        raise Mismatch("ERROR_MAPPING")


def canonical_agrees(old_response_projection: dict, response: dict) -> bool:
    """Compare partial ACEP1 from independently mapped old facts, never reuse new values."""
    old_value = AstroPassportResponseV1.model_validate_json(json.dumps(old_response_projection))
    new_value = AstroPassportResponseV1.model_validate_json(json.dumps(response))
    return passport_content(old_value) == passport_content(new_value)


def project_reference(record: dict, *, new_revision: str) -> dict:
    """Public-safe scientific expectation projection from retained old scientific facts.

    Only classified /response targets are exported. No private manifest leaf, pair
    methodology, context, wrapper or history is emitted. This is a reference derivation
    tool, never an alternate service implementation or a bypass of HTTPS parity.
    """
    flat = leaves(record)
    projected = {}
    constants = {
        "/response/schema_version": "AstroPassportResponse.v1",
        "/response/contract_version": "1.0.0",
        "/response/profile": "sun-moon.v1",
        "/response/authenticity": "unsigned-direct-client-only",
        "/response/serialization": "astro-passport-json.v1",
        "/response/provenance/schema_version": "AstroPassportProvenance.v1",
    }
    for row in rules():
        path = row["path"]
        if row["side"] != "new" or not path.startswith("/response/"):
            continue
        sources = [s for s in row["sources"] if not s.startswith("/manifest/")]
        value = flat[sources[0]] if sources else constants[path]
        if path.endswith("/source_repository"):
            value = NEW_REPOSITORY
        elif path.endswith("/source_revision"):
            value = new_revision
        elif path == "/response/selected_place/schema_version":
            value = "SelectedPlaceInput.v1"
        elif path == "/response/boundary/outcome":
            if value != "resolved":
                raise Mismatch("expected_success")
            value = "unique"
        elif path.endswith("/manifest_sha256"):
            if value != OLD_MANIFEST:
                raise Mismatch("reference_manifest_identity")
            value = NEW_MANIFEST
        elif path == "/response/civil_input/time":
            value = dt.time.fromisoformat(value).isoformat(timespec="microseconds")
        elif path == "/response/civil/utc":
            instant = dt.datetime.fromisoformat(value)
            if instant.utcoffset() != dt.timedelta(0):
                raise Mismatch("reference_utc")
            value = instant.isoformat(timespec="microseconds").replace("+00:00", "Z")
        elif path.endswith("/decimal_degrees"):
            number = Decimal(value)
            value = format(number if number else 0, ".9f")
        parts = path.split("/")[2:]
        current = projected
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    projected["bodies"] = [projected["bodies"]["0"], projected["bodies"]["1"]]
    AstroPassportResponseV1.model_validate_json(json.dumps(projected))
    return projected
