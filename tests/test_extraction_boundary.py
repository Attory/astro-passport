# SPDX-License-Identifier: AGPL-3.0-only
"""Public source-origin and canonical authority drift checks; no private repo access."""

import ast
import hashlib
import json
from pathlib import Path

from app.build import AAC_BASELINE
from app.science.boundaries import identity as boundary
from app.science.civil import contracts as civil
from app.science.ephemeris.identity import DATA
from scripts.scientific_artifacts import FILES, TZIF


def test_authorized_origins_and_no_cross_repository_runtime():
    record = json.loads(Path("docs/extraction/origins.json").read_bytes())
    assert record["aac_baseline"] == AAC_BASELINE
    assert hashlib.sha256(Path("docs/extraction/origins.json").read_bytes()).hexdigest() == (
        "6aeb2735374829e06d47be4fe3b5c759912fbd9e8a550df65b5c4fcd710e97c2"
    )
    assert len(record["origins"]) == 16
    for row in record["origins"]:
        if row["destination"] is None:
            continue
        raw = Path(row["destination"]).read_text()
        assert row["sha256"] in "\n".join(raw.splitlines()[:4])
        assert row["origin_revision"] == record["reference_revision"]
    for path in Path("app").rglob("*.py"):
        raw = path.read_text()
        assert "/home/soul/" not in raw
        tree = ast.parse(raw)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(("ace.", "ais.", "app.engines.western.synastry"))
            if path.is_relative_to(Path("app/science")):
                imports = (
                    [node.module]
                    if isinstance(node, ast.ImportFrom) and node.module
                    else [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                for module in imports:
                    if module == "app" or module.startswith("app."):
                        assert module in ("app.build", "app.contracts") or module.startswith(
                            "app.science."
                        )


def test_exact_accepted_contract_and_manifest_bytes():
    hashes = {
        "schema.json": "6d02118dd7b5ed16f52e1a67d2b270da53d070afe83c58e934484a0db5e8467c",
        "comparator.json": "7e1215f01916b4e0825491c5374423ea372680eef2feb3fa080676cdcc396fdd",
        "errors.json": "7e942b8e0c48929ebb91b440bbb3fd8a36d123c144ed3af97f4806d7389dc38d",
        "tbb-manifest.json": "2721941b70ba791ab06052972bbe493d7c7758884dea7ba72f339fb939e106e9",
        "semantics.md": "e10218f503ca0c3cf18517f10318a24b5ff30f97ed68a7e163f8982f849f2de8",
        "acep1-profile.md": "a6f289c3e685a4551301773cd920b3bb64884952f9d7571719a15fb6d41f913b",
    }
    for name, digest in hashes.items():
        assert (
            hashlib.sha256((Path("contracts/accepted") / name).read_bytes()).hexdigest() == digest
        )


def test_acquisition_runtime_and_accepted_manifest_pins_agree():
    raw = Path("contracts/accepted/tbb-manifest.json").read_bytes()
    manifest = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == boundary.MANIFEST_SHA256
    assert (
        manifest["archive"]["sha256"]
        == boundary.ARCHIVE_SHA256
        == FILES["boundaries/timezones.geojson.zip"]
    )
    assert (
        manifest["catalog"]["sha256"]
        == boundary.CATALOG_SHA256
        == FILES["boundaries/timezone-names.json"]
    )
    assert manifest["geometry"]["sha256"] == boundary.GEOMETRY_SHA256
    assert TZIF == civil.ARCHIVE_SHA256
    assert FILES["sources/tzdata2026c.tar.gz"] == civil.TZDATA_SHA256
    assert FILES["sources/tzcode2026c.tar.gz"] == civil.TZCODE_SHA256
    for name, _, digest in DATA:
        assert FILES["swiss/" + name] == digest
