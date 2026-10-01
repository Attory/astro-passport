"""Additive velocity facts retain exact approved legacy results and native settings."""

import asyncio
import os
from pathlib import Path

import pytest

from app.science.errors import ScienceFailure
from tests.test_science import science as science_fixture
from tests.test_western import western_request

science = science_fixture


@pytest.mark.parametrize(
    "day,latitude,longitude",
    [
        ("1900-01-01", -33.87, 151.21),
        ("2000-01-15", -33.87, 151.21),
        ("2100-12-31", 78.22, 15.65),
    ],
)
def test_portable_kinematics_matches_native_and_preserves_legacy(science, day, latitude, longitude):
    import swisseph as swe

    request = western_request(date=day, latitude=latitude, longitude=longitude)
    old = asyncio.run(science.calculate_western(request))
    legacy, motion = asyncio.run(science.calculate_portable(request))
    assert legacy.model_dump_json() == old.model_dump_json()
    assert motion is not None
    assert motion[0] == 1 and motion[1] == 258 and motion[2] == [258] * 11
    assert len(motion[3]) == 11
    swe.set_ephe_path(str(Path(os.environ["APT_TEST_ARTIFACTS"]) / "swiss"))
    swe.set_tid_acc(swe.TIDAL_DE441)
    swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
    try:
        jd = float.fromhex(legacy.base.tropical.provenance.tt_jd_binary64)
        for body, expected in zip(
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
            motion[3],
            strict=True,
        ):
            values, flags, warning = swe.calc(jd, body, 258)
            assert flags == 258 and not warning
            assert [value.hex() for value in values] == [value.hex() for value in expected]
    finally:
        swe.close()


def test_portable_uses_existing_dst_normalization_and_rejects_unknown_clock(science):
    value = western_request(date="2024-04-07", time="02:30")
    with pytest.raises(ScienceFailure) as error:
        asyncio.run(science.calculate_portable(value))
    assert error.value.code == "civil_ambiguous"
    first, _ = asyncio.run(
        science.calculate_portable(western_request(date="2024-04-07", time="02:30", fold=0))
    )
    second, _ = asyncio.run(
        science.calculate_portable(western_request(date="2024-04-07", time="02:30", fold=1))
    )
    assert first.base.tropical.civil.utc != second.base.tropical.civil.utc
    # Unknown time is a separate explicit unavailable transport outcome, never
    # admitted into this precise legacy/numerical path with a guessed default.
    with pytest.raises(ValueError):
        western_request(time=None)
