# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic exact-revision Corresponding Source assembly; no publication/deployment.

Combines a clean git source archive with all retained matching third-party sources, build
controls, original notices and scientific data in one verifiable artifact. Images and
activation remain separate; this tool does not claim bit-reproducible upstream compilation.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from compliance.bundle import pack
from compliance.validate import validate


def digest(path: Path) -> str:
    state = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            state.update(block)
    return state.hexdigest()


def assemble(cache: Path, output: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=root):
        raise ValueError("clean committed source required")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    validate(root)
    source = subprocess.check_output(["git", "archive", "--format=tar", revision], cwd=root)
    lock = root / "compliance/source-lock.json"
    with tempfile.TemporaryDirectory(prefix="apt-source-bundle-", dir=output.parent) as temporary:
        third = Path(temporary) / "third-party.tar"
        pack(lock, cache, third)
        receipt = {
            "schema": "apt-corresponding-source.v1",
            "source_revision": revision,
            "source_repository": "https://github.com/Attory/astro-passport",
            "apt_source_archive_sha256": hashlib.sha256(source).hexdigest(),
            "third_party_bundle_sha256": digest(third),
            "source_lock_sha256": hashlib.sha256(lock.read_bytes()).hexdigest(),
            "activation": "not authorized",
            "upstream_compiler_bit_reproducibility": "not claimed",
        }
        # Fixed outer metadata. Inner git archive is fixed by exact source revision;
        # inner third-party archive is separately hash-verified and deterministic.
        with output.open("xb") as target, tarfile.open(fileobj=target, mode="w") as archive:
            for name, raw in [
                (
                    "manifest.json",
                    json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode(),
                ),
                ("apt-source.tar", source),
            ]:
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                info.mode = 0o644
                info.mtime = 0
                archive.addfile(info, io.BytesIO(raw))
            info = tarfile.TarInfo("third-party.tar")
            info.size = third.stat().st_size
            info.mode = 0o644
            info.mtime = 0
            with third.open("rb") as stream:
                archive.addfile(info, stream)
    return {**receipt, "bundle_sha256": digest(output), "bundle_bytes": output.stat().st_size}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assemble(args.cache, args.output), sort_keys=True))
