"""Derive exact transitive Rust source pins from the retained pydantic-core Cargo.lock."""

import argparse
import io
import json
import tarfile
import tomllib
from pathlib import Path

from compliance.bundle import acquire


def expand(seed: dict, lock: dict, cache: Path) -> dict:
    source = next(e for e in lock["artifacts"] if e["name"] == "pydantic_core-2.46.5.tar.gz")
    path = acquire(source, cache, offline=True)
    with tarfile.open(fileobj=io.BytesIO(path.read_bytes())) as archive:
        cargo = archive.extractfile("pydantic_core-2.46.5/Cargo.lock")
        if cargo is None:
            raise ValueError("missing Cargo.lock")
        packages = tomllib.loads(cargo.read().decode())["package"]
    for package in packages:
        if "source" not in package:
            continue
        if package["source"] != "registry+https://github.com/rust-lang/crates.io-index":
            raise ValueError("unreviewed Cargo source")
        name, version = package["name"], package["version"]
        seed["artifacts"].append(
            {
                "name": f"{name}-{version}.crate",
                "component": f"pydantic-core Cargo source:{name}={version}",
                "url": f"https://static.crates.io/crates/{name}/{name}-{version}.crate",
                "sha256": package["checksum"],
            }
        )
    return seed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            expand(
                json.loads(args.seed.read_bytes()), json.loads(args.lock.read_bytes()), args.cache
            ),
            indent=2,
        )
        + "\n"
    )
