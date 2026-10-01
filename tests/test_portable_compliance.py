"""Opaque source-cache import rejects archive paths/links and altered content."""

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from compliance.import_bundle import import_bundle


def fixture_bundle(tmp_path: Path, mutation: str | None = None) -> tuple[Path, str, int]:
    raw = b"Original synthetic source archive bytes, not executable code"
    digest = hashlib.sha256(raw).hexdigest()
    lock = {
        "failures": [],
        "artifacts": [
            {
                "name": "synthetic.tar.gz",
                "component": "fixture",
                "sha256": digest,
                "url": "https://example.invalid/synthetic.tar.gz",
                "bytes": len(raw),
            }
        ],
    }
    inner = io.BytesIO()
    with tarfile.open(fileobj=inner, mode="w") as archive:
        for name, value in (
            ("source-lock.json", json.dumps(lock).encode()),
            ("sha256/" + digest, raw),
        ):
            item = tarfile.TarInfo(name)
            item.size = len(value)
            if mutation == "link" and name.startswith("sha256/"):
                item.type, item.linkname, item.size = tarfile.SYMTYPE, "/etc/passwd", 0
                archive.addfile(item)
            else:
                if mutation == "tamper" and name.startswith("sha256/"):
                    value = b"X" * len(value)
                archive.addfile(item, io.BytesIO(value))
        if mutation == "path":
            archive.addfile(tarfile.TarInfo("../../not-authorized"))
    output = tmp_path / "complete.tar"
    with tarfile.open(output, mode="w") as outer:
        data = inner.getvalue()
        item = tarfile.TarInfo("third-party.tar")
        item.size = len(data)
        outer.addfile(item, io.BytesIO(data))
    return output, hashlib.sha256(output.read_bytes()).hexdigest(), output.stat().st_size


def test_verified_public_blobs_reuse_without_overwrite(tmp_path: Path) -> None:
    source, digest, size = fixture_bundle(tmp_path)
    cache = tmp_path / "cache"
    assert import_bundle(source, cache, digest, size) == 1
    assert import_bundle(source, cache, digest, size) == 1
    assert len(list(cache.iterdir())) == 1
    with pytest.raises(ValueError, match="digest"):
        import_bundle(source, cache, "0" * 64, size)


@pytest.mark.parametrize("mutation", ["path", "link", "tamper"])
def test_untrusted_archive_metadata_never_becomes_host_paths(tmp_path: Path, mutation: str) -> None:
    source, digest, size = fixture_bundle(tmp_path, mutation)
    with pytest.raises(ValueError):
        import_bundle(source, tmp_path / "cache", digest, size)
