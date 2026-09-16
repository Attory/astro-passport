# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/timezone/boundaries/tbb.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 6731dc458cc4cb3776a47de5c970687745c39fc15f8e0434a0ab856b87e5a693
"""One pinned local boundary adapter. No downloads, civil time or geometry repair."""

import hashlib
import io
import json
import platform
import re
import zipfile
from pathlib import Path
from typing import Any, NoReturn

import numpy as np
import shapely
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from app.science.boundaries.contracts import (
    BoundaryProvenance,
    GeographicCoordinates,
    TimezoneBoundaryError,
    TimezoneBoundaryFailure,
    TimezoneBoundaryResult,
)
from app.science.boundaries.identity import ARCHIVE_SHA256 as ARCHIVE_SHA256
from app.science.boundaries.identity import CATALOG_SHA256 as CATALOG_SHA256
from app.science.boundaries.identity import GEOMETRY_SHA256 as GEOMETRY_SHA256
from app.science.boundaries.identity import MANIFEST_SHA256 as MANIFEST_SHA256
from app.science.boundaries.identity import pinned_provenance

ARCHIVE_BYTES = 51_283_605
GEOMETRY_BYTES = 170_230_574
CATALOG_BYTES = 7_734
FEATURE_COUNT = 419
PREFIX = re.compile(r'\s*\{\s*"type"\s*:\s*"FeatureCollection"\s*,\s*"features"\s*:\s*\[')


def _invalid() -> NoReturn:
    raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_INVALID)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _read_verified(path: Path, size: int, digest: str) -> bytes:
    try:
        with path.open("rb") as stream:
            value = stream.read(size + 1)
    except (OSError, MemoryError):
        raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_UNAVAILABLE) from None
    if len(value) != size or hashlib.sha256(value).hexdigest() != digest:
        raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_INTEGRITY)
    return value


def _validate_ring(ring: Any) -> None:
    if not isinstance(ring, list) or len(ring) < 4:
        _invalid()
    for point in ring:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or any(type(value) not in (int, float) for value in point)
        ):
            _invalid()
    coordinates = np.asarray(ring, dtype=np.float64)
    if (
        not np.isfinite(coordinates).all()
        or np.any(np.abs(coordinates[:, 0]) > 180)
        or np.any(np.abs(coordinates[:, 1]) > 90)
        or not np.array_equal(coordinates[0], coordinates[-1])
    ):
        _invalid()
    same_pole = (coordinates[:-1, 1] == coordinates[1:, 1]) & (np.abs(coordinates[:-1, 1]) == 90)
    if np.any((np.abs(np.diff(coordinates[:, 0])) > 180) & ~same_pole):
        _invalid()


def _geometry(value: Any) -> BaseGeometry:
    if not isinstance(value, dict) or set(value) != {"type", "coordinates"}:
        _invalid()
    kind = value["type"]
    if kind not in {"Polygon", "MultiPolygon"}:
        _invalid()
    polygons = [value["coordinates"]] if kind == "Polygon" else value["coordinates"]
    if not isinstance(polygons, list) or not polygons:
        _invalid()
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            _invalid()
        for ring in polygon:
            _validate_ring(ring)
    geometry = shape(value)
    if geometry.is_empty or not geometry.is_valid:
        _invalid()
    return geometry


def _parse_geometry(
    raw: bytes, catalog: frozenset[str]
) -> tuple[tuple[str, ...], tuple[BaseGeometry, ...]]:
    """Decode features separately, retaining original geometry without a second world-sized tree."""
    text = raw.decode("utf-8")
    prefix = PREFIX.match(text)
    if prefix is None:
        _invalid()
    position = prefix.end()
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    names: list[str] = []
    geometries: list[BaseGeometry] = []
    while True:
        while position < len(text) and text[position] in " \t\r\n":
            position += 1
        if text.startswith("]", position):
            if text[position:].strip() != "]}":
                _invalid()
            break
        feature, position = decoder.raw_decode(text, position)
        if (
            not isinstance(feature, dict)
            or set(feature) != {"type", "properties", "geometry"}
            or feature["type"] != "Feature"
            or not isinstance(feature["properties"], dict)
            or set(feature["properties"]) != {"tzid"}
        ):
            _invalid()
        name = feature["properties"]["tzid"]
        if not isinstance(name, str) or name not in catalog or name in names:
            _invalid()
        names.append(name)
        if len(names) > FEATURE_COUNT:
            _invalid()
        geometries.append(_geometry(feature["geometry"]))
        del feature
        while position < len(text) and text[position] in " \t\r\n":
            position += 1
        if position < len(text) and text[position] == ",":
            position += 1
            lookahead = position
            while lookahead < len(text) and text[lookahead] in " \t\r\n":
                lookahead += 1
            if text.startswith("]", lookahead):
                _invalid()
        elif position >= len(text) or text[position] != "]":
            _invalid()
    if set(names) != catalog:
        _invalid()
    return tuple(names), tuple(geometries)


def _outcome(
    coordinates: GeographicCoordinates,
    names: tuple[str, ...],
    geometries: tuple[BaseGeometry, ...],
    tree: shapely.STRtree,
    provenance: BoundaryProvenance,
) -> TimezoneBoundaryResult:
    fields: dict[str, Any] = {
        "schema_version": "timezone-boundary.v1",
        "coordinates": coordinates,
        "provenance": provenance,
    }
    if abs(coordinates.longitude) == 180 or abs(coordinates.latitude) == 90:
        return TimezoneBoundaryResult(**fields, status="boundary", reason="coordinate_seam_or_pole")
    point = Point(coordinates.longitude, coordinates.latitude)
    ids: set[str] = set()
    boundary = False
    for index in tree.query(point):
        geometry = geometries[int(index)]
        if geometry.covers(point):
            ids.add(names[int(index)])
            boundary |= not geometry.contains(point)
    ordered = tuple(sorted(ids))
    if boundary:
        return TimezoneBoundaryResult(
            **fields, status="boundary", reason="polygon_boundary", candidate_ids=ordered
        )
    if len(ordered) > 1:
        return TimezoneBoundaryResult(
            **fields, status="ambiguous", reason="multiple_zone_interiors", candidate_ids=ordered
        )
    if ordered:
        return TimezoneBoundaryResult(**fields, status="resolved", tzid=ordered[0])
    return TimezoneBoundaryResult(**fields, status="no_match", reason="outside_dataset")


def _require_runtime() -> None:
    if (
        shapely.__version__ != "2.1.2"
        or shapely.geos_version_string != "3.13.1"
        or np.__version__ != "2.5.3"
        or platform.python_version() != "3.12.14"
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        raise TimezoneBoundaryError(TimezoneBoundaryFailure.UNSUPPORTED_RUNTIME)


class TBBTimezoneBoundaryResolver:
    """Construct explicitly from owned read-only local artifacts; never from request paths."""

    def __init__(self, directory: Path) -> None:
        if not isinstance(directory, Path):
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.INVALID_INPUT)
        _require_runtime()
        archive = _read_verified(directory / "timezones.geojson.zip", ARCHIVE_BYTES, ARCHIVE_SHA256)
        catalog_bytes = _read_verified(
            directory / "timezone-names.json", CATALOG_BYTES, CATALOG_SHA256
        )
        try:
            with zipfile.ZipFile(io.BytesIO(archive)) as container:
                if container.namelist() != ["combined.json"]:
                    _invalid()
                info = container.getinfo("combined.json")
                if info.file_size != GEOMETRY_BYTES:
                    _invalid()
                raw = container.read(info)
            del archive
            if len(raw) != GEOMETRY_BYTES or hashlib.sha256(raw).hexdigest() != GEOMETRY_SHA256:
                raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_INTEGRITY)
            catalog_value = json.loads(catalog_bytes)
            if (
                not isinstance(catalog_value, list)
                or len(catalog_value) != FEATURE_COUNT
                or any(
                    not isinstance(item, str) or not item or len(item) > 128
                    for item in catalog_value
                )
                or len(set(catalog_value)) != FEATURE_COUNT
            ):
                _invalid()
            self._names, self._geometries = _parse_geometry(raw, frozenset(catalog_value))
            self._tree = shapely.STRtree(self._geometries)
        except TimezoneBoundaryError:
            raise
        except MemoryError:
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_UNAVAILABLE) from None
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            OverflowError,
            RecursionError,
            zipfile.BadZipFile,
            shapely.errors.GEOSException,
        ):
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_INVALID) from None
        # Constants are coupled to the committed manifest by a regression test. No local paths
        # or mutable acquisition dates enter a lookup result.
        self._provenance = pinned_provenance()

    def resolve(self, coordinates: GeographicCoordinates) -> TimezoneBoundaryResult:
        try:
            if not isinstance(coordinates, GeographicCoordinates):
                raise ValueError
            checked = GeographicCoordinates.model_validate(coordinates.model_dump(warnings=False))
        except (ValueError, TypeError):
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.INVALID_INPUT) from None
        try:
            return _outcome(checked, self._names, self._geometries, self._tree, self._provenance)
        except MemoryError:
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_UNAVAILABLE) from None
        except shapely.errors.GEOSException:
            raise TimezoneBoundaryError(TimezoneBoundaryFailure.ARTIFACT_INVALID) from None
