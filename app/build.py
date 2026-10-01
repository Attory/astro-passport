# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable build identity, never runtime environment or filesystem details."""

import re
from pathlib import Path

AAC_BASELINE = "59500ec0951e082dd4c3984999b8a42fe4ce53c8"
REPOSITORY = "https://github.com/Attory/astro-passport"
RELEASE_TAG = "apt-v0.2.0"
SCHEMA_TAG = "astropassport-schema-v1.0.0"
REVISION_FILE = Path(__file__).with_name("_revision")


def require_revision() -> str:
    revision = identity()["git_sha"]
    if revision is None:
        raise ValueError("immutable source revision unavailable")
    return revision


def identity() -> dict[str, str | None]:
    try:
        revision = REVISION_FILE.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        revision = ""
    valid = re.fullmatch(r"[0-9a-f]{40}", revision) is not None
    return {
        "service": "astro-passport",
        "service_version": "0.2.0",
        "git_sha": revision if valid else None,
        "release_tag": RELEASE_TAG if valid else None,
        "build_identity": f"git:{revision}" if valid else None,
        "aac_baseline": AAC_BASELINE,
        "source_repository": REPOSITORY,
        "source_url": f"{REPOSITORY}/tree/{revision}" if valid else None,
        "source_archive": f"{REPOSITORY}/archive/{revision}.tar.gz" if valid else None,
        "license": "AGPL-3.0-only",
        "license_url": f"{REPOSITORY}/blob/{revision}/LICENSE" if valid else None,
        "codec_version": "1.0.0",
        "codec_license": "Apache-2.0",
        "codec_source_url": f"{REPOSITORY}/tree/{revision}/passport_codec" if valid else None,
        "schema_version": "1.0.0",
        "schema_license": "Apache-2.0",
        "schema_source_url": (
            f"{REPOSITORY}/blob/{SCHEMA_TAG}/contracts/astropassport/v1/schema.json"
            if valid
            else None
        ),
        "supported_passport_profile": "western-synastry-core.v1-mvp",
    }
