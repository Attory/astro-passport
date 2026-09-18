# SPDX-License-Identifier: AGPL-3.0-only
"""Independently synthetic candidate-profile tests; no real-person examples."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.canonical import passport_content
from app.contracts import AstroPassportRequestV1
from app.lahiri import LahiriRequest, LahiriResponse, lahiri_content, lahiri_digest
from app.main import create_app
from tests.test_api import HEADERS, Spy, payload, provision
from tests.test_science import request
from tests.test_science import science as science_fixture

science = science_fixture


def lahiri_request(**kwargs):
    value = request(**kwargs).model_dump(mode="json")
    value["profile"] = "sun-moon-lahiri.v1-mvp"
    return LahiriRequest.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "date", ["1900-01-01", "1976-06-15", "1985-02-15", "2000-01-15", "2100-12-31"]
)
def test_scientific_profile_repeatability_and_tropical_stability(science, date):
    value = lahiri_request(date=date)
    first = asyncio.run(science.calculate_lahiri(value))
    second = asyncio.run(science.calculate_lahiri(value))
    old = asyncio.run(science.calculate(value.tropical_request()))
    assert first.model_dump_json() == second.model_dump_json()
    assert first.tropical.model_dump_json() == old.model_dump_json()
    assert passport_content(first.tropical) == passport_content(old)
    assert lahiri_content(first) == lahiri_content(second)
    assert lahiri_digest(first) == lahiri_digest(second)
    assert first.sidereal.requested_flags == 65538
    assert first.sidereal.returned_flags == 65602
    assert 0 <= Decimal(first.sidereal.moon.decimal_degrees) < 360
    assert first.sidereal.swiss_sidereal_mode == 1
    assert first.tropical.provenance.library == "2.10.03"


def test_old_profile_rejects_new_shape():
    with pytest.raises(ValueError):
        AstroPassportRequestV1.model_validate_json(lahiri_request().model_dump_json())
    assert lahiri_request().tropical_request() == request()
    for profile in ("sun-moon-lahiri.v2", "lahiri", None):
        value = json.loads(lahiri_request().model_dump_json())
        value["profile"] = profile
        with pytest.raises(ValueError):
            LahiriRequest.model_validate_json(json.dumps(value))


def test_real_moon_near_sidereal_wrap(science):
    # Public synthetic UTC crossing located by bisection using pinned Swiss 2.10.03.
    # Sydney civil clock is UTC+11 on this date. No boundary time is fabricated.
    before = asyncio.run(
        science.calculate_lahiri(lahiri_request(date="2000-01-15", time="00:51:45.160448"))
    )
    after = asyncio.run(
        science.calculate_lahiri(lahiri_request(date="2000-01-15", time="00:51:47.160448"))
    )
    assert Decimal("359.999") < Decimal(before.sidereal.moon.decimal_degrees) < 360
    assert 0 < Decimal(after.sidereal.moon.decimal_degrees) < Decimal("0.001")
    assert lahiri_digest(before) != lahiri_digest(after)


def test_new_api_profile_shares_auth_quota_and_version_admission(tmp_path):
    spy = Spy()

    class Candidate(Spy):
        async def calculate_lahiri(self, value):
            assert isinstance(value, LahiriRequest)
            return await self.calculate(value.tropical_request())

    spy = Candidate()
    body = payload()
    body["profile"] = "sun-moon-lahiri.v1-mvp"
    with TestClient(
        create_app(provision(tmp_path, limit=1), spy), base_url="https://testserver"
    ) as client:
        assert client.post("/v1/passports", json=body).status_code == 401
        assert spy.calls == 0
        result = client.post("/v1/passports", json=body, headers=HEADERS)
        assert result.status_code == 503 and spy.calls == 1
        assert result.headers["cache-control"] == "no-store"
        assert client.post("/v1/passports", json=body, headers=HEADERS).status_code == 429
        assert spy.calls == 1


def test_full_api_new_profile(science, tmp_path):
    with TestClient(
        create_app(provision(tmp_path), science), base_url="https://testserver"
    ) as client:
        response = client.post(
            "/v1/passports", content=lahiri_request().model_dump_json(), headers=HEADERS
        )
        assert response.status_code == 200
        value = LahiriResponse.model_validate_json(response.content)
        assert value.profile == "sun-moon-lahiri.v1-mvp"
        for field in ("system", "policy", "swiss_sidereal_mode", "returned_flags"):
            raw = value.model_dump(mode="json")
            raw["sidereal"][field] = "unapproved"
            with pytest.raises(ValueError):
                LahiriResponse.model_validate_json(json.dumps(raw))
        raw = value.model_dump(mode="json")
        raw["sidereal"]["swiss_sidereal_mode"] = True
        with pytest.raises(ValueError):
            LahiriResponse.model_validate_json(json.dumps(raw))
        raw = value.model_dump(mode="json")
        raw["sidereal"]["moon"] = {
            "body": "moon",
            "binary64_hex": (1.0).hex(),
            "decimal_degrees": "1.000000000",
        }
        with pytest.raises(ValueError):
            LahiriResponse.model_validate_json(json.dumps(raw))


def test_candidate_schema_generation():
    from scripts.lahiri_schema import render

    assert Path("contracts/mvp/lahiri-v1/schema.json").read_bytes() == render()
