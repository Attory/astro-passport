# SPDX-License-Identifier: AGPL-3.0-only
"""Public synthetic science tests; no private checkout, corpus, credential or external API."""

import asyncio
import datetime as dt
import json
import os
from pathlib import Path

import pytest

from app import build
from app.contracts import AstroPassportRequestV1
from app.science.boundaries.contracts import GeographicCoordinates, TimezoneBoundaryError
from app.science.boundaries.tbb import TBBTimezoneBoundaryResolver
from app.science.civil.contracts import CivilTimeError
from app.science.civil.tzdb import PinnedCivilTimeResolver
from app.science.ephemeris.adapter import SwissEphemeris
from app.science.ephemeris.contracts import EphemerisError, EphemerisRequest
from app.science.errors import ScienceFailure
from app.science.pipeline import PassportScience


def request(
    date: str = "2000-01-15",
    time: str = "12:00",
    fold: int | None = None,
    latitude: float = -33.87,
    longitude: float = 151.21,
) -> AstroPassportRequestV1:
    return AstroPassportRequestV1.model_validate_json(
        json.dumps(
            {
                "schema_version": "AstroPassportRequest.v1",
                "contract_version": "1.0.0",
                "profile": "sun-moon.v1",
                "civil": {"date": date, "time": time, "fold": fold},
                "selected_place": {
                    "schema_version": "SelectedPlaceInput.v1",
                    "provider": "synthetic",
                    "source_id": "public-artificial-geography",
                    "display_name": "Synthetic research case",
                    "latitude": latitude,
                    "longitude": longitude,
                    "attribution": None,
                    "query": "  Exact synthetic query  ",
                    "requested_limit": 1,
                    "selected_index": 0,
                    "result_count": 1,
                },
            }
        )
    )


@pytest.fixture(scope="module")
def science(tmp_path_factory: pytest.TempPathFactory):
    path = os.environ.get("APT_TEST_ARTIFACTS")
    if path is None:
        pytest.skip("explicit public artifacts required; CI scientific job always supplies them")
    folder = tmp_path_factory.mktemp("science-source")
    revision = folder / "revision"
    revision.write_text("a" * 40 + "\n")  # Clearly synthetic build identity, not parity evidence.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(build, "REVISION_FILE", revision)
        yield PassportScience(Path(path))


@pytest.mark.parametrize(
    "date,time,lat,lon,zone,offset",
    [
        ("1976-06-15", "12:00", 59.93, 30.31, "Europe/Moscow", 10800),
        ("1985-02-15", "12:00", 54.92, 82.99, "Asia/Novosibirsk", 25200),
        ("2000-01-15", "12:00", -33.87, 151.21, "Australia/Sydney", 39600),
        ("2000-07-15", "12:00", -33.87, 151.21, "Australia/Sydney", 36000),
    ],
)
def test_public_geography_and_repeatability(science, date, time, lat, lon, zone, offset):
    value = request(date, time, latitude=lat, longitude=lon)
    first = asyncio.run(science.calculate(value))
    second = asyncio.run(science.calculate(value))
    assert first.model_dump_json() == second.model_dump_json()
    assert first.boundary.iana_zone == zone
    assert first.civil.offset_seconds == offset
    assert first.selected_place.query == "  Exact synthetic query  "
    assert [p.body for p in first.bodies] == ["sun", "moon"]
    assert first.provenance.requested_flags == 2


@pytest.mark.parametrize(
    "date,time,fold,code",
    [
        ("2020-04-05", "02:30", None, "civil_ambiguous"),
        ("2020-10-04", "02:30", None, "civil_nonexistent"),
        ("2000-07-15", "12:00", 0, "invalid_fold"),
    ],
)
def test_explicit_civil_failures(science, date, time, fold, code):
    with pytest.raises(ScienceFailure) as failure:
        asyncio.run(science.calculate(request(date, time, fold)))
    assert failure.value.code == code


def test_fold_choices_are_different_instants(science):
    results = [
        asyncio.run(science.calculate(request("2020-04-05", "02:30", fold))) for fold in (0, 1)
    ]
    assert [r.civil.fold for r in results] == [0, 1]
    instants = [dt.datetime.fromisoformat(r.civil.utc) for r in results]
    assert instants[1] - instants[0] == dt.timedelta(hours=1)


@pytest.mark.parametrize(
    "lat,lon,code",
    [
        (0, -140, "boundary_no_match"),
        (90, 0, "boundary_boundary"),
        (-90, 0, "boundary_boundary"),
        (0, 180, "boundary_boundary"),
        (0, -180, "boundary_boundary"),
    ],
)
def test_boundary_ocean_and_seams(science, lat, lon, code):
    with pytest.raises(ScienceFailure) as failure:
        asyncio.run(science.calculate(request(latitude=lat, longitude=lon)))
    assert failure.value.code == code


@pytest.mark.parametrize(
    "date,time",
    [
        ("1900-01-01", "00:00:00.000001"),
        ("2100-12-31", "23:59:59.999999"),
        ("1972-01-01", "00:00"),
        ("2017-01-01", "00:00"),
        ("2000-01-01", "00:00:00.123456"),
    ],
)
def test_supported_edges_microseconds_and_limitations(science, date, time):
    result = asyncio.run(science.calculate(request(date, time)))
    assert result.civil_input.time == dt.time.fromisoformat(time).isoformat(timespec="microseconds")
    assert result.civil.utc.endswith("Z")
    assert result.provenance.limitations[0] == "modelled-ut1-not-measured-earth-orientation"


def test_missing_artifacts_fail_closed(tmp_path):
    for factory, error in [
        (TBBTimezoneBoundaryResolver, TimezoneBoundaryError),
        (PinnedCivilTimeResolver, CivilTimeError),
        (SwissEphemeris, EphemerisError),
    ]:
        with pytest.raises(error):
            factory(tmp_path / "missing")


def test_native_flags_and_timeout_are_explicit(science, monkeypatch):
    import subprocess

    from app.science.ephemeris import adapter

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("isolated worker", 5)

    monkeypatch.setattr(adapter.subprocess, "run", timeout)
    with pytest.raises(EphemerisError) as failure:
        science.natal._ephemeris.calculate(
            EphemerisRequest(utc=dt.datetime(2000, 1, 1, tzinfo=dt.UTC))
        )
    assert failure.value.category == "timeout"


def test_coordinates_reject_nonfinite_and_out_of_range():
    for latitude, longitude in [(91, 0), (0, 181), (float("nan"), 0), (0, float("inf"))]:
        with pytest.raises(ValueError):
            GeographicCoordinates(latitude=latitude, longitude=longitude)
