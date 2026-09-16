"""Independent synthetic compliance-tool tests; no network or scientific imports."""

import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import pytest

from compliance.audit import dsc_checks
from compliance.bundle import acquire, checked, pack, verify
from compliance.native import elf_sections, rpm
from compliance.validate import validate


def fixture_entry() -> tuple[bytes, dict[str, object]]:
    payload = b"independently authored source-compliance test bytes\n"
    return payload, {
        "url": "https://example.com/source.tar.gz",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/x",
        "file:///etc/passwd",
        "https://user:secret@example.com/x",
        "https://example.com/x?secret=forbidden",
        "https://example.com/x#fragment",
    ],
)
def test_public_credential_free_https_required(url: str) -> None:
    _, entry = fixture_entry()
    entry["url"] = url
    with pytest.raises(ValueError):
        checked(entry)


@pytest.mark.parametrize("size", [0, -1, True, 2**31])
def test_sizes_bounded(size: int) -> None:
    _, entry = fixture_entry()
    entry["bytes"] = size
    with pytest.raises(ValueError):
        checked(entry)


def test_offline_corruption_missing_and_symlink_fail(tmp_path: Path) -> None:
    payload, entry = fixture_entry()
    digest = str(entry["sha256"])
    with pytest.raises(ValueError):
        acquire(entry, tmp_path, offline=True)
    path = tmp_path / digest
    path.write_bytes(payload)
    assert acquire(entry, tmp_path, offline=True) == path
    path.write_bytes(b"X" + payload[1:])
    with pytest.raises(ValueError):
        verify(path, digest, len(payload))
    target = tmp_path / "target"
    target.write_bytes(payload)
    link = tmp_path / "symlink"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        verify(link, digest, len(payload))


def test_deterministic_bundle_and_exclusive_output(tmp_path: Path) -> None:
    payload, entry = fixture_entry()
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / str(entry["sha256"])).write_bytes(payload)
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"artifacts": [entry]}))
    first, second = tmp_path / "a.tar", tmp_path / "b.tar"
    pack(lock, cache, first)
    pack(lock, cache, second)
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(FileExistsError):
        pack(lock, cache, first)
    with tarfile.open(first) as archive:
        assert archive.getnames() == ["source-lock.json", "sha256/" + str(entry["sha256"])]
        assert all(m.mtime == 0 and m.uid == 0 and m.gid == 0 for m in archive.getmembers())


@pytest.mark.parametrize("raw", [b"", b"not native", b"\x7fELF\x02\x01", b"\xed\xab\xee\xdb"])
def test_truncated_native_headers_rejected(raw: bytes) -> None:
    for reader in (rpm, elf_sections):
        with pytest.raises(ValueError):
            reader(raw)


def test_dsc_sources_missing_wrong_hash_and_wrong_size_rejected() -> None:
    digest = "a" * 64
    text = f"Checksums-Sha256:\n {digest} 10 source.tar.xz\nOther: value\n"
    rows = {"source.tar.xz": {"sha256": digest, "bytes": 10}}
    assert dsc_checks(text, rows) == {"source.tar.xz": digest}
    for siblings in (
        {},
        {"source.tar.xz": {"sha256": "b" * 64, "bytes": 10}},
        {"source.tar.xz": {"sha256": digest, "bytes": 11}},
    ):
        with pytest.raises(ValueError):
            dsc_checks(text, siblings)
    with pytest.raises(ValueError):
        dsc_checks("Checksums-Sha256:\n", rows)


def test_committed_compliance_coverage() -> None:
    validate(Path(__file__).resolve().parents[1])


@pytest.mark.parametrize("change", ["source", "notice", "base", "wheel", "missing", "failure"])
def test_compliance_drift_fails_closed(tmp_path: Path, change: str) -> None:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(
        root / "compliance", tmp_path / "compliance", ignore=shutil.ignore_patterns("__pycache__")
    )
    for name in ("uv.lock", "Dockerfile"):
        shutil.copyfile(root / name, tmp_path / name)
    path = tmp_path / "compliance" / "base-image.json"
    data = json.loads(path.read_bytes())
    if change == "source":
        data["packages"][0]["source_version"] = "unreviewed"
    elif change == "notice":
        data["copyrights"][next(iter(data["copyrights"]))]["text"] += "corruption"
    elif change == "base":
        data["image"] += "wrong"
    else:
        path = tmp_path / "compliance" / "source-lock.json"
        data = json.loads(path.read_bytes())
        if change == "missing":
            data["artifacts"].pop()
        elif change == "failure":
            data["failures"].append("missing source")
        else:
            next(e for e in data["artifacts"] if e["name"].endswith(".whl"))["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        validate(tmp_path)
