"""Offline synthetic wire conformance. Golden keys are NEVER operational trust."""

import base64
import hashlib
import json
from pathlib import Path

import cbor2

from .codec import FIELDS, canonical, verify


def check() -> int:
    root = Path(__file__).parent
    pins = json.loads((root / "PINS.json").read_text())
    expected = {"__init__.py", "codec.py", "conformance.py", "fixtures/golden-v1.json"}
    if pins["version"] != 1 or set(pins["files"]) != expected:
        raise ValueError("Invalid frozen codec pin inventory")
    for name, digest in pins["files"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Codec copy differs from the frozen reviewed inventory")
    fixture = json.loads((Path(__file__).parent / "fixtures/golden-v1.json").read_text())
    fields = hashlib.sha256(json.dumps(FIELDS, separators=(",", ":")).encode()).hexdigest()
    if fields != fixture["field_table_sha256"]:
        raise ValueError("Codec field table differs from frozen v1")
    count = 0
    for vector in fixture["vectors"]:
        raw = bytes.fromhex(vector["canonical_hex"])
        if canonical(cbor2.loads(raw)) != raw:
            raise ValueError("Noncanonical golden vector")
        keys = {
            entry["kid"].encode(): base64.b64decode(entry["public_key_base64"], validate=True)
            for entry in vector["signatures"]
        }
        for entry in vector["signatures"]:
            receipt = verify(entry["token"], keys)
            if receipt.scientific_bytes != raw or receipt.profile_id != vector["profile_id"]:
                raise ValueError("Golden verification/identity mismatch")
            count += 1
    return count


if __name__ == "__main__":
    print(f"{check()} frozen synthetic signatures verified; no astronomical correctness claimed")
