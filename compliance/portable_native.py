"""Offline correspondence for the added COSE/Ed25519 native dependency closure.

Inspect retained archives/SBOM/native identities, never execute archive source.
This is source correspondence, not an upstream compiler reproducibility claim.
"""

import hashlib
import json
import tarfile
import tomllib
import zipfile
from pathlib import Path

from compliance.native import elf_sections


def member(path: Path, suffix: str, depth: int | None = None) -> bytes:
    with tarfile.open(path) as archive:
        matches = [
            m
            for m in archive
            if m.isfile()
            and m.name.endswith(suffix)
            and (depth is None or m.name.count("/") == depth)
        ]
        if len(matches) != 1 or matches[0].size > 16 * 1024 * 1024:
            raise ValueError("Ambiguous/oversized native source member")
        stream = archive.extractfile(matches[0])
        if stream is None:
            raise ValueError("Missing native source member")
        return stream.read()


def audit(entries: list[dict], paths: dict[str, Path]) -> dict:
    by_name = {e["name"]: e for e in entries}
    crypto_name = next(
        n for n in paths if n.startswith("cryptography-50.0.2-") and n.endswith(".whl")
    )
    cffi_name = next(n for n in paths if n.startswith("cffi-2.1.1-") and n.endswith(".whl"))
    cbor_name = next(n for n in paths if n.startswith("cbor2-5.9.0-") and n.endswith(".whl"))
    with zipfile.ZipFile(paths[crypto_name]) as wheel:
        binary = wheel.read(next(n for n in wheel.namelist() if n.endswith("/_rust.abi3.so")))
        sbom_raw = wheel.read("cryptography-50.0.2.dist-info/sboms/sbom.json")
        rust_sbom = json.loads(
            wheel.read("cryptography-50.0.2.dist-info/sboms/cryptography-rust.cyclonedx.json")
        )
    sbom = json.loads(sbom_raw)["components"]
    if len(sbom) != 1 or (sbom[0]["name"], sbom[0]["version"]) != ("openssl", "4.0.3"):
        raise ValueError("Unexpected bundled crypto component")
    openssl = by_name["openssl-4.0.3.tar.gz"]
    if sbom[0]["hashes"] != [{"alg": "SHA-256", "content": openssl["sha256"]}]:
        raise ValueError("OpenSSL SBOM/source mismatch")
    if not any(
        r["type"] == "distribution" and r["url"] == openssl["url"]
        for r in sbom[0]["externalReferences"]
    ):
        raise ValueError("OpenSSL distribution identity mismatch")
    if b"OpenSSL 4.0.3 29 Sep 2026" not in binary:
        raise ValueError("Bundled OpenSSL identity mismatch")
    version = member(paths["openssl-4.0.3.tar.gz"], "/VERSION.dat")
    if any(line not in version.splitlines() for line in (b"MAJOR=4", b"MINOR=0", b"PATCH=3")):
        raise ValueError("OpenSSL source version mismatch")
    cargo = tomllib.loads(member(paths["cryptography-50.0.2.tar.gz"], "/Cargo.lock").decode())
    crates = {}
    for package in cargo["package"]:
        if "source" not in package:
            continue
        if package["source"] != "registry+https://github.com/rust-lang/crates.io-index":
            raise ValueError("Unexpected Cargo source")
        name = package["name"] + "-" + package["version"] + ".crate"
        if by_name[name]["sha256"] != package["checksum"]:
            raise ValueError("Cargo/source mismatch")
        crates[name] = package["checksum"]
    for component in rust_sbom["components"]:
        if (
            not component.get("purl", "").startswith("pkg:cargo/")
            or "download_url=file:" in component["purl"]
        ):
            continue
        name = component["name"] + "-" + component["version"] + ".crate"
        if component.get("hashes") != [{"alg": "SHA-256", "content": crates[name]}]:
            raise ValueError("Wheel Cargo SBOM differs from retained source")
    rust_commit = b"48a229ceaefd4985c50990b14116b6d856af0985"
    if (
        b"rustc version 1.98.1" not in elf_sections(binary)[".comment"]
        or b"/rustc/" + rust_commit not in binary
    ):
        raise ValueError("Crypto Rust runtime identity mismatch")
    rust_source = paths["rustc-1.98.1-src.tar.xz"]
    if (
        member(rust_source, "/git-commit-hash", 1).strip() != rust_commit
        or member(rust_source, "/src/version", 2).strip() != b"1.98.1"
    ):
        raise ValueError("Crypto Rust source identity mismatch")
    controls = member(
        paths["cryptography-50.0.2-build-controls.tar.gz"], "/.github/workflows/wheel-builder.yml"
    )
    if b"OPENSSL_STATIC=1" not in controls or b"--sbom-include=" not in controls:
        raise ValueError("Crypto build controls changed")
    cffi_controls = member(paths["cffi-2.1.1-build-controls.tar.gz"], "/.github/workflows/ci.yaml")
    if (
        b"libffi/archive/v3.4.6.tar.gz" not in cffi_controls
        or b"--enable-shared=no" not in cffi_controls
    ):
        raise ValueError("CFFI bundled libffi source changed")
    ffi_config = member(paths["libffi-3.4.6-source.tar.gz"], "/configure.ac")
    if b"3.4.6" not in ffi_config:
        raise ValueError("libffi source version mismatch")
    with zipfile.ZipFile(paths[cffi_name]) as wheel:
        cffi_binary = wheel.read(next(n for n in wheel.namelist() if n.endswith(".so")))
        if b"cffistatic_ffi_call" not in cffi_binary:
            raise ValueError("CFFI static libffi marker missing")
    return {
        "claim": "Pinned upstream archives, native identities, SBOM and build controls; no upstream compiler bit-reproducibility claim",
        "cryptography_wheel_sha256": by_name[crypto_name]["sha256"],
        "openssl_source_sha256": openssl["sha256"],
        "openssl_sbom_sha256": hashlib.sha256(sbom_raw).hexdigest(),
        "crypto_build_controls_sha256": by_name["cryptography-50.0.2-build-controls.tar.gz"][
            "sha256"
        ],
        "crypto_cargo_sources": crates,
        "rust_source_sha256": by_name["rustc-1.98.1-src.tar.xz"]["sha256"],
        "rust_source_commit": rust_commit.decode(),
        "cffi_wheel_sha256": by_name[cffi_name]["sha256"],
        "cffi_build_controls_sha256": by_name["cffi-2.1.1-build-controls.tar.gz"]["sha256"],
        "libffi_source_sha256": by_name["libffi-3.4.6-source.tar.gz"]["sha256"],
        "cbor_wheel_sha256": by_name[cbor_name]["sha256"],
        "cbor_source_sha256": by_name["cbor2-5.9.0.tar.gz"]["sha256"],
    }
