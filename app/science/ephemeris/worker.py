# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/ephemeris/swiss/worker.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: b824816fc9e4b881773c30f7879407e6ebcda3c2f1bee72faff29d1d838bf2f3
"""Private one-request native process. Run only through SwissEphemeris, never a server."""

import datetime as dt
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import platform
import resource
import sys
from pathlib import Path
from typing import Any

# This script is launched with -I and contains no application import or ambient configuration.
# Exact binary identity is checked before importing the extension.
BINARY_SHA256 = "2b3234b6678dfa5666c98e898c16ee7e8c6c8457100e293c24ce679cd4387764"
BINARY_SIZE = 2391504
LEAP_DATES = (
    "1972-06-30",
    "1972-12-31",
    "1973-12-31",
    "1974-12-31",
    "1975-12-31",
    "1976-12-31",
    "1977-12-31",
    "1978-12-31",
    "1979-12-31",
    "1981-06-30",
    "1982-06-30",
    "1983-06-30",
    "1985-06-30",
    "1987-12-31",
    "1989-12-31",
    "1990-12-31",
    "1992-06-30",
    "1993-06-30",
    "1994-06-30",
    "1995-12-31",
    "1997-06-30",
    "1998-12-31",
    "2005-12-31",
    "2008-12-31",
    "2012-06-30",
    "2015-06-30",
    "2016-12-31",
)


class WorkerFailure(Exception):
    pass


def _library() -> Any:
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or platform.python_implementation() != "CPython"
        or platform.python_version() != "3.12.14"
        or importlib.metadata.version("pysweph") != "2.10.3.6"
    ):
        raise WorkerFailure("unsupported_runtime")
    spec = importlib.util.find_spec("swisseph")
    if spec is None or spec.origin is None:
        raise WorkerFailure("unsupported_runtime")
    with Path(spec.origin).open("rb") as stream:
        binary = stream.read(BINARY_SIZE + 1)
    if len(binary) != BINARY_SIZE or hashlib.sha256(binary).hexdigest() != BINARY_SHA256:
        raise WorkerFailure("unsupported_runtime")
    swe = importlib.import_module("swisseph")
    if swe.version != "2.10.03":
        raise WorkerFailure("unsupported_runtime")
    return swe


def run(utc: dt.datetime, directory: Path) -> dict[str, object]:
    swe = _library()
    swe.set_ephe_path(str(directory))
    swe.set_tid_acc(swe.TIDAL_DE441)
    swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)

    def delta(jd: float) -> float:
        value, warning = swe.deltat_ex(jd, 2)
        if warning or not math.isfinite(value):
            raise WorkerFailure("native_failure")
        return float(value)

    hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
    jd_clock = float(swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL))
    limitations = ["modelled-ut1-not-measured-earth-orientation"]
    if utc.year < 1972:
        # Explicit historical approximation, never an unnoticed swe_utc_to_jd fallback.
        jd_ut1 = jd_clock
        jd_tt = jd_ut1 + delta(jd_ut1)
        limitations.append("pre1972-proleptic-utc-used-as-ut1-proxy")
    else:
        leap_count = sum(utc.date() > dt.date.fromisoformat(day) for day in LEAP_DATES)
        jd_tt = jd_clock + (10 + leap_count + 32.184) / 86400
        jd_ut1 = jd_clock
        for _ in range(4):
            jd_ut1 = jd_tt - delta(jd_ut1)
        if utc >= dt.datetime(2017, 1, 1, tzinfo=dt.UTC):
            limitations.append("leap-table-frozen-after-2016-not-a-future-prediction")
    positions = []
    for body in (swe.SUN, swe.MOON):
        values, flags, warning = swe.calc(jd_tt, body, 2)
        if flags != 2:
            raise WorkerFailure("fallback_rejected")
        if warning or len(values) != 6 or not all(math.isfinite(value) for value in values):
            raise WorkerFailure("native_failure")
        positions.append(float(values[0]).hex())
    for index, name in ((0, "sepl_18.se1"), (1, "semo_18.se1")):
        actual_path, start, end, generation = swe.get_current_file_data(index)
        if Path(actual_path) != directory / name or generation != 441 or not start < jd_tt < end:
            raise WorkerFailure("fallback_rejected")
    swe.close()
    return {
        "positions": positions,
        "jd_tt_hex": jd_tt.hex(),
        "jd_ut1_hex": jd_ut1.hex(),
        "limitations": limitations,
    }


def main() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8192, 8192))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        raw = json.loads(sys.stdin.read(257))
        utc = dt.datetime.fromisoformat(raw["utc"])
        if utc.utcoffset() != dt.timedelta(0) or set(raw) != {"utc"}:
            raise WorkerFailure("invalid_input")
        result = run(utc, Path.cwd())
        print(json.dumps(result, separators=(",", ":"), allow_nan=False))
    except WorkerFailure as error:
        print(json.dumps({"error": str(error)}))
    except Exception:
        # Neither native diagnostics nor traceback/local input may escape to service logs.
        print('{"error":"native_failure"}')


if __name__ == "__main__":
    main()
