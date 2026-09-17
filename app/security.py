# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded credentials and operational-only durable quota; never birth retention."""

import datetime as dt
import hashlib
import hmac
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class SecurityStateError(Exception):
    def __init__(self) -> None:
        super().__init__("security state unavailable")


def unique_json(data: bytes) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate member")
            result[key] = value
        return result

    def constant(_: str) -> object:
        raise ValueError("invalid JSON constant")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


class KeyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    key_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    sha256: SecretStr
    expires_at: dt.datetime = Field(repr=False)
    enabled: bool = Field(strict=True)
    scope: Literal["passport:calculate"]
    per_minute: int = Field(strict=True, ge=1, le=60)


def private_file(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 32768:
            raise SecurityStateError
        if info.st_uid not in (0, os.getuid()):
            raise SecurityStateError
        data = os.read(descriptor, 32769)
        if len(data) > 32768:
            raise SecurityStateError
        return data
    finally:
        os.close(descriptor)


def authenticate(path: Path | None, authorization: str, now: dt.datetime) -> KeyRecord | None:
    if path is None:
        raise SecurityStateError
    try:
        values = unique_json(private_file(path))
        if not isinstance(values, list) or not 1 <= len(values) <= 16:
            raise SecurityStateError
        records = [KeyRecord.model_validate(value) for value in values]
        if len({record.key_id for record in records}) != len(records):
            raise SecurityStateError
        for record in records:
            if not re.fullmatch(r"[0-9a-f]{64}", record.sha256.get_secret_value()):
                raise SecurityStateError
            if record.expires_at.utcoffset() != dt.timedelta(0):
                raise SecurityStateError
    except Exception:
        raise SecurityStateError from None
    match = re.fullmatch(r"Bearer apt1\.([0-9a-f]{16})\.([0-9a-f]{64})", authorization)
    key_id, secret = match.groups() if match else ("", "")
    supplied = hashlib.sha256(secret.encode("ascii")).hexdigest()
    found = None
    for record in records:
        equal = hmac.compare_digest(supplied, record.sha256.get_secret_value())
        if equal and record.key_id == key_id and record.enabled and now < record.expires_at:
            found = record
    return found


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    keys_file: Path | None = None
    quota_file: Path | None = None
    science_directory: Path | None = None

    @classmethod
    def environment(cls) -> "Settings":
        keys = os.environ.get("APT_KEYS_FILE")
        quota = os.environ.get("APT_QUOTA_FILE")
        science = os.environ.get("APT_SCIENCE_DIRECTORY")
        return cls(
            os.environ.get("APT_API_ENABLED") == "1",
            Path(keys) if keys else None,
            Path(quota) if quota else None,
            Path(science) if science else None,
        )


def initialize_quota(path: Path) -> None:
    """Explicit operator-only provisioning, never called at app startup; no overwrite."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE quota (key_id TEXT PRIMARY KEY, bucket INTEGER, used INTEGER)"
        )
        connection.execute("PRAGMA user_version = 1")


def reserve_quota(path: Path | None, key: KeyRecord, now: dt.datetime) -> bool:
    """Atomic across processes/restarts; unavailable/corrupt/missing state fails closed."""
    if path is None:
        raise SecurityStateError
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 1024 * 1024:
            raise SecurityStateError
        if info.st_uid not in (0, os.getuid()):
            raise SecurityStateError
        bucket = int(now.timestamp()) // 60
        with sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=0.1) as db:
            db.execute("PRAGMA synchronous = FULL")
            db.execute("BEGIN IMMEDIATE")
            if db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise SecurityStateError
            row = db.execute(
                "SELECT bucket, used FROM quota WHERE key_id = ?", (key.key_id,)
            ).fetchone()
            if row is None:
                if db.execute("SELECT COUNT(*) FROM quota").fetchone()[0] >= 128:
                    raise SecurityStateError
                used = 0
            else:
                previous, used = row
                if (
                    type(previous) is not int
                    or type(used) is not int
                    or used < 0
                    or bucket < previous
                ):
                    raise SecurityStateError
                if previous != bucket:
                    used = 0
            if used >= key.per_minute:
                return False
            db.execute(
                "INSERT OR REPLACE INTO quota VALUES (?, ?, ?)", (key.key_id, bucket, used + 1)
            )
        return True
    except Exception:
        raise SecurityStateError from None
