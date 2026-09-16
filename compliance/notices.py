"""Retain verbatim native dependency notices without executing or installing libraries."""

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path

from compliance.bundle import acquire


def collect(lock: dict, cache: Path) -> dict:
    texts: dict[str, tuple[bytes, list[str]]] = {}

    def add(label: str, raw: bytes) -> None:
        digest = hashlib.sha256(raw).hexdigest()
        if digest not in texts:
            texts[digest] = (raw, [])
        texts[digest][1].append(label)

    for entry in lock["artifacts"]:
        name = entry["name"]
        if not (
            name.endswith((".crate", ".whl"))
            or name in ("rustc-1.98.0-src.tar.xz", "wit-bindgen-source.tar.gz")
        ):
            continue
        path = acquire(entry, cache, offline=True)
        if name.endswith(".whl"):
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if not member.endswith("/") and re.search(
                        r"(?i)(license|copying|copyright|notice)", member
                    ):
                        add(name + ":" + member, archive.read(member))
        else:
            with tarfile.open(path) as archive:
                for member in archive:
                    if member.isfile() and re.search(
                        r"(?i)^(license|licence|copying|copyright|notice|authors)([.-].*)?$",
                        member.name.rsplit("/", 1)[-1],
                    ):
                        stream = archive.extractfile(member)
                        if stream is None:
                            raise ValueError("notice unavailable")
                        add(name + ":" + member.name, stream.read())
    # Keep original bytes intact. UTF-8 decoding is validation, never replacement.
    result = {
        "scope": "current scaffold and proposed scientific dependency superset; original terms, not relicensed; inclusion does not imply installation",
        "notices": [],
    }
    for digest, (raw, labels) in sorted(texts.items()):
        result["notices"].append(
            {"sha256": digest, "origins": sorted(labels), "text": raw.decode("utf-8")}
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(
            collect(json.loads(args.lock.read_bytes()), args.cache), indent=2, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
