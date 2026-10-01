"""Generate the frozen runtime wheel licence inventory without importing packages."""

import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

from compliance.bundle import acquire


def inventory(root: Path, cache: Path) -> list[dict]:
    packages = {p["name"]: p for p in tomllib.loads((root / "uv.lock").read_text())["package"]}
    source = json.loads((root / "compliance/source-lock.json").read_text())["artifacts"]
    names, pending = set(), ["astro-passport"]
    while pending:
        name = pending.pop()
        if name in names:
            continue
        names.add(name)
        pending.extend(d["name"] for d in packages[name].get("dependencies", []))
    result = []
    for name in sorted(names - {"astro-passport"}):
        package = packages[name]
        wheels = [
            e
            for e in source
            if e["component"] == name + "=" + package["version"] and e["name"].endswith(".whl")
        ]
        if len(wheels) != 1:
            raise ValueError("One exact runtime wheel required: " + name)
        entry = wheels[0]
        with zipfile.ZipFile(acquire(entry, cache, offline=True)) as wheel:
            meta = Parser().parsestr(
                wheel.read(
                    next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
                ).decode()
            )
            expression = meta.get("License-Expression") or meta.get("License")
            if not expression or len(expression) > 200:
                expression = "See original retained upstream notices; metadata is not a compact SPDX expression"
            notices = {
                n: hashlib.sha256(wheel.read(n)).hexdigest()
                for n in wheel.namelist()
                if not n.endswith("/") and re.search(r"(?i)(license|copying|copyright|notice)", n)
            }
            if not notices:
                raise ValueError("Missing original wheel notices: " + name)
            result.append(
                {
                    "distribution": name,
                    "version": package["version"],
                    "license": expression,
                    "retained_license_sha256": notices,
                }
            )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = inventory(Path(__file__).resolve().parents[1], args.cache)
    args.output.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Recorded {len(rows)} frozen runtime wheel notice inventories")
