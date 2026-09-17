# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from scripts/build-tzdb-artifact.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: a31cb6f2aa81a4798563252282fd5ca1156e6ac442f6aef19bc463a25b1c81ba
#!/usr/bin/env python3
"""Explicit pinned IANA build/retention tooling; never invoked by the web runtime."""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

SOURCES = {
    "tzcode2026c.tar.gz": "b1cffc3ace4c4c7cd0efba2f7add86ec3d0b79da48bcf03582671fd3c8feace8",
    "tzdata2026c.tar.gz": "e4a178a4477f3d0ea77cc31828ff72aa38feff8d61aa13e7e99e142e9d902be4",
}
BUILD_POLICY = "main-backzone-zone.tab-posix-slim.v1"


def build(source_directory: Path, output: Path) -> str:
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tzdb-build-", dir=output.parent) as temporary:
        work = Path(temporary)
        total = 0
        for filename, digest in SOURCES.items():
            with (source_directory / filename).open("rb") as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("source integrity")
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
                for member in archive:
                    if (
                        not member.isfile()
                        or not re.fullmatch(r"[A-Za-z0-9_.-]+", member.name)
                        or member.name in {".", ".."}
                        or member.size > 1024 * 1024
                    ):
                        raise ValueError("source member")
                    total += member.size
                    if total > 16 * 1024 * 1024:
                        raise ValueError("source size")
                    extracted = archive.extractfile(member)
                    if extracted is None:
                        raise ValueError("source member")
                    value = extracted.read(member.size + 1)
                    if len(value) != member.size:
                        raise ValueError("source size")
                    destination = work / member.name
                    if destination.exists():
                        if destination.read_bytes() != value:
                            raise ValueError("conflicting source members")
                    else:
                        destination.write_bytes(value)
                        # Upstream's version target detects modified source mtimes. Preserve the
                        # verified release metadata rather than fabricating a clean version flag.
                        os.utime(destination, (member.mtime, member.mtime))
        environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "TZ": "UTC"}
        subprocess.run(
            [
                "make",
                "-C",
                str(work),
                "-j2",
                "zic",
                "tzdata.zi",
                "PACKRATDATA=backzone",
                "PACKRATLIST=zone.tab",
                "DATAFORM=main",
                "REDO=posix_only",
                "CC=gcc",
                "CFLAGS=-O2",
            ],
            check=True,
            capture_output=True,
            timeout=120,
            env=environment,
        )
        compiler = work / "zic"
        version = subprocess.run(
            [str(compiler), "--version"],
            check=True,
            capture_output=True,
            timeout=10,
            text=True,
            env=environment,
        ).stdout.strip()
        if version != "zic (tzcode) 2026c":
            raise ValueError("compiler identity")
        zone_directory = work / "compiled"
        subprocess.run(
            [str(compiler), "-b", "slim", "-d", str(zone_directory), str(work / "tzdata.zi")],
            check=True,
            capture_output=True,
            timeout=30,
            env=environment,
        )
        zones = {}
        for path in sorted(zone_directory.rglob("*")):
            if path.is_symlink():
                raise ValueError("compiled symlink")
            if path.is_file():
                name = path.relative_to(zone_directory).as_posix()
                value = path.read_bytes()
                if not value.startswith(b"TZif") or len(value) > 64 * 1024:
                    raise ValueError("compiled zone")
                zones[name] = value
        if len(zones) != 598 or sum(map(len, zones.values())) > 8 * 1024 * 1024:
            raise ValueError("compiled scope")
        manifest = {
            "schema_version": "tzdb-artifact.v1",
            "iana_version": "2026c",
            "build_policy": BUILD_POLICY,
            "zic_version": version,
            "sources": SOURCES,
            "zones": {name: hashlib.sha256(value).hexdigest() for name, value in zones.items()},
        }
        entries = {
            "manifest.json": json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode(),
            **{f"zoneinfo/{name}": value for name, value in zones.items()},
        }
        staged = work / "tzdb.zip"
        with zipfile.ZipFile(
            staged, "w", compression=zipfile.ZIP_STORED, allowZip64=False
        ) as result:
            for name, value in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                result.writestr(info, value)
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        staged.chmod(0o644)
        os.link(staged, output)
        return digest


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3:
            raise ValueError("usage")
        print(build(Path(sys.argv[1]), Path(sys.argv[2])))
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError):
        sys.exit("Pinned timezone-rule build failed; no fallback or overwrite performed")
