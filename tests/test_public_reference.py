# SPDX-License-Identifier: AGPL-3.0-only
"""Public synthetic golden answers derived by the controlled frozen reference process."""

import asyncio
import copy
import json
from pathlib import Path

import pytest
from test_science import science as science

from app.canonical import passport_content, passport_digest
from app.contracts import AstroPassportRequestV1
from app.science.errors import ScienceFailure


def cases():
    return json.loads(Path("tests/data/public-scientific-reference.v1.json").read_bytes())["cases"]


@pytest.mark.parametrize("case", cases(), ids=lambda case: case["id"])
def test_exact_frozen_scientific_answers(science, case):
    request = AstroPassportRequestV1.model_validate_json(json.dumps(case["request"]))
    if "error" in case:
        with pytest.raises(ScienceFailure) as failure:
            asyncio.run(science.calculate(request))
        assert failure.value.code == case["error"]["code"]
        return
    result = asyncio.run(science.calculate(request))
    expected = copy.deepcopy(case["expected"])
    expected["provenance"]["source_revision"] = "a" * 40
    assert result.model_dump(mode="json") == expected
    assert passport_content(result).hex() == case["acep1_utf8_hex"]
    assert passport_digest(result) == case["acep1_sha256"]
