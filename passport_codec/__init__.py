"""Versioned, science-free APT transport codec; never an identity/access token.

New original interoperability code. Publication/licence grant tracked in AAC0010.
COSE and Ed25519 operations are delegated to maintained cwt/cryptography libraries.
"""

from .codec import (
    PROFILE,
    CodecError,
    VerifiedPassport,
    build_payload,
    canonical,
    input_digest,
    normalize_input,
    pack,
    sign,
    unpack,
    verify,
)

__all__ = [
    "PROFILE",
    "CodecError",
    "VerifiedPassport",
    "build_payload",
    "canonical",
    "input_digest",
    "normalize_input",
    "pack",
    "sign",
    "unpack",
    "verify",
]
