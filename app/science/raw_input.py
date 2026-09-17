# SPDX-License-Identifier: AGPL-3.0-only
# Extracted under rights-holder authorization from app/domain/birth/raw_input.py
# Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: 86fcab9c68a8b7da530f113e1acd97b6298592f9ed3db888055d7da741251837
"""Unresolved human-entered birth information."""

from __future__ import annotations

import datetime as dt
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_PLACE_QUERY_LENGTH = 256
ISO_CIVIL_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
LOCAL_CIVIL_TIME_PATTERN = re.compile(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?\Z")


class RawBirthInput(BaseModel):
    """Local civil birth input before place, timezone, or UTC resolution."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    date: dt.date
    time: dt.time
    place_query: str = Field(strict=True, min_length=1, max_length=MAX_PLACE_QUERY_LENGTH)

    @field_validator("date", mode="before")
    @classmethod
    def require_civil_date_input(cls, value: object) -> object:
        """Accept only an ISO civil-date string or a native date without time semantics."""
        if isinstance(value, dt.datetime):
            raise ValueError("date must not include clock-time information")
        if isinstance(value, dt.date):
            return value
        if isinstance(value, str) and ISO_CIVIL_DATE_PATTERN.fullmatch(value) is not None:
            return value
        raise ValueError("date must be an ISO YYYY-MM-DD string or a native date")

    @field_validator("time", mode="before")
    @classmethod
    def require_civil_time_input(cls, value: object) -> object:
        """Accept only an approved local clock string or a native time."""
        if isinstance(value, dt.time):
            return value
        if isinstance(value, str) and LOCAL_CIVIL_TIME_PATTERN.fullmatch(value) is not None:
            return value
        raise ValueError("time must be a local civil clock string or a native time")

    @field_validator("time")
    @classmethod
    def require_naive_local_time(cls, value: dt.time) -> dt.time:
        """Keep the supplied civil time free of timezone and DST-fold semantics."""
        if value.tzinfo is not None:
            raise ValueError("time must not include timezone information")
        if value.fold != 0:
            raise ValueError("time must not include a DST fold")
        return value

    @field_validator("place_query", mode="before")
    @classmethod
    def trim_place_query(cls, value: object) -> object:
        """Trim only surrounding whitespace, preserving meaningful internal text."""
        if isinstance(value, str):
            return value.strip()
        return value
