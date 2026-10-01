"""Reuse an exact hash-pinned public corresponding-source bundle, without extraction.

Only validated opaque content blobs are published into the hash cache. No archive
paths, links, permissions or code are applied to the host filesystem.
"""

import argparse
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
from pathlib import Path

from compliance.bundle import checked, verify


def import_bundle(source: Path, cache: Path, digest: str, size: int) -> int:
    verify(source, digest, size)
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="apt-source-import-", dir=cache.parent) as directory:
        inner = Path(directory) / "third-party.tar"
        with tarfile.open(source) as outer:
            matches = [m for m in outer if m.name == "third-party.tar"]
            if len(matches) != 1 or not matches[0].isfile() or matches[0].size > size:
                raise ValueError("Invalid corresponding-source bundle")
            stream = outer.extractfile(matches[0])
            if stream is None:
                raise ValueError("Missing source stream")
            with inner.open("xb") as out:
                shutil.copyfileobj(stream, out, 1024 * 1024)
        with tarfile.open(inner) as archive:
            records = archive.getmembers()
            if len({m.name for m in records}) != len(records):
                raise ValueError("Duplicate bundle member")
            lock_member = archive.getmember("source-lock.json")
            if not lock_member.isfile() or lock_member.size > 1024 * 1024:
                raise ValueError("Invalid source lock")
            stream = archive.extractfile(lock_member)
            if stream is None:
                raise ValueError("Missing source lock")
            lock = json.loads(stream.read())
            if lock["failures"]:
                raise ValueError("Incomplete source lock")
            expected = {}
            for entry in lock["artifacts"]:
                identity, _, length = checked(entry)
                if identity in expected and expected[identity] != length:
                    raise ValueError("Conflicting content identity")
                expected[identity] = length
            if {m.name for m in records} != {
                "source-lock.json",
                *("sha256/" + k for k in expected),
            }:
                raise ValueError("Unexpected source member")
            for identity, length in expected.items():
                if not re.fullmatch(r"[0-9a-f]{64}", identity):
                    raise ValueError("Invalid content identity")
                target = cache / identity
                if target.exists() or target.is_symlink():
                    verify(target, identity, length)
                    continue
                item = archive.getmember("sha256/" + identity)
                if not item.isfile() or item.size != length:
                    raise ValueError("Invalid source content")
                stream = archive.extractfile(item)
                if stream is None:
                    raise ValueError("Missing source content")
                temporary = Path(directory) / identity
                state = hashlib.sha256()
                with temporary.open("xb") as out:
                    while block := stream.read(1024 * 1024):
                        state.update(block)
                        out.write(block)
                if state.hexdigest() != identity:
                    raise ValueError("Source content digest mismatch")
                try:
                    target.hardlink_to(temporary)
                except FileExistsError:
                    verify(target, identity, length)
    return len(expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--bytes", type=int, required=True)
    args = parser.parse_args()
    print(
        f"Verified/imported {import_bundle(args.source, args.cache, args.sha256, args.bytes)} public source blobs; no source executed"
    )
