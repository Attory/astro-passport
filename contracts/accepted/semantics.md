# AstroPassport 1.0.0 proposal revision 2 — field semantics

Status: Proposed, not accepted or published. Exact candidate bytes are `schema.proposed.json`;
the generated field catalogue expands every scalar/atomic-array path. All defined fields are
required on the wire, including error schema/version. Nullable is explicitly declared with null;
missing is not null. Unknown fields and duplicate JSON object keys are rejected at every level.
No defaults silently fill missing wire data. UTF-8 JSON only; nonfinite numbers are forbidden.

This proposal corrects the public scaffold's incomplete provenance, not its running implementation.
The authoritative prospective `$id` remains the single URL specified in AAC ADR-0002. Version/tag
1.0.0 remains unreleased. Exact bytes, semantic invariants, licence and protected tag target require
human approval. No schema release or child service modification follows from this document alone.

## Inputs and selection

Request is one `sun-moon.v1` profile. `selected_place` retains provider slug, opaque source ID,
display name, attribution (required nullable), query, requested_limit (1..10), selected_index and
result_count. `0 <= selected_index < result_count <= requested_limit`. Source ID/query/display
cannot be blank. These are caller assertions, not signatures or proof of GeoNames origin.
Strings retain the actual validated selected values: no NFC/trim/casefold or re-query at this wire
boundary. Legacy ACE validation has already trimmed surrounding query/display/attribution whitespace;
the legacy adapter must preserve those validated values and reject unequal raw/selected queries
BEFORE HTTP. New wire inputs do not bypass that old acceptance rule. No manual-coordinate profile
or mandatory search session is introduced. Synthetic fixture provenance is for tests only.

Coordinates are finite binary64 decimal JSON numbers in degrees, latitude [-90,90], longitude
[-180,180]. Decode to nearest binary64, reject out of range/nonfinite, retain exact bits (including
negative zero) for replay and comparison. A round-trippable decimal JSON spelling is mandatory for
clients; no identity E7 rounding before geometry lookup. No input sex/role/account/A-B, timezone,
source URL/path, native flags, scoring or method fields.

Civil date is strict Gregorian YYYY-MM-DD, local year 1900..2100. Input time accepts
HH:mm[:ss[.ffffff]] without zone, offset, leap second or implicit fold. Missing seconds/microseconds
mean exactly zero, not unknown. `fold` is required nullable integer 0/1 (not boolean). Null for a
unique time; folds require an explicit choice; gaps reject. Unnecessary fold on a unique time
rejects. Response civil_input uses normalized HH:mm:ss.ffffff; exact date/clock meaning preserved.

## Facts and provenance

Boundary success: schema timezone-boundary.v1, outcome unique, exact registered IANA ID from the
pinned catalog. Boundary provenance retains dataset/release/variant, manifest/archive/geometry/
catalog hashes, planar resolver, Shapely/GEOS/NumPy/Python/target, ODbL licence/URI and attribution.
It must equal the approved retained runtime inventory, not arbitrary client strings. Failure never
selects among polygons. Boundary/no-match/ambiguity return distinct errors, no partial passport.
Detailed reason/candidate-ID lists are intentionally absent from public errors; retain them in
private stage-level conformance evidence. This is not a claim those omitted diagnostics can be
compared through the public API. The comparator records this explicit information boundary.

Civil facts: exact UTC `YYYY-MM-DDTHH:mm:ss.ffffffZ`, integer offset_seconds (-86400,86400), unique
or explicit_fold resolution with coherent nullable fold. UTC + offset equals supplied local time
exactly; result is verified against pinned rules before astronomy. Provenance retains IANA version,
build policy, compiled archive/source/TZif hashes, resolver/Python/calendar/POSIX policy and historical
assurance. Civil limitations are ordered exactly: modern-geography-not-date-specific-jurisdiction;
then pre1970-records-have-limited-assurance if before1970 OR post-release-rules-are-not-a-prediction-guarantee
if after2026-07-08. No current wall clock affects replay. No historical truth claim from modern geography.

Bodies: exactly Sun then Moon, one each. Decimal longitude is a string with exactly nine digits
after the decimal point, range [0,360), normalized zero. Retain canonical Python binary64 hex as
well, range [0,360); it is not a substitute for canonical scaled integers. Decimal MUST equal
Decimal(shortest round-trippable binary64 decimal) quantized half-even to 9 places, rounded360→0.
Do not quantize the exact binary rational instead. No uncertainty/accuracy claim from 9 decimals.

Swiss provenance retains ephemeris.v1, swiss-isolated.v1, distribution pysweph-2.10.3.6, Swiss2.10.03,
native/source/data hashes, DE441, requested flag2 and returned [2,2], frame, numerical/time/delta-T
policies, exact runtime and canonical finite TT/UT1 JD hex (2400000 < value <2490000). UTC is the
same verified civil UTC, not a fake TT input. Source repository is the fixed public APT URL; revision
is the immutable actual 40-lowercase-hex build SHA, never unknown, environment override or client input.
The API/schema/scientific profile/data/runtime/source identities are separate fields.

Astronomical limitations retain order: modelled-ut1-not-measured-earth-orientation, then the
pre1972-proleptic-utc-used-as-ut1-proxy entry before1972 OR leap-table-frozen-after-2016-not-a-future-prediction
from2017. The known1972 model seam is unchanged; no smoothing, new leap table or EOP interpretation.
Native warnings are hard failures, not discarded warnings or successful partial results.

The serialization label astro-passport-json.v1 names the scientific wire envelope, NOT ACEP1.
The separate proposed ACEP1 content projection excludes provenance and provider text; no NCF/NAD
is emitted. Source/build changes may change artifact digests without changing content. No signature
or offline authenticity is claimed; unsigned responses are trusted only directly from authenticated
TLS service interactions. Ordinary logs contain neither inputs, outputs, hashes nor diagnostics.

## Errors, transport and compatibility

Error fields are schema_version AstroPassportError.v1, contract_version 1.0.0, fixed `code`; no
detail/input/stack/native message/person/stage echo. Original internal error categories are in the
explicit error-mapping table; deployment/state/native failures remain distinguishable from no-match.
The exhaustive machine-readable `errors.json:wire_status` table assigns every code its HTTP status.
`invalid_request` is 400 for transport/framing/header/query violations, 422 for body JSON/schema/
semantic input violations; every other code has exactly one status. `forbidden` is 403 reserved,
not currently emitted. Nonliteral dispatch instructions have their own field, never `new_code`.
No automatic
retry; every admitted attempt consumes quota. Request header and body version must both be1.0.0.

All auth/TLS/body/quota/zero-work/privacy gates of ADR-0003 remain. No body/query in logs, no query
credentials, no redirects carrying auth, no wildcard CORS, no public admin/OpenAPI. Computation
credentials do not protect public source/schema access. This draft adds no operational activation.
Fixes before release change proposal/hash; after release use new immutable versions, never retag.

Schema alone cannot prove calendar validity, finite hex/canonical forms, trusted production or the
derived facts' consistency. These semantic validators and reference tests are mandatory before a
future implementation is accepted. Existing APT scaffold does not yet implement this revision.
In particular, this AAC local suite checks schema shapes, not runtime duplicate-key parsing or
binary64-shortest-decimal production. Those remain explicit implementation/conformance obligations.
