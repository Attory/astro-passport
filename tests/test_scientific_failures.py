# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic fault injection; synthetic native stubs are not astronomical goldens."""

import asyncio
import datetime as dt
import json
import threading

import pytest
from test_contracts import response
from test_science import request

from app.contracts import AstroPassportResponseV1
from app.science.boundaries.contracts import TimezoneBoundaryError
from app.science.boundaries.tbb import TBBTimezoneBoundaryResolver
from app.science.civil.contracts import ARCHIVE_NAME, CivilTimeError
from app.science.civil.tzdb import PinnedCivilTimeResolver
from app.science.ephemeris import worker
from app.science.ephemeris.adapter import SwissEphemeris
from app.science.ephemeris.contracts import EphemerisError
from app.science.errors import ScienceFailure
from app.science.pipeline import PassportScience


@pytest.mark.parametrize(
    "fault", ["flags", "warning", "nonfinite", "generation", "file", "delta_warning"]
)
def test_native_fallback_and_warning_never_become_success(tmp_path, monkeypatch, fault):
    class Library:
        TIDAL_DE441 = 441
        DELTAT_AUTOMATIC = 0
        GREG_CAL = 1
        SUN = 0
        MOON = 1

        def set_ephe_path(self, path):
            pass

        def set_tid_acc(self, value):
            pass

        def set_delta_t_userdef(self, value):
            pass

        def julday(self, *args):
            return 2451545.0

        def deltat_ex(self, *args):
            return (0.001, "warning" if fault == "delta_warning" else "")

        def calc(self, *args):
            values = (float("nan") if fault == "nonfinite" else 0.0, 0, 0, 0, 0, 0)
            return values, 4 if fault == "flags" else 2, "warning" if fault == "warning" else ""

        def get_current_file_data(self, index):
            path = tmp_path / ("sepl_18.se1" if index == 0 else "semo_18.se1")
            return (
                str(path if fault != "file" else tmp_path / "wrong"),
                2400000,
                2490000,
                440 if fault == "generation" else 441,
            )

        def close(self):
            pass

    monkeypatch.setattr(worker, "_library", lambda: Library())
    with pytest.raises(worker.WorkerFailure):
        worker.run(dt.datetime(2000, 1, 1, tzinfo=dt.UTC), tmp_path)


def test_native_binary_identity_is_checked_before_import(monkeypatch):
    monkeypatch.setattr(worker, "BINARY_SHA256", "0" * 64)
    with pytest.raises(worker.WorkerFailure, match="unsupported_runtime"):
        worker._library()


def test_corrupt_artifact_bytes_are_not_replaced_or_accepted(tmp_path):
    (tmp_path / "timezones.geojson.zip").write_bytes(b"corrupt")
    with pytest.raises(TimezoneBoundaryError) as boundary:
        TBBTimezoneBoundaryResolver(tmp_path)
    assert boundary.value.category == "artifact_integrity"
    (tmp_path / ARCHIVE_NAME).write_bytes(b"corrupt")
    with pytest.raises(CivilTimeError) as civil:
        PinnedCivilTimeResolver(tmp_path)
    assert civil.value.category == "artifact_integrity"
    swiss = tmp_path / "swiss"
    swiss.mkdir()
    (swiss / "sepl_18.se1").write_bytes(b"corrupt")
    (swiss / "semo_18.se1").write_bytes(b"corrupt")
    with pytest.raises(EphemerisError) as native:
        SwissEphemeris(swiss)
    assert native.value.category == "data_integrity"


def test_cancelled_waiters_do_not_release_running_science_slots(monkeypatch):
    service = PassportScience.__new__(PassportScience)
    service._capacity = threading.BoundedSemaphore(2)
    release = threading.Event()
    entered = [threading.Event(), threading.Event()]
    lock = threading.Lock()
    calls = 0
    value = AstroPassportResponseV1.model_validate_json(json.dumps(response()))

    def work(request):
        nonlocal calls
        with lock:
            index = calls
            calls += 1
        entered[index].set()
        assert release.wait(5)
        return value

    monkeypatch.setattr(service, "_calculate", work)

    async def scenario():
        tasks = [asyncio.create_task(service.calculate(request())) for _ in range(2)]
        try:
            for event in entered:
                assert await asyncio.to_thread(event.wait, 2)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            with pytest.raises(ScienceFailure) as failure:
                await service.calculate(request())
            assert failure.value.code == "busy" and calls == 2
        finally:
            release.set()

    asyncio.run(scenario())
    assert service._capacity.acquire(blocking=False)
    assert service._capacity.acquire(blocking=False)
