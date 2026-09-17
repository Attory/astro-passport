# Proposed minimal ACEP1 profile

Identifier: `apt.sun-moon-content.v1-proposed`; status PROPOSED, not frozen/accepted.
Existing frozen principles remain authoritative. This specifies previously undefined details for
a separate partial-content domain, not any full NatalFactSnapshot/NCF1/NAD1 or projection fingerprint.
It does not change the old ace-calculation-json.v1 serialization or scientific numerical policy.

Content keys (all required, no extras): `schema` = APTCanonicalSunMoonContent.v1-proposed,
`profile` = sun-moon.v1, `numerical_policy` = binary64-to-decimal-9dp-half-even.v1,
`utc` = fixed six-fraction-digit UTC, `latitude_e7`, `longitude_e7`, `frame` =
geocentric-tropical-apparent-ecliptic-of-date, `bodies` = exactly ordered Sun/Moon objects containing
`body` and integer `longitude_e9`. No source/build/timezone/provider text, personal identifiers,
compatibility or sex. This projection does not replace the complete scientific envelope.

E7: derive from the shortest round-trippable decimal spelling of the retained selected binary64
coordinate; exact decimal half-even at 7 places. Latitude range ±900000000 inclusive; geographic
longitude range [-1800000000,1800000000), mapping rounded+180 to-180. This is a proposed identity-
projection normalization only: retain exact unrounded coordinates for scientific lookup/parity.
E9: multiply the ALREADY verified legacy 9-place decimal by1e9 exactly; no second rounding.
Quantization primitive vectors also test shortest-decimal inputs at half-even thresholds; rounded
360 maps0. Native raw360 or negative/nonfinite longitude is rejected. E9 range [0,360000000000).
Normalize scaled signed zero to integer0; do not discard its original binary64 scientific evidence.
E12 is not used because this profile has no distance or velocity. No Base32 or frozen NCF prefix.

Domain-separated bytes: restricted JCS of the three-element array
`["ACEP1","apt.sun-moon-content.v1-proposed",content]`. NFC string/key normalization precedes JCS;
reject lone surrogates, duplicate keys and normalized-key collisions. RFC8785 UTF-16 key sorting,
UTF-8 encoding, canonical escaping, no whitespace/BOM/newline, arrays preserve order. This subset
uses only null/booleans/strings/arrays/objects and safe-integer-valued numbers (abs<=2^53-1); 4.0
and4 canonicalize as4. No raw scientific float JSON enters canonical content. Null is distinct from
absent; fixed content schema permits neither omission nor null for its required fields. Primitive
vectors exercise these distinctions without claiming a scalar is a valid whole content document.

UTC date/time is validated, offset zero, fixed YYYY-MM-DDTHH:mm:ss.ffffffZ. No timezone conversion
here, no truncation/rounding beyond six digits, no leap second. Scientific UTC bounds remain
1899-12-31 inclusive through2101-01-02 exclusive. No wall-clock timestamp in deterministic content.
Digest is SHA-256 of exactly those bytes, encoded lowercase64-hex. Hash identity is exact, not
epsilon or authenticity. Profile identity is INCLUDED in bytes, not supplied out of band.

Actual content strings are ASCII closed vocabulary; user/provider strings are outside the content
projection. Generic Unicode primitive vectors use stable NFC characters. A later Unicode-bearing
scientific content profile needs pinned normalization-version qualifications before adoption.

Independent public tools: APT `conformance/acep1.py` uses Python Decimal; `acep1.mjs` uses Node
BigInt quotient/remainder half-even and a separate serializer; `vectors.json` holds fixed inputs,
expected bytes and digests. No tool imports ACE, APT application code, Swiss or geographic data.
Python3.12.14 and Node22.22.2 are test runtimes, not a shared scientific library. Source remains
AGPL in APT; any neutral re-licensing is a separate rights/approval action.

Primary encoding reference: [RFC8785](https://www.rfc-editor.org/rfc/rfc8785). NFC is an explicit
profile pre-transform, not behavior supplied by JCS. Frozen ACE encoding has no prior exact domain
bytes to overwrite; naming and byte choices here require human approval. A safety check rejected
removing the proposed identifier before acceptance; it remains explicitly proposed throughout.
