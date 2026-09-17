"""Offline source correspondence evidence, without importing/executing scientific code.

Input archives are checksum-verified and inspected in memory, never extracted to disk.
This proves the stated relationships only, not a bit-reproducible upstream compiler build.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path

from compliance.bundle import acquire
from compliance.native import elf_sections, rpm

SECTIONS = (
    ".text",
    ".rodata",
    ".eh_frame",
    ".eh_frame_hdr",
    ".init",
    ".fini",
    ".note.gnu.build-id",
    ".gnu_debuglink",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def compare_sections(left: bytes, right: bytes, sections=SECTIONS) -> dict:
    a, b = elf_sections(left), elf_sections(right)
    for name in sections:
        if name not in a or name not in b or not a[name] or a[name] != b[name]:
            raise ValueError("native section mismatch: " + name)
    return {
        "original_sha256": sha(left),
        "wheel_sha256": sha(right),
        "equal_sections": {name: sha(a[name]) for name in sections},
        "claim": "listed sections byte-equal; whole-file identity NOT asserted",
    }


def dsc_checks(text: str, siblings: dict[str, dict]) -> dict:
    section = re.search(r"^Checksums-Sha256:\n((?: .+\n)+)", text, re.M)
    if section is None:
        raise ValueError("DSC has no SHA256 checksums")
    hashes = {}
    for line in section[1].splitlines():
        digest, size, name = line.split()
        if (
            name not in siblings
            or siblings[name]["sha256"] != digest
            or siblings[name]["bytes"] != int(size)
        ):
            raise ValueError("DSC/source mismatch")
        hashes[name] = digest
    if not hashes:
        raise ValueError("empty DSC")
    return hashes


def archive_members(path: Path):
    """Yield only ordinary files. Never follow archive links or run build controls."""
    with tarfile.open(path) as archive:
        for member in archive:
            if member.isfile():
                if member.size > 512 * 1024 * 1024:
                    raise ValueError("oversized archive member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError("missing member")
                yield member.name, stream.read()


def run(lock: dict, cache: Path) -> dict:
    if lock.get("failures"):
        raise ValueError("source acquisition failures remain")
    entries = lock["artifacts"]
    by_name = {e["name"]: e for e in entries}
    if len(by_name) != len(entries):
        raise ValueError("duplicate source name")
    paths = {e["name"]: acquire(e, cache, offline=True) for e in entries}
    result = {
        "schema": "apt-source-correspondence.v1",
        "scientific_execution": False,
        "artifact_count": len(entries),
        "debian_sources": [],
        "rust_crates": [],
        "native_lineage": {},
        "notices": [],
    }
    result["source_lock_sha256"] = sha(
        json.dumps(lock, sort_keys=True, separators=(",", ":")).encode()
    )
    for entry in entries:
        name = entry["name"]
        if name.endswith(".dsc"):
            siblings = {e["name"]: e for e in entries if e["component"] == entry["component"]}
            checked = dsc_checks(paths[name].read_text(), siblings)
            result["debian_sources"].append(
                {
                    "package": entry["source_package"],
                    "version": entry["source_version"],
                    "dsc_sha256": entry["sha256"],
                    "checked_sources": checked,
                }
            )
        if name.endswith(".crate"):
            members = dict(archive_members(paths[name]))
            cargo = next(
                v for n, v in members.items() if n.count("/") == 1 and n.endswith("/Cargo.toml")
            )
            package = tomllib.loads(cargo.decode())["package"]
            notices = {
                n: sha(v)
                for n, v in members.items()
                if re.search(r"(?i)(license|copying|copyright|notice|/AUTHORS$)", n)
            }
            if name == "wit-bindgen-rt-0.39.0.crate":
                vcs = json.loads(members["wit-bindgen-rt-0.39.0/.cargo_vcs_info.json"])
                if vcs["git"]["sha1"] != "f2393e6e98fa5f9236cac580db8a3fc9de6a4b70":
                    raise ValueError("unexpected wit-bindgen source")
                notices.update(
                    {
                        n: sha(v)
                        for n, v in archive_members(paths["wit-bindgen-source.tar.gz"])
                        if re.search(r"(?i)(license|copying|copyright|notice)", n)
                    }
                )
            if not package.get("license") or not notices:
                raise ValueError("Rust licence/notice requires review: " + name)
            result["rust_crates"].append(
                {
                    "name": package["name"],
                    "version": package["version"],
                    "license": package["license"],
                    "source_sha256": entry["sha256"],
                    "notices": notices,
                }
            )
        if name.endswith(".whl"):
            with zipfile.ZipFile(paths[name]) as wheel:
                notices = {
                    n: sha(wheel.read(n))
                    for n in wheel.namelist()
                    if not n.endswith("/")
                    and re.search(r"(?i)(license|copying|copyright|notice)", n)
                }
            if not notices:
                raise ValueError("wheel notice missing: " + name)
            result["notices"].append({"artifact": name, "files": notices})
    source_packages = {e["component"] for e in entries if "source_package" in e}
    if len(result["debian_sources"]) != len(source_packages):
        raise ValueError("Debian source coverage mismatch")

    numpy_name = next(n for n in paths if n.startswith("numpy-") and n.endswith(".whl"))
    with zipfile.ZipFile(paths[numpy_name]) as wheel:
        for library in ("libquadmath", "libgfortran"):
            original = library + "-8.5.0-28.el8_10.alma.1.x86_64.rpm"
            tags, files = rpm(paths[original].read_bytes())
            source = "gcc-8.5.0-28.el8_10.alma.1.src.rpm"
            if tags.get(1044) != source:
                raise ValueError("unexpected RPM source identity")
            original_binary = next(
                v
                for n, v in files.items()
                if n.startswith("./usr/lib64/" + library + ".so.") and v.startswith(b"\x7fELF")
            )
            member = next(
                n for n in wheel.namelist() if n.startswith("numpy.libs/" + library) and ".so." in n
            )
            proof = compare_sections(original_binary, wheel.read(member))
            proof.update(
                {"rpm": original, "source_rpm": source, "source_sha256": by_name[source]["sha256"]}
            )
            result["native_lineage"][library] = proof
        openblas = next(
            n for n in paths if n.startswith("scipy_openblas64-") and n.endswith(".whl")
        )
        with zipfile.ZipFile(paths[openblas]) as upstream:
            original = next(
                n for n in upstream.namelist() if n.endswith("/libscipy_openblas64_.so")
            )
            member = next(
                n
                for n in wheel.namelist()
                if n.startswith("numpy.libs/libscipy_openblas") and n.endswith(".so")
            )
            result["native_lineage"]["openblas"] = compare_sections(
                upstream.read(original), wheel.read(member), SECTIONS[:-1]
            )

    binding = {
        n.split("/libswe/", 1)[1]: sha(v)
        for n, v in archive_members(paths["pysweph-2.10.3.6.tar.gz"])
        if "/libswe/" in n
        and n.endswith((".c", ".h"))
        and n.split("/libswe/", 1)[1].count("/") == 0
    }
    upstream = {
        n.split("/", 1)[1]: sha(v)
        for n, v in archive_members(paths["swisseph-core-source.tar.gz"])
        if n.count("/") == 1 and n.endswith((".c", ".h"))
    }
    if len(binding) != 27 or binding != upstream:
        raise ValueError("Swiss C/header source correspondence mismatch")
    result["swiss_source_equal"] = binding
    core_name = next(n for n in paths if n.startswith("pydantic_core-") and n.endswith(".whl"))
    with zipfile.ZipFile(paths[core_name]) as core:
        binary = core.read(next(n for n in core.namelist() if n.endswith(".so")))
    rust_commit = b"88d9e12ae178fab0fb5cc050a94da85685d449ea"
    if (
        b"rustc version 1.98.0" not in elf_sections(binary)[".comment"]
        or b"/rustc/" + rust_commit not in binary
    ):
        raise ValueError("Rust native build identity changed")
    rust_identity = {}
    with tarfile.open(paths["rustc-1.98.0-src.tar.xz"]) as archive:
        for member in archive:
            name = member.name.split("/", 1)[-1]
            if name in ("git-commit-hash", "src/version") and member.isfile():
                stream = archive.extractfile(member)
                if stream is not None:
                    rust_identity[name] = stream.read().strip()
    if rust_identity != {"git-commit-hash": rust_commit, "src/version": b"1.98.0"}:
        raise ValueError("Rust runtime source identity mismatch")
    result["rust_runtime"] = {
        "source_commit": rust_commit.decode(),
        "version": "1.98.0",
        "wheel_binary_sha256": sha(binary),
        "source_sha256": by_name["rustc-1.98.0-src.tar.xz"]["sha256"],
    }
    result["publication_evidence"] = {}
    for package in ("numpy", "pysweph"):
        evidence = json.loads(paths[package + "-publication-provenance.json"].read_bytes())
        subjects = []
        for bundle in evidence["attestation_bundles"]:
            for attestation in bundle["attestations"]:
                statement = json.loads(base64.b64decode(attestation["envelope"]["statement"]))
                for subject in statement["subject"]:
                    if by_name[subject["name"]]["sha256"] != subject["digest"]["sha256"]:
                        raise ValueError("publication subject mismatch")
                    subjects.append(subject)
        result["publication_evidence"][package] = {
            "subjects": subjects,
            "scope": "PyPI HTTPS publication record and subject hash checked; not independent Sigstore verification or reproducible build proof",
        }
    shapely_controls = dict(archive_members(paths["shapely-build-controls.tar.gz"]))
    workflow = next(
        v for n, v in shapely_controls.items() if n.endswith("/.github/workflows/release.yml")
    )
    if b'GEOS_VERSION: "3.13.1"' not in workflow:
        raise ValueError("GEOS build version changed")
    result["geos_build_controls"] = {
        "version": "3.13.1",
        "workflow_sha256": sha(workflow),
        "source_sha256": by_name["geos-3.13.1.tar.bz2"]["sha256"],
    }
    with zipfile.ZipFile(paths["timezones.geojson.zip"]) as geometry:
        digest = sha(geometry.read("combined.json"))
        if digest != "40863a7e585e4c1f25a7dd9b0b204d591f4af45a180aa9ec44775fed8a8510bf":
            raise ValueError("TBB geometry identity changed")
        result["tbb_geometry_sha256"] = digest
    for name in ("tzcode2026c.tar.gz", "tzdata2026c.tar.gz"):
        versions = [v for n, v in archive_members(paths[name]) if n == "version"]
        if versions != [b"2026c\n"]:
            raise ValueError("IANA source version changed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(json.loads(args.lock.read_bytes()), args.cache)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Verified source correspondence without scientific execution")
