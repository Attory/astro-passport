# Proposed ACEP1 conformance tools — not an approved scientific implementation

Profile candidate `apt.sun-moon-content.v1-proposed`. AAC ADR-0007 proposal governs acceptance;
these newly authored public tools/vectors implement only fixed-input encoding tests, never astronomy.
They import no ACE/APT application implementation, read no private corpus and use no scientific data.
The Python Decimal and Node BigInt algorithms are independently implemented; standard hashing is
provided by each runtime. No runtime dependency is added. Run `uv run pytest tests/test_conformance.py`
and `node conformance/acep1.mjs`. Human approval is still required; no canonical schema tag exists.

Rules under proposal: pre-normalize strings/keys to NFC; reject lone surrogates and NFC key collisions;
restricted RFC8785/JCS with only null/bool/string/safe-integer-valued numbers/arrays/objects, UTF-16 key sorting and
preserved array order. Integral spellings such as 4.0 encode as 4; non-integer numbers are forbidden.
No raw binary64 scientific number is used in this content encoding. Duplicate wire keys are separately
rejected by the parser. Fixed UTC microseconds; null and absent differ. Exact half-even E7/E9 from
bounded decimal strings; zero has one integer representation; celestial rounded360 wraps0 and
geographic rounded+180 maps-180. No E12 quantity or Base32 representation is needed by this profile.
Raw binary64 hex remains a separate exact scientific-envelope value, never approximated by E7.

Domain: canonical JSON array `["ACEP1","apt.sun-moon-content.v1-proposed",value]`, UTF-8, SHA-256,
lowercase 64-character hexadecimal digest. This is a PROPOSED conformance digest, never NCF1/NAD1
or proof of issuer identity. Vector values (including Sun/Moon-labelled constants) are invented
numeric inputs, explicitly not calculated astronomical answers or private birth records.

Minimum eventual content object: schema/profile/numerical-policy identity, exact normalized UTC,
E7 geographic coordinates, explicit raw astronomical frame and Sun/Moon-ordered E9 longitudes.
Provider text, timezone/build provenance, participants, methods/scores/identity are excluded from
that content projection; they must not be silently removed from the separate scientific envelope.
No digest is added to the service response by these tools. Full frozen natal identity is deferred.

Generic Unicode vectors exercise long-stable characters. Runtime NFC versions must be pinned for
any later profile accepting arbitrary Unicode scientific content; current actual content fields
are ASCII closed vocabulary/timestamps/integers, not user display/query text.
