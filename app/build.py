"""Immutable build identity, never runtime environment or filesystem details."""

import re
from pathlib import Path

AAC_BASELINE = "aa4373b5d7b2539adf5bc87c0b4cc7d392d2135d"
REPOSITORY = "https://github.com/Attory/astro-passport"
REVISION_FILE = Path(__file__).with_name("_revision")


def identity() -> dict[str, str | None]:
    try:
        revision = REVISION_FILE.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        revision = ""
    valid = re.fullmatch(r"[0-9a-f]{40}", revision) is not None
    return {
        "service": "astro-passport",
        "git_sha": revision if valid else None,
        "aac_baseline": AAC_BASELINE,
        "source_repository": REPOSITORY,
        "source_url": f"{REPOSITORY}/tree/{revision}" if valid else None,
        "source_archive": f"{REPOSITORY}/archive/{revision}.tar.gz" if valid else None,
        "license": "AGPL-3.0-only",
        "license_url": f"{REPOSITORY}/blob/{revision}/LICENSE" if valid else None,
    }
