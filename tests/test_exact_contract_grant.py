"""An exact-byte Apache grant cannot silently spread to changed contracts."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "accepted/schema.json": "6d02118dd7b5ed16f52e1a67d2b270da53d070afe83c58e934484a0db5e8467c",
    "astropassport/v1/schema.json": "6d02118dd7b5ed16f52e1a67d2b270da53d070afe83c58e934484a0db5e8467c",
    "accepted/errors.json": "7e942b8e0c48929ebb91b440bbb3fd8a36d123c144ed3af97f4806d7389dc38d",
    "mvp/lahiri-v1/schema.json": "95fc7cd0fc093c6c3faa8f10a2282470f58d91cbed1f6f2709d1b5b410d8b477",
    "mvp/western-v1/schema.json": "3a56dc3638c0bd95d9ec60faec0ef8147b58550284299b4380e24263c7c5d062",
    "accepted/acep1-profile.md": "a6f289c3e685a4551301773cd920b3bb64884952f9d7571719a15fb6d41f913b",
    "accepted/semantics.md": "e10218f503ca0c3cf18517f10318a24b5ff30f97ed68a7e163f8982f849f2de8",
}


def test_apache_notice_matches_only_exact_contract_bytes() -> None:
    notice = (ROOT / "contracts/NOTICE").read_text()
    assert "Copyright © 2026 Anton Mosin" in notice
    assert len([line for line in notice.splitlines() if line.startswith("| `")]) == len(EXPECTED)
    for relative, expected in EXPECTED.items():
        source = (ROOT / "contracts" / relative).read_bytes()
        assert hashlib.sha256(source).hexdigest() == expected
        assert f"| `{relative}` | `{expected}` |" in notice
