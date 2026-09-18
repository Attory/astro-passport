# CP-010 additive Lahiri MVP candidate

Authority: explicit human CP-010 product/implementation approval. This is an
opt-in MVP candidate, not a silent amendment to AAC's accepted tropical contract.
Base: e0f25379079645a73d67c5f54c0e1290521083e0. No scientific dependency upgrades.

`POST /v1/passports`, existing authentication/version/body/quota controls, accepts
the additional `sun-moon-lahiri.v1-mvp` profile. Date, selected-place and fold input
semantics are unchanged. A new `AstroPassportLahiriResponse.v1-mvp` envelope retains
the complete original tropical response under `tropical`, plus one `sidereal` fact.
Old requests still produce only the old response. Old schema, encoding, profile
and conformance fixtures are unchanged. Delivery source SHA necessarily identifies
the running revision; it is excluded from canonical scientific content as before.

## Scientific policy

`swiss-lahiri-apparent-moon.v1-mvp`: geocentric apparent Moon, ecliptic of date,
Swiss SIDM_LAHIRI (1), no user epoch or sidereal option bits. The existing pinned
UTC-to-TT policy supplies the same TT instant as tropical calculation. Requested
flags are SWIEPH|SIDEREAL (65538); returned flags must be exactly 65602 (Swiss adds
NONUT). No Moshier fallback or other sidereal system is accepted. The isolated
fresh worker sets the mode explicitly. No process-global state reaches another
request. Files, binding, binary, delta-T and leap provenance are shared with the
retained tropical envelope and remain exactly pinned.

The displayed true ayanamsha includes nutation: `get_ayanamsa_ex(TT, SWIEPH)`.
Its returned flag must be 2. Native sidereal Moon comes from `calc`, never an ACE
or hand-written ayanamsha approximation. An internal circular-difference check
of tropical Moon minus this ayanamsha against the native sidereal result rejects
differences over 1e-10 degrees. This is an algorithm-consistency bound, NOT an
epsilon for migration parity; existing binary64 parity remains exact.
Reference: [Swiss programming manual, sidereal functions](https://www.astro.com/swisseph/swephprg.htm#_Toc112771371)
(section 12.2; with/without-nutation ayanamsha and SIDEREAL calculation guidance).

Both angles retain canonical binary64 hex and the existing shortest-decimal,
9-decimal-place half-even representation, with rounded 360 mapped to zero.
No sign/nakshatra/pada or compatibility tables are produced by APT.

## Content identity and versioning

Domain `apt.sun-moon-lahiri-content.v1-mvp` uses the existing restricted-JCS/NFC
ACEP1 primitive and SHA-256. Content starts with the existing tropical content
fields, changes schema/profile to the new explicit identities, and adds Lahiri
system/mode/policy, ayanamsha kind/E9 and Moon E9. No source revision, hostname,
personal label or wall-clock timestamp enters the content. Old content is
independently recoverable byte-for-byte from the nested tropical response.
Missing/extra/null/unknown fields, incompatible flags and inconsistent angle
representations fail closed. The generated candidate JSON schema is retained in
`contracts/mvp/lahiri-v1/schema.json`; it never replaces canonical v1 publication.

No personal human regression record belongs in this public repository. Public
tests use independently synthetic dates/places. Ashtakuta methodology stays in
private ACE. Deployment and exact-revision Corresponding Source evidence must
be recorded after CI and source reproduction, not inferred from implementation.
