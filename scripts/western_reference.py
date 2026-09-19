# SPDX-License-Identifier: AGPL-3.0-only
"""Generate independently synthetic public wire fixtures from a clean exact producer."""

import argparse
import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

from app import build
from app.science.pipeline import PassportScience
from app.western import WesternRequest, western_content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    # Untracked fixture/tool does not affect runtime; tracked runtime must match HEAD.
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "app", "uv.lock"], check=True)
    with tempfile.TemporaryDirectory(prefix="apt-reference-") as directory:
        path = Path(directory) / "revision"
        path.write_text(revision + "\n")
        build.REVISION_FILE = path
        science = PassportScience(options.artifacts)
        cases = []
        for name, lat, lon in (("sydney", -33.87, 151.21), ("polar", 78.22, 15.65)):
            request = WesternRequest.model_validate_json(
                json.dumps(
                    {
                        "schema_version": "AstroPassportRequest.v1",
                        "contract_version": "1.0.0",
                        "profile": "western-synastry-core.v1-mvp",
                        "civil": {"date": "2000-01-15", "time": "12:00:00.000000", "fold": None},
                        "selected_place": {
                            "schema_version": "SelectedPlaceInput.v1",
                            "provider": "synthetic",
                            "source_id": "public-artificial-geography",
                            "display_name": "Synthetic research case",
                            "latitude": lat,
                            "longitude": lon,
                            "attribution": None,
                            "query": "Exact synthetic query",
                            "requested_limit": 1,
                            "selected_index": 0,
                            "result_count": 1,
                        },
                    }
                )
            )
            response = asyncio.run(science.calculate_western(request))
            cases.append(
                {
                    "id": name,
                    "apt_revision": revision,
                    "origin": "Independent public synthetic geography/time, no personal records",
                    "request": request.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                    "canonical_hex": western_content(response).hex(),
                }
            )
        options.output.write_text(json.dumps({"cases": cases}, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
