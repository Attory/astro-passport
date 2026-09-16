"""Maintainer-only public source-lock discovery; no scientific imports or private inputs."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 1024 * 1024 * 1024


def fetch(url: str, cache: Path) -> bytes:
    """Discovery cache is keyed by URL, then immutable release lock pins actual bytes."""
    if not url.startswith("https://"):
        raise ValueError("HTTPS required")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / hashlib.sha256(url.encode()).hexdigest()
    if destination.is_file():
        return destination.read_bytes()
    for attempt in range(3):
        temporary = None
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                if not response.url.startswith("https://"):
                    raise ValueError("insecure redirect")
                with tempfile.NamedTemporaryFile(dir=cache, delete=False) as out:
                    temporary = Path(out.name)
                    count = 0
                    while block := response.read(1024 * 1024):
                        count += len(block)
                        if count > MAX_BYTES:
                            raise ValueError("source too large")
                        out.write(block)
            os.replace(temporary, destination)
            return destination.read_bytes()
        except (OSError, ValueError):
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def record(url: str, name: str, component: str, cache: Path, expected: str | None = None):
    data = fetch(url, cache)
    digest = hashlib.sha256(data).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("upstream digest differs from approved pin: " + name)
    target = cache.parent / "sha256" / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(data)
    return {"name": name, "component": component, "url": url, "sha256": digest, "bytes": len(data)}


def debian(package: dict[str, str], cache: Path):
    name, version = package["source_package"], package["source_version"]
    root = "https://snapshot.debian.org"
    url = f"{root}/mr/package/{name}/{urllib.parse.quote(version, safe='')}/srcfiles"
    metadata = json.loads(fetch(url, cache))
    rows = []
    for item in metadata["result"]:
        identity = item["hash"]
        info = json.loads(fetch(f"{root}/mr/file/{identity}/info", cache))
        filename = info["result"][0]["name"]
        raw = fetch(f"{root}/file/{identity}", cache)
        if hashlib.sha1(raw).hexdigest() != identity:
            raise ValueError("Debian archive identity mismatch")
        row = record(f"{root}/file/{identity}", filename, f"debian:{name}={version}", cache)
        row["snapshot_sha1_locator"] = identity
        row["source_package"], row["source_version"] = name, version
        rows.append(row)
    print(f"source retained: Debian {name} {version}", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seed = json.loads(args.seed.read_bytes())
    cache = args.cache / "discovery"
    artifacts = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(debian, p, cache): p for p in seed["debian_sources"]}
        for future in concurrent.futures.as_completed(jobs):
            try:
                artifacts.extend(future.result())
            except Exception as error:
                failures.append({"component": jobs[future], "failure": type(error).__name__})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {
            pool.submit(record, e["url"], e["name"], e["component"], cache, e.get("sha256")): e
            for e in seed["artifacts"]
        }
        for future in concurrent.futures.as_completed(jobs):
            entry = jobs[future]
            try:
                artifacts.append(future.result())
                print("source retained:", entry["name"], flush=True)
            except Exception as error:
                failures.append({"component": entry["name"], "failure": type(error).__name__})
    result = {
        "schema": "apt-runtime-source-lock.v1",
        "status": "discovery_not_clearance",
        "artifacts": sorted(artifacts, key=lambda e: (e["component"], e["name"])),
        "failures": failures,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Retained {len(artifacts)} artifacts; {len(failures)} unresolved acquisition failures")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
