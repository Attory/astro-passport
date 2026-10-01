"""APT compact transport v1: finite lossless facts, canonical bytes, offline trust.

No scientific calculations, member identifiers, clocks, storage or network calls.
The signed payload is the scientific identity; COSE headers/signatures are not.
"""

import base64
import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any

import cbor2
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cwt import COSE, COSEKey

VERSION = 1
PROFILE = "western-synastry-core.v1-mvp"
CONTENT_TYPE = "application/apt-passport+cbor;v=1"
AAD = b"APT-PASSPORT\x00CBOR-COSE-v1"
MAX_CBOR = 49152
MAX_TOKEN = 65536

# Frozen v1 table: never reorder or insert fields; incompatible changes need a version.
# These are wire field names, not imported scientific implementation or rules.
FIELDS = (
    "adapter",
    "archive_sha256",
    "ascendant",
    "attribution",
    "authenticity",
    "ayanamsha",
    "ayanamsha_flags",
    "ayanamsha_kind",
    "base",
    "binary64_hex",
    "binary_sha256",
    "binding",
    "binding_source_sha256",
    "bodies",
    "body",
    "boundary",
    "build_policy",
    "calendar",
    "catalog_sha256",
    "civil",
    "civil_input",
    "contract_version",
    "cusps",
    "data_origin",
    "dataset",
    "date",
    "decimal_degrees",
    "delta_t_policy",
    "display_name",
    "ephemeris_schema",
    "execution_target",
    "flags",
    "fold",
    "geometry_sha256",
    "geos_version",
    "historical_assurance",
    "houses",
    "iana_version",
    "iana_zone",
    "latitude",
    "library",
    "license",
    "license_url",
    "limitations",
    "longitude",
    "manifest_sha256",
    "mc",
    "moon",
    "moon_data_sha256",
    "numerical_policy",
    "numpy_version",
    "offset_seconds",
    "outcome",
    "planet_data_sha256",
    "policy",
    "profile",
    "projection",
    "provenance",
    "provider",
    "python_runtime",
    "python_version",
    "query",
    "reason",
    "release",
    "requested_flags",
    "requested_limit",
    "resolution",
    "resolver",
    "result_count",
    "returned_flags",
    "runtime",
    "schema_version",
    "selected_index",
    "selected_place",
    "serialization",
    "shapely_version",
    "sidereal",
    "source_id",
    "source_repository",
    "source_revision",
    "status",
    "swiss_sidereal_mode",
    "system",
    "time",
    "time_policy",
    "tropical",
    "tt_jd_binary64",
    "tzcode_source_sha256",
    "tzdata_source_sha256",
    "tzif_sha256",
    "ut1_jd_binary64",
    "utc",
    "utc_convention",
    "variant",
    "western",
)
FIELD_IDS = {name: index for index, name in enumerate(FIELDS)}
HEX_FIELDS = {"binary64_hex", "tt_jd_binary64", "ut1_jd_binary64"}
BODIES = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "true_north_node",
)


class CodecError(ValueError):
    """Only bounded codes escape; never echo a passport, key or native exception."""

    def __init__(self, code: str = "invalid_passport") -> None:
        self.code = code
        super().__init__(code)


def _finite(value: Any, depth: int = 0, budget: list[int] | None = None) -> None:
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    if depth > 16 or budget[0] < 0:
        raise CodecError("too_large")
    kind = type(value)
    if kind is float:
        if not math.isfinite(value):
            raise CodecError("non_finite")
    elif kind is int:
        if not -(1 << 63) <= value < (1 << 64):
            raise CodecError()
    elif kind in (str, bytes):
        if len(value) > 4096:
            raise CodecError("too_large")
    elif kind in (bool, type(None)):
        pass
    elif kind is list:
        for item in value:
            _finite(item, depth + 1, budget)
    elif kind is dict:
        for key, item in value.items():
            if type(key) is not int:
                raise CodecError()
            _finite(key, depth + 1, budget)
            _finite(item, depth + 1, budget)
    else:
        raise CodecError()


def canonical(value: Any) -> bytes:
    """RFC8949 deterministic CBOR, shortest lossless floats; no E9 truncation."""
    _finite(value)
    result: bytes = cbor2.dumps(value, canonical=True)
    if len(result) > MAX_CBOR:
        raise CodecError("too_large")
    return result


def _decode(data: bytes) -> Any:
    try:
        value = cbor2.loads(data, max_depth=20)
        # Also rejects duplicate keys, indefinite encodings and trailing bytes.
        if canonical(value) != data:
            raise CodecError("non_canonical")
        return value
    except CodecError:
        raise
    except Exception:
        raise CodecError("invalid_encoding") from None


def pack(value: Any) -> Any:
    """Exact reversible integer-key projection of the compatible JSON schema."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key not in FIELD_IDS:
                raise CodecError("unsupported_field")
            if key in HEX_FIELDS:
                try:
                    number = float.fromhex(item)
                    if not math.isfinite(number) or number.hex() != item:
                        raise ValueError
                except (ValueError, TypeError):
                    raise CodecError("invalid_number") from None
                result[FIELD_IDS[key]] = number
            else:
                result[FIELD_IDS[key]] = pack(item)
        return result
    if isinstance(value, tuple | list):
        return [pack(item) for item in value]
    _finite(value)
    return value


def unpack(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if type(key) is not int or not 0 <= key < len(FIELDS):
                raise CodecError("unsupported_field")
            name = FIELDS[key]
            if name in HEX_FIELDS:
                if type(item) is not float or not math.isfinite(item):
                    raise CodecError("invalid_number")
                result[name] = item.hex()
            else:
                result[name] = unpack(item)
        return result
    if isinstance(value, list):
        return [unpack(item) for item in value]
    _finite(value)
    return value


def normalize_input(request: Mapping[str, Any]) -> dict[str, Any]:
    """Wire normalization only. Geographic/civil resolution remains solely APT."""
    try:
        if request["profile"] != PROFILE:
            raise CodecError("unsupported_profile")
        civil = request["civil"]
        day = date.fromisoformat(civil["date"])
        if not 1900 <= day.year <= 2100:
            raise ValueError
        clock = None if civil["time"] is None else time.fromisoformat(civil["time"])
        if clock is not None and clock.tzinfo is not None:
            raise ValueError
        fold = civil["fold"]
        if fold is not None and (type(fold) is not int or fold not in (0, 1)):
            raise ValueError
        if clock is None and fold is not None:
            raise ValueError
        place = dict(request["selected_place"])
        for key, maximum in (("latitude", 90), ("longitude", 180)):
            raw = place[key]
            if type(raw) not in (int, float) or not math.isfinite(raw) or abs(raw) > maximum:
                raise ValueError
            place[key] = float(raw)
        result = {
            "profile": PROFILE,
            "selected_place": place,
            "civil": {
                "date": day.isoformat(),
                "time": clock.isoformat(timespec="microseconds") if clock is not None else None,
                "fold": fold,
            },
        }
        canonical(pack(result))
        return result
    except CodecError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError):
        raise CodecError("invalid_input") from None


def input_digest(request: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(canonical(pack(normalize_input(request)))).digest()


def build_payload(
    request: Mapping[str, Any],
    legacy: dict[str, Any] | None,
    kinematics: dict[int, Any] | None,
    unavailable_provenance: dict[str, Any] | None = None,
) -> dict[int, Any]:
    value = {
        0: VERSION,
        1: PROFILE,
        2: input_digest(request),
        3: pack(normalize_input(request)),
        4: 0 if legacy is not None else 1,
        5: pack(legacy),
        6: kinematics,
        7: pack(unavailable_provenance or {}),
    }
    _validate(value)
    return value


def _resource_provenance(value: Any) -> None:
    if not isinstance(value, dict):
        raise CodecError("missing_provenance")
    for name in (
        "binary_sha256",
        "binding_source_sha256",
        "planet_data_sha256",
        "moon_data_sha256",
    ):
        if not isinstance(value.get(name), str) or not re.fullmatch(r"[0-9a-f]{64}", value[name]):
            raise CodecError("missing_provenance")
    if (
        value.get("library") != "2.10.03"
        or value.get("binding") != "pysweph-2.10.3.6"
        or value.get("data_origin") != "DE441"
        or value.get("source_repository") != "https://github.com/Attory/astro-passport"
        or not isinstance(value.get("source_revision"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", value["source_revision"])
    ):
        raise CodecError("unsupported_provenance")


def _validate(value: Any) -> None:
    _finite(value)
    if type(value) is not dict or set(value) != set(range(8)):
        raise CodecError()
    if type(value[0]) is not int or value[0] != VERSION:
        raise CodecError("unsupported_version")
    if value[1] != PROFILE:
        raise CodecError("unsupported_profile")
    if type(value[2]) is not bytes or len(value[2]) != 32:
        raise CodecError("invalid_input_binding")
    if input_digest(unpack(value[3])) != value[2]:
        raise CodecError("invalid_input_binding")
    if type(value[4]) is not int or value[4] not in (0, 1):
        raise CodecError()
    if value[4] == 1:
        if (
            unpack(value[3])["civil"]["time"] is not None
            or value[5] is not None
            or value[6] is not None
        ):
            raise CodecError()
        if not value[7]:
            raise CodecError("missing_provenance")
        provenance = unpack(value[7])
        _resource_provenance(provenance)
        if set(provenance) - {
            "library",
            "binding",
            "data_origin",
            "binary_sha256",
            "binding_source_sha256",
            "planet_data_sha256",
            "moon_data_sha256",
            "source_repository",
            "source_revision",
            "status",
            "reason",
            "boundary",
        }:
            raise CodecError("invalid_availability")
        if (
            provenance.get("status") != "unavailable"
            or provenance.get("reason") != "unknown_birth_time"
        ):
            raise CodecError("invalid_availability")
    else:
        if unpack(value[3])["civil"]["time"] is None:
            raise CodecError("invalid_availability")
        legacy = unpack(value[5])
        if not isinstance(legacy, dict) or legacy.get("profile") != PROFILE or value[7] != {}:
            raise CodecError()
        if (
            legacy.get("schema_version") != "AstroPassportWesternResponse.v1-mvp"
            or legacy.get("contract_version") != "1.0.0"
        ):
            raise CodecError("unsupported_version")
        if tuple(b["body"] for b in legacy["western"]["bodies"]) != BODIES:
            raise CodecError("body_order")
        tropical = legacy["base"]["tropical"]
        if tropical["civil_input"]["time"] is None:
            raise CodecError("invalid_availability")
        _resource_provenance(tropical.get("provenance"))
        actual_input = {
            "profile": PROFILE,
            "selected_place": tropical["selected_place"],
            "civil": tropical["civil_input"],
        }
        if input_digest(actual_input) != value[2]:
            raise CodecError("invalid_input_binding")
        # Supplement v1: [lon,lat,distance,lon/day,lat/day,distance/day], flags258.
        kin = value[6]
        if (
            type(kin) is not dict
            or set(kin) != {0, 1, 2, 3}
            or type(kin[0]) is not int
            or kin[0] != 1
            or type(kin[1]) is not int
            or kin[1] != 258
        ):
            raise CodecError("invalid_kinematics")
        if (
            type(kin[2]) is not list
            or kin[2] != [258] * 11
            or type(kin[3]) is not list
            or len(kin[3]) != 11
        ):
            raise CodecError("invalid_kinematics")
        for row in kin[3]:
            if (
                type(row) is not list
                or len(row) != 6
                or any(type(number) is not float for number in row)
            ):
                raise CodecError("invalid_kinematics")
            if not 0 <= row[0] < 360 or not -90 <= row[1] <= 90 or row[2] < 0:
                raise CodecError("invalid_kinematics")


@dataclass(frozen=True, repr=False)
class VerifiedPassport:
    scientific_bytes: bytes = field(repr=False)
    profile_id: str
    kid: bytes = field(repr=False)

    def payload(self) -> dict[int, Any]:
        # Return a fresh structure, never mutable cached trusted state.
        value: dict[int, Any] = _decode(self.scientific_bytes)
        return value


def sign(payload: dict[int, Any], kid: bytes, key: Ed25519PrivateKey) -> str:
    try:
        if type(kid) is not bytes or not 1 <= len(kid) <= 64:
            raise CodecError("invalid_key")
        _validate(payload)
        cose_key = COSEKey.new(
            {
                1: 1,
                2: kid,
                3: -8,
                4: [1],
                -1: 6,
                -2: key.public_key().public_bytes_raw(),
                -4: key.private_bytes_raw(),
            }
        )
        encoded = COSE(deterministic_header=True).encode_and_sign(
            canonical(payload),
            cose_key,
            protected={1: -8, 3: CONTENT_TYPE, 4: kid},
            external_aad=AAD,
        )
        if not isinstance(encoded, bytes) or len(encoded) > MAX_CBOR:
            raise CodecError("too_large")
        return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")
    except CodecError:
        raise
    except Exception:
        raise CodecError("invalid_passport") from None


def verify(
    token: str,
    trusted_keys: Mapping[bytes, bytes],
    expected_input: bytes | None = None,
) -> VerifiedPassport:
    try:
        if (
            type(token) is not str
            or not 1 <= len(token) <= MAX_TOKEN
            or not re.fullmatch(r"[A-Za-z0-9_-]+", token)
        ):
            raise CodecError("invalid_encoding")
        raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != token or len(raw) > MAX_CBOR:
            raise CodecError("non_canonical")
        tag = cbor2.loads(raw, max_depth=20)
        if not isinstance(tag, cbor2.CBORTag) or tag.tag != 18 or len(tag.value) != 4:
            raise CodecError("invalid_encoding")
        protected, unprotected, body, signature = tag.value
        if type(protected) is not bytes or unprotected != {} or type(body) is not bytes:
            raise CodecError("invalid_headers")
        if type(signature) is not bytes or len(signature) != 64:
            raise CodecError("invalid_signature")
        if cbor2.dumps(tag, canonical=True) != raw:
            raise CodecError("non_canonical")
        headers = _decode(protected)
        if (
            set(headers) != {1, 3, 4}
            or type(headers[1]) is not int
            or headers[1] != -8
            or headers[3] != CONTENT_TYPE
        ):
            raise CodecError("invalid_headers")
        kid = headers[4]
        if type(kid) is not bytes or not 1 <= len(kid) <= 64 or kid not in trusted_keys:
            raise CodecError("untrusted_key")
        public = trusted_keys[kid]
        if type(public) is not bytes or len(public) != 32:
            raise CodecError("invalid_key")
        key = COSEKey.new({1: 1, 2: kid, 3: -8, 4: [2], -1: 6, -2: public})
        _, _, verified = COSE(verify_kid=True).decode_with_headers(raw, key, external_aad=AAD)
        payload = _decode(verified)
        _validate(payload)
        if expected_input is not None and payload[2] != expected_input:
            raise CodecError("input_mismatch")
        return VerifiedPassport(verified, hashlib.sha256(verified).hexdigest(), kid)
    except CodecError:
        raise
    except Exception:
        raise CodecError("invalid_passport") from None
