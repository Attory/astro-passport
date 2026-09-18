# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/ephemeris/swiss/adapter.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 05b0dd6a7cdc28b03aace66ed7afae34fe9df34301c5fc6b91210a5a88c32d81
"""Immutable verified data plus fresh bounded process: no shared Swiss global state."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.build import require_revision
from app.science.ephemeris.contracts import (
    BodyLongitude,
    EphemerisError,
    EphemerisFailure,
    EphemerisProvenance,
    EphemerisRequest,
    EphemerisResult,
    longitude_decimal,
)
from app.science.ephemeris.identity import BINARY_SHA256, BINDING_SOURCE_SHA256, DATA

_CAPACITY = threading.BoundedSemaphore(2)
_WORKER = Path(__file__).with_name("worker.py")


class SwissEphemeris:
    def __init__(self, directory: Path) -> None:
        if not isinstance(directory, Path):
            raise EphemerisError(EphemerisFailure.INVALID_INPUT)
        try:
            if {path.name for path in directory.iterdir()} != {item[0] for item in DATA}:
                raise EphemerisError(EphemerisFailure.DATA_INTEGRITY)
            contents = []
            for name, size, digest in DATA:
                path = directory / name
                if path.is_symlink() or not path.is_file():
                    raise EphemerisError(EphemerisFailure.DATA_INTEGRITY)
                with path.open("rb") as stream:
                    raw = stream.read(size + 1)
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                    raise EphemerisError(EphemerisFailure.DATA_INTEGRITY)
                contents.append(raw)
            self._contents = tuple(contents)
        except OSError:
            raise EphemerisError(EphemerisFailure.DATA_UNAVAILABLE) from None

    def calculate(self, request: EphemerisRequest) -> EphemerisResult:
        return self._calculate(request, lahiri=False)[0]

    def calculate_lahiri(self, request: EphemerisRequest) -> tuple[EphemerisResult, dict[str, Any]]:
        return self._calculate(request, lahiri=True)

    def _calculate(
        self, request: EphemerisRequest, *, lahiri: bool
    ) -> tuple[EphemerisResult, dict[str, Any]]:
        try:
            if not isinstance(request, EphemerisRequest):
                raise ValueError
            checked = EphemerisRequest.model_validate(request.model_dump(warnings=False))
        except (TypeError, ValueError):
            raise EphemerisError(EphemerisFailure.INVALID_INPUT) from None
        if not _CAPACITY.acquire(blocking=False):
            raise EphemerisError(EphemerisFailure.BUSY)
        try:
            # Only the retained validated bytes enter this fresh 0700 directory. Caller-side
            # mutation, extra leap/delta-T files and ambient search paths cannot influence it.
            with tempfile.TemporaryDirectory(prefix="apt-swiss-") as temporary:
                directory = Path(temporary)
                for (name, _, _), raw in zip(DATA, self._contents, strict=True):
                    (directory / name).write_bytes(raw)
                    (directory / name).chmod(0o400)
                with tempfile.TemporaryFile() as output:
                    result = subprocess.run(
                        [sys.executable, "-I", str(_WORKER)],
                        input=json.dumps(
                            {"utc": checked.utc.isoformat(), **({"lahiri": True} if lahiri else {})}
                        ).encode(),
                        stdout=output,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                        check=False,
                        cwd=directory,
                        env={"PATH": os.defpath, "LC_ALL": "C", "TZ": "UTC"},
                    )
                    output.seek(0)
                    encoded = output.read(8193)
                if result.returncode != 0 or len(encoded) > 8192:
                    raise EphemerisError(EphemerisFailure.NATIVE_FAILURE)
            value = json.loads(encoded)
            if isinstance(value, dict) and set(value) == {"error"}:
                raise EphemerisError(EphemerisFailure(value["error"]))
            extension = value.pop("lahiri") if lahiri else {}
            if not isinstance(extension, dict):
                raise ValueError
            return self._result(checked, value), extension
        except subprocess.TimeoutExpired:
            raise EphemerisError(EphemerisFailure.TIMEOUT) from None
        except OSError:
            raise EphemerisError(EphemerisFailure.NATIVE_FAILURE) from None
        except (ValueError, TypeError, KeyError, OverflowError):
            raise EphemerisError(EphemerisFailure.INVALID_RESULT) from None
        finally:
            _CAPACITY.release()

    @staticmethod
    def _result(request: EphemerisRequest, value: object) -> EphemerisResult:
        if not isinstance(value, dict) or set(value) != {
            "positions",
            "jd_tt_hex",
            "jd_ut1_hex",
            "limitations",
        }:
            raise ValueError
        positions = tuple(
            BodyLongitude.model_validate(
                {
                    "body": body,
                    "longitude": longitude_decimal(float.fromhex(raw)),
                    "binary64_hex": raw,
                }
            )
            for body, raw in zip(("sun", "moon"), value["positions"], strict=True)
        )
        return EphemerisResult.model_validate(
            {
                "utc": request.utc,
                "positions": positions,
                "jd_tt_hex": value["jd_tt_hex"],
                "jd_ut1_hex": value["jd_ut1_hex"],
                "limitations": value["limitations"],
                "provenance": EphemerisProvenance(
                    adapter="swiss-isolated.v1",
                    binding="pysweph-2.10.3.6",
                    library="2.10.03",
                    binary_sha256=BINARY_SHA256,
                    binding_source_sha256=BINDING_SOURCE_SHA256,
                    planet_data_sha256=DATA[0][2],
                    moon_data_sha256=DATA[1][2],
                    data_origin="DE441",
                    requested_flags=2,
                    returned_flags=(2, 2),
                    projection="geocentric-tropical-apparent-ecliptic-of-date",
                    numerical_policy="binary64-to-decimal-9dp-half-even.v1",
                    time_policy="pinned-leaps-2016-pre1972-ut1-proxy.v1",
                    delta_t_policy="swiss-2.10.03-auto-model-tidal-DE441",
                    runtime="CPython-3.12.14-Linux-x86_64",
                    source_repository="https://github.com/Attory/astro-passport",
                    source_revision=require_revision(),
                ),
            }
        )
