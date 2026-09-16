# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path

from conformance.acep1 import evaluate


def test_independent_synthetic_encoding_vectors() -> None:
    vectors = json.loads(Path("conformance/vectors.json").read_text())
    assert vectors["status"] == "proposed_not_approved"
    assert len({v["id"] for v in vectors["cases"]}) == len(vectors["cases"])
    for case in vectors["cases"]:
        assert evaluate(case) == case["expected"], case["id"]
