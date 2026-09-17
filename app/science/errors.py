# SPDX-License-Identifier: AGPL-3.0-only
"""Only fixed scientific failure codes may cross the HTTP boundary."""

from app.contracts import ErrorCode


class ScienceFailure(Exception):
    def __init__(self, code: ErrorCode) -> None:
        self.code = code
        super().__init__(code)


STATUS: dict[ErrorCode, int] = {
    "invalid_request": 422,
    "boundary_boundary": 422,
    "boundary_ambiguous": 422,
    "boundary_no_match": 422,
    "civil_ambiguous": 422,
    "civil_nonexistent": 422,
    "invalid_fold": 422,
    "artifact_unavailable": 503,
    "artifact_integrity": 500,
    "artifact_invalid": 500,
    "unsupported_runtime": 503,
    "native_failure": 500,
    "fallback_rejected": 500,
    "invalid_result": 500,
    "busy": 503,
    "timeout": 408,
    "internal_error": 500,
}
