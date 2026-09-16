# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/timezone/resolution/tzdb.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: f41ecd0159480092709e6573f543e8801bd76926e6f6ea631e4ee7b8240b3398
"""One offline pinned TZif adapter. No ambient tzdata, network, guessing or correction."""

import datetime as dt
import hashlib
import io
import json
import platform
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

from app.science.boundaries.contracts import TimezoneBoundaryError, TimezoneBoundaryResult
from app.science.boundaries.identity import registered_zone_ids, validate_registered_boundary_fact
from app.science.civil.contracts import (
    ARCHIVE_BYTES,
    ARCHIVE_NAME,
    ARCHIVE_SHA256,
    BUILD_POLICY,
    TZCODE_SHA256,
    TZDATA_SHA256,
    CivilTimeError,
    CivilTimeFailure,
    CivilTimeProvenance,
    ResolvedCivilTime,
    limitations_for,
)
from app.science.raw_input import RawBirthInput


def _load_zones(directory: Path) -> dict[str, bytes]:
    try:
        with (directory / ARCHIVE_NAME).open("rb") as stream:
            raw = stream.read(ARCHIVE_BYTES + 1)
    except (OSError, MemoryError):
        raise CivilTimeError(CivilTimeFailure.ARTIFACT_UNAVAILABLE) from None
    if len(raw) != ARCHIVE_BYTES or hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise CivilTimeError(CivilTimeFailure.ARTIFACT_INTEGRITY)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            if (
                manifest["schema_version"] != "tzdb-artifact.v1"
                or manifest["iana_version"] != "2026c"
                or manifest["build_policy"] != BUILD_POLICY
                or manifest["zic_version"] != "zic (tzcode) 2026c"
                or manifest["sources"]
                != {
                    "tzdata2026c.tar.gz": TZDATA_SHA256,
                    "tzcode2026c.tar.gz": TZCODE_SHA256,
                }
                or not isinstance(manifest["zones"], dict)
                or len(manifest["zones"]) != 598
            ):
                raise ValueError
            names = manifest["zones"]
            expected = {"manifest.json", *(f"zoneinfo/{name}" for name in names)}
            if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
                raise ValueError
            if not registered_zone_ids().issubset(names):
                raise ValueError
            zones = {}
            for name, digest in names.items():
                value = archive.read(f"zoneinfo/{name}")
                if not value.startswith(b"TZif") or hashlib.sha256(value).hexdigest() != digest:
                    raise ValueError
                zones[name] = value
            return zones
    except MemoryError:
        raise CivilTimeError(CivilTimeFailure.ARTIFACT_UNAVAILABLE) from None
    except (ValueError, TypeError, KeyError, RecursionError, zipfile.BadZipFile):
        raise CivilTimeError(CivilTimeFailure.ARTIFACT_INVALID) from None


def _utc_candidates(local: dt.datetime, zone: ZoneInfo) -> dict[int, dt.datetime]:
    candidates = {}
    seen = set()
    for fold in (0, 1):
        utc = local.replace(tzinfo=zone, fold=fold).astimezone(dt.UTC)
        replayed = utc.astimezone(zone).replace(tzinfo=None, fold=0)
        if replayed == local and utc not in seen:
            candidates[fold] = utc
            seen.add(utc)
    return candidates


class PinnedCivilTimeResolver:
    def __init__(self, directory: Path) -> None:
        if not isinstance(directory, Path):
            raise CivilTimeError(CivilTimeFailure.INVALID_INPUT)
        if platform.python_implementation() != "CPython" or platform.python_version() != "3.12.14":
            raise CivilTimeError(CivilTimeFailure.UNSUPPORTED_RUNTIME)
        self._zones = _load_zones(directory)

    def verify_result(self, value: ResolvedCivilTime) -> ResolvedCivilTime:
        """Recompute from retained rules, not merely a shape-valid claimed UTC/offset.

        This verifies arithmetic and registered provenance, not ownership/authenticity
        of a submitted birth input or selected geography. No provider query is made.
        """
        try:
            if not isinstance(value, ResolvedCivilTime):
                raise ValueError
            checked = ResolvedCivilTime.model_validate(value.model_dump(warnings=False))
            replayed = self.resolve(
                RawBirthInput(
                    date=checked.local_date, time=checked.local_time, place_query="replay"
                ),
                checked.boundary,
                fold_choice=checked.fold_choice,
            )
            if replayed != checked:
                raise ValueError
            return replayed
        except CivilTimeError as error:
            if error.category in {
                CivilTimeFailure.ARTIFACT_UNAVAILABLE,
                CivilTimeFailure.ARTIFACT_INTEGRITY,
                CivilTimeFailure.ARTIFACT_INVALID,
                CivilTimeFailure.UNSUPPORTED_RUNTIME,
            }:
                raise CivilTimeError(error.category) from None
            raise CivilTimeError(CivilTimeFailure.INVALID_INPUT) from None
        except (ValueError, TypeError):
            raise CivilTimeError(CivilTimeFailure.INVALID_INPUT) from None

    def resolve(
        self,
        raw: RawBirthInput,
        boundary: TimezoneBoundaryResult,
        *,
        fold_choice: int | None = None,
    ) -> ResolvedCivilTime:
        if fold_choice is not None and (type(fold_choice) is not int or fold_choice not in (0, 1)):
            raise CivilTimeError(CivilTimeFailure.INVALID_FOLD)
        try:
            if not isinstance(raw, RawBirthInput):
                raise ValueError
            checked = RawBirthInput.model_validate(raw.model_dump(warnings=False))
            source = validate_registered_boundary_fact(boundary)
            if not 1900 <= checked.date.year <= 2100:
                raise ValueError
        except (ValueError, TypeError, TimezoneBoundaryError):
            raise CivilTimeError(CivilTimeFailure.INVALID_INPUT) from None
        if source.status != "resolved" or source.tzid is None:
            raise CivilTimeError(CivilTimeFailure.UNRESOLVED_ZONE)
        try:
            value = self._zones[source.tzid]
            zone = ZoneInfo.from_file(io.BytesIO(value), key=source.tzid)
            local = dt.datetime.combine(checked.date, checked.time)
            candidates = _utc_candidates(local, zone)
        except (ValueError, KeyError, OSError):
            raise CivilTimeError(CivilTimeFailure.ARTIFACT_INVALID) from None
        if not candidates:
            raise CivilTimeError(CivilTimeFailure.NONEXISTENT_LOCAL_TIME)
        if len(candidates) == 2:
            if fold_choice is None:
                raise CivilTimeError(CivilTimeFailure.AMBIGUOUS_LOCAL_TIME)
            utc = candidates[fold_choice]
        else:
            if fold_choice is not None:
                raise CivilTimeError(CivilTimeFailure.INVALID_FOLD)
            utc = next(iter(candidates.values()))
        offset = local - utc.replace(tzinfo=None)
        return ResolvedCivilTime(
            schema_version="civil-time.v1",
            local_date=checked.date,
            local_time=checked.time,
            boundary=source,
            utc=utc,
            offset_seconds=int(offset.total_seconds()),
            resolution="explicit_fold" if fold_choice is not None else "unique",
            fold_choice=fold_choice,
            limitations=limitations_for(checked.date),
            provenance=CivilTimeProvenance(
                iana_version="2026c",
                build_policy=BUILD_POLICY,
                archive_sha256=ARCHIVE_SHA256,
                tzdata_source_sha256=TZDATA_SHA256,
                tzcode_source_sha256=TZCODE_SHA256,
                tzif_sha256=hashlib.sha256(value).hexdigest(),
                resolver="zoneinfo-roundtrip.v1",
                python_runtime="CPython-3.12.14",
                calendar="proleptic-gregorian",
                utc_convention="posix-no-leap-seconds",
                historical_assurance="pinned-dataset-rules-only",
            ),
        )
