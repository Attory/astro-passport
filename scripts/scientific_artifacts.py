# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit public acquisition/build; never called by the scientific service.

Uses the already-reviewed content-addressed source lock. No ACE checkout, credential,
private release or network access is needed after the public cache is populated.
"""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from compliance.bundle import acquire, verify
from scripts.build_tzdb_artifact import build

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "boundaries/timezones.geojson.zip": "7d3f0c5a33b6acd891335c0ad5ba767736b6914cb1a1d68c71921c17ce358948",
    "boundaries/timezone-names.json": "2584551f8c9af23a19bc8b197bf46ad458d9fa8c78d4df056f0408c67fd315ff",
    "sources/tzdata2026c.tar.gz": "e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4",
    "sources/tzcode2026c.tar.gz": "b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8",
    "swiss/sepl_18.se1": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
    "swiss/semo_18.se1": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
}
TZIF = "ff4d43e00b4de4ca68a892c0361a071af3a05583fac315a5f0b6c5490d4a58fa"


def prepare(cache: Path, output: Path, *, offline: bool) -> None:
    entries = json.loads((ROOT / "compliance/source-lock.json").read_bytes())["artifacts"]
    for name, digest in FILES.items():
        entry = next(e for e in entries if e["sha256"] == digest)
        source = acquire(entry, cache, offline)
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            verify(target, digest, entry["bytes"])
            continue
        # Publish verified bytes exclusively; cross-filesystem caches are supported.
        with tempfile.TemporaryDirectory(dir=target.parent) as directory:
            staged = Path(directory) / "verified"
            staged.write_bytes(source.read_bytes())
            verify(staged, digest, entry["bytes"])
            staged.chmod(0o444)
            os.link(staged, target)
    target = output / "civil/tzdb-2026c-packrat-zone-tab.v1.zip"
    if not target.exists() and not target.is_symlink():
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as directory:
            staged = Path(directory) / "built.zip"
            if build(output / "sources", staged) != TZIF:
                raise ValueError("compiled timezone identity differs from approved policy")
            staged.chmod(0o444)
            os.link(staged, target)
    verify(target, TZIF, 470044)
    manifest = ROOT / "contracts/accepted/tbb-manifest.json"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != (
        "2721941b70ba791ab06052972bbe493d7c7758884dea7ba72f339fb939e106e9"
    ):
        raise ValueError("unapproved public boundary manifest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    options = parser.parse_args()
    prepare(options.cache, options.output, offline=options.offline)
    print("Pinned public scientific artifacts verified; no service activated")
