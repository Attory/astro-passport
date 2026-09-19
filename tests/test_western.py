# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic Western facts, pinned native reference and unchanged old profiles."""

import asyncio
import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.lahiri import LahiriRequest, lahiri_content
from app.main import create_app
from app.western import BODIES, PlacidusAvailable, WesternRequest, WesternResponse, western_content
from tests.test_api import HEADERS, Spy, payload, provision
from tests.test_science import request
from tests.test_science import science as science_fixture

science = science_fixture


def western_request(**kwargs):
    data = request(**kwargs).model_dump(mode="json")
    data["profile"] = "western-synastry-core.v1-mvp"
    return WesternRequest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "date,latitude,longitude",
    [
        ("1900-01-01", -33.87, 151.21),
        ("1976-06-15", 59.93, 30.31),
        ("1985-02-15", 54.92, 82.99),
        ("2000-01-15", -33.87, 151.21),
        ("2100-12-31", -33.87, 151.21),
    ],
)
def test_all_bodies_houses_repeatability_old_profiles_and_native_reference(
    science, date, latitude, longitude
):
    import swisseph as swe

    value = western_request(date=date, latitude=latitude, longitude=longitude)
    result = asyncio.run(science.calculate_western(value))
    repeated = asyncio.run(science.calculate_western(value))
    old = asyncio.run(science.calculate_lahiri(value.lahiri_request()))
    assert result.model_dump_json() == repeated.model_dump_json()
    assert western_content(result) == western_content(repeated)
    assert result.base.model_dump_json() == old.model_dump_json()
    assert lahiri_content(result.base) == lahiri_content(old)
    assert tuple(b.body for b in result.western.bodies) == BODIES
    houses = result.western.houses
    assert isinstance(houses, PlacidusAvailable)
    assert len(houses.cusps) == 12
    assert houses.ascendant == houses.cusps[0] and houses.mc == houses.cusps[9]
    assert (
        sum(
            float.fromhex(houses.cusps[(i + 1) % 12].binary64_hex)
            < float.fromhex(houses.cusps[i].binary64_hex)
            for i in range(12)
        )
        == 1
    )
    # Direct pinned native API independently checks body IDs and UT1/coordinate wiring.
    # No fabricated expected planetary values, no production cross-service import.
    import os

    swe.set_ephe_path(str(Path(os.environ["APT_TEST_ARTIFACTS"]) / "swiss"))
    swe.set_tid_acc(swe.TIDAL_DE441)
    swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
    try:
        jd_tt = float.fromhex(result.base.tropical.provenance.tt_jd_binary64)
        for identifier, body in zip(
            (
                swe.SUN,
                swe.MOON,
                swe.MERCURY,
                swe.VENUS,
                swe.MARS,
                swe.JUPITER,
                swe.SATURN,
                swe.URANUS,
                swe.NEPTUNE,
                swe.PLUTO,
                swe.TRUE_NODE,
            ),
            result.western.bodies,
            strict=True,
        ):
            native, flags, warning = swe.calc(jd_tt, identifier, 2)
            assert flags == 2 and not warning
            assert native[0].hex() == body.binary64_hex
        cusps, axes = swe.houses_ex(
            float.fromhex(result.base.tropical.provenance.ut1_jd_binary64),
            latitude,
            longitude,
            b"P",
            0,
        )
        assert tuple(v.hex() for v in cusps[1:]) == tuple(c.binary64_hex for c in houses.cusps)
        assert axes[0].hex() == houses.ascendant.binary64_hex
        assert axes[1].hex() == houses.mc.binary64_hex
    finally:
        swe.close()


def test_polar_placidus_is_explicitly_unavailable_not_substituted(science):
    result = asyncio.run(
        science.calculate_western(western_request(latitude=78.22, longitude=15.65))
    )
    assert result.western.houses.model_dump() == {
        "status": "unavailable",
        "system": "placidus",
        "policy": "swiss-placidus-ut1-tropical-cusps.v1-mvp",
        "reason": "placidus_undefined",
    }
    assert len(result.western.bodies) == 11
    assert "porphyry" not in result.model_dump_json().lower()
    assert western_content(result)


def test_closed_models_order_flags_axes_and_representation(science):
    result = asyncio.run(science.calculate_western(western_request()))
    original = result.model_dump(mode="json")
    for mutation in ("order", "extra", "flag", "axis", "cusp_order", "decimal", "sun"):
        value = copy.deepcopy(original)
        facts = value["western"]
        if mutation == "order":
            facts["bodies"].reverse()
        if mutation == "extra":
            facts["compatibility"] = 100
        if mutation == "flag":
            facts["bodies"][2]["returned_flags"] = 4
        if mutation == "axis":
            facts["houses"]["ascendant"] = facts["houses"]["mc"]
        if mutation == "cusp_order":
            facts["houses"]["cusps"].reverse()
        if mutation == "decimal":
            facts["bodies"][2]["decimal_degrees"] = "0.000000000"
        if mutation == "sun":
            facts["bodies"][0].update(binary64_hex=(1.0).hex(), decimal_degrees="1.000000000")
        with pytest.raises(ValueError):
            WesternResponse.model_validate_json(json.dumps(value))
    with pytest.raises(ValueError):
        LahiriRequest.model_validate_json(western_request().model_dump_json())


def test_authenticated_api_dispatch_and_admission(science, tmp_path):
    with TestClient(
        create_app(provision(tmp_path), science), base_url="https://testserver"
    ) as client:
        body = western_request().model_dump_json()
        assert client.post("/v1/passports", content=body).status_code == 401
        response = client.post("/v1/passports", content=body, headers=HEADERS)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert (
            WesternResponse.model_validate_json(response.content).profile
            == "western-synastry-core.v1-mvp"
        )
        bad = json.loads(body)
        bad["profile"] = "western-synastry-core.v2"
        assert client.post("/v1/passports", json=bad, headers=HEADERS).status_code == 422


def test_missing_port_is_not_silent_profile_downgrade(tmp_path):
    spy = Spy()
    body = payload()
    body["profile"] = "western-synastry-core.v1-mvp"
    with TestClient(create_app(provision(tmp_path), spy), base_url="https://testserver") as client:
        response = client.post("/v1/passports", json=body, headers=HEADERS)
        assert response.status_code == 503 and spy.calls == 0


def test_candidate_schema_matches():
    from scripts.western_schema import render

    assert Path("contracts/mvp/western-v1/schema.json").read_bytes() == render()
