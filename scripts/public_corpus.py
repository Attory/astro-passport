# SPDX-License-Identifier: AGPL-3.0-only
"""Independently authored artificial inputs, not copied or redacted personal cases.

No astronomical expected value is generated here. Those require the controlled frozen
reference run and independent review. Geometry probes are derived from the pinned public
ODbL dataset, not from a private test fixture.
"""

import argparse
import json
from pathlib import Path

from app.science.boundaries.contracts import GeographicCoordinates
from app.science.boundaries.tbb import TBBTimezoneBoundaryResolver


def selected(date, time, latitude, longitude, fold=None):
    return {
        "raw": {"date": date, "time": time, "place_query": "Public artificial case"},
        "selected_place": {
            "schema_version": "selected-place.v1",
            "candidate": {
                "provider": "synthetic",
                "source_id": "public-artificial-case",
                "display_name": "Artificial research geography",
                "latitude": float(latitude),
                "longitude": float(longitude),
                "attribution": None,
            },
            "search_request": {"query": "Public artificial case", "limit": 1},
            "selected_index": 0,
            "result_count": 1,
        },
        "fold_choice": fold,
    }


def cases(resolver):
    specs = [
        ("spb-1976", "1976-06-15", "12:00", 59.93, 30.31, None),
        ("krasnoobsk-1985", "1985-02-15", "12:00", 54.92, 82.99, None),
        ("sydney-summer", "2000-01-15", "12:00", -33.87, 151.21, None),
        ("sydney-winter", "2000-07-15", "12:00", -33.87, 151.21, None),
        ("sydney-fold-missing", "2020-04-05", "02:30", -33.87, 151.21, None),
        ("sydney-fold-0", "2020-04-05", "02:30", -33.87, 151.21, 0),
        ("sydney-fold-1", "2020-04-05", "02:30", -33.87, 151.21, 1),
        ("sydney-gap", "2020-10-04", "02:30", -33.87, 151.21, None),
        ("unnecessary-fold", "2000-07-15", "12:00", -33.87, 151.21, 0),
        ("ocean-no-match", "2000-01-01", "12:00", 0, -140, None),
        ("north-pole", "2000-01-01", "12:00", 90, 0, None),
        ("south-pole", "2000-01-01", "12:00", -90, 0, None),
        ("dateline-positive", "2000-01-01", "12:00", 0, 180, None),
        ("dateline-negative", "2000-01-01", "12:00", 0, -180, None),
        ("year-minimum", "1900-01-01", "00:00:00.000001", -33.87, 151.21, None),
        ("year-maximum", "2100-12-31", "23:59:59.999999", -33.87, 151.21, None),
        ("utc-previous-date", "2000-01-01", "00:00:00.123456", -33.87, 151.21, None),
        ("utc-next-date", "2000-01-01", "23:59:59.999999", 40.71, -74.0, None),
        ("ut1-proxy-last-day", "1972-01-01", "10:59:59.999999", -33.87, 151.21, None),
        ("1972-policy-seam", "1972-01-01", "11:00:00", -33.87, 151.21, None),
        ("2017-leap-limit", "2017-01-01", "11:00:00", -33.87, 151.21, None),
    ]
    # The first dataset feature/vertex is an exact stored binary64 geometry point.
    geometry = resolver._geometries[0]
    polygon = list(geometry.geoms)[0] if geometry.geom_type == "MultiPolygon" else geometry
    lon, lat = polygon.exterior.coords[0]
    assert resolver.resolve(GeographicCoordinates(latitude=lat, longitude=lon)).status == "boundary"
    specs.append(("certified-dataset-vertex", "2000-01-01", "12:00", lat, lon, None))
    # Independently locate the first deterministic overlap interior, if the approved
    # real dataset has one. Never relabel a boundary point as an ambiguous interior.
    found = False
    for index, geometry in enumerate(resolver._geometries):
        if found:
            break
        for other in sorted(int(i) for i in resolver._tree.query(geometry) if int(i) > index):
            intersection = geometry.intersection(resolver._geometries[other])
            if intersection.is_empty or intersection.area == 0:
                continue
            point = intersection.representative_point()
            outcome = resolver.resolve(GeographicCoordinates(latitude=point.y, longitude=point.x))
            if outcome.status == "ambiguous":
                specs.append(
                    ("certified-dataset-overlap", "2000-01-01", "12:00", point.y, point.x, None)
                )
                found = True
                break
    return [
        {"id": name, "legacy_selected": selected(date, time, lat, lon, fold)}
        for name, date, time, lat, lon, fold in specs
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    resolver = TBBTimezoneBoundaryResolver(args.artifacts / "boundaries")
    corpus = {
        "schema": "apt-public-synthetic-science.v1",
        "origin": "independently-authored-artificial-inputs",
        "cases": cases(resolver),
        "expected_values": "not-generated",
    }
    with args.output.open("x") as output:
        json.dump(corpus, output, ensure_ascii=False, sort_keys=True, indent=2)
        output.write("\n")
    print(f"Public artificial inputs prepared: {len(corpus['cases'])}; no parity claim")
