# AstroPassport portable codec 1.0.0

This directory is the implementation-neutral, Apache-2.0 transport codec used
by APT, Unbubble and ACE. It carries no birth records, scientific rules,
compatibility methodology, identity authority or network client. The four
frozen source/fixture files and their SHA-256 digests are in `PINS.json`.

`LICENSE` and `NOTICE` apply to this directory. The APT service is separately
AGPL-3.0-only. Dependencies are cwt 3.3.0, cbor2 5.9.0 and cryptography 50.0.2;
their own licence notices remain in installed distributions. The `pyproject.toml`
in this directory builds a standalone source/wheel distribution without importing
the APT application or private repositories. Consumers must still configure
their own trusted Ed25519 public keys; this package does not authorize a key.

From a clean APT checkout, run `uv build passport_codec --out-dir /tmp/apt-codec-dist`
and `uv run --frozen python -m passport_codec.conformance`. The four synthetic
signatures test deterministic wire interoperability, not astronomical accuracy.
