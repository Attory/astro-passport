# Accepted public API semantics — canonical release pending

Status: **AAC-accepted 1.0.0 revision 2 semantics; not a published schema release**.
request/response/provenance/error families are `.v1`. No schema tag or canonical release exists.
The limited `sun-moon.v1` profile is not full AstroIdentity, ACEP1, NCF, NAD, WPF or a fingerprint.

Accepted bytes: `accepted/schema.json`; validators: `app/contracts.py`; conformance checker:
`scripts/schema.py`. The checker preserves the exact approved bytes while comparing every
runtime definition's constraints. `contracts/manifest.json` records approval and digest.
All references resolve inside that file. Normative semantics are in `accepted/semantics.md`.
Pydantic semantic validators add invariants beyond JSON Schema (calendar validity, coherence,
finite hexadecimal numbers); the release must approve both the specification and conformance
tests. This implementation is not a required client SDK. Independent JSON/HTTPS clients only.

The sole prospective canonical publication path is the schema's `$id`:
`https://raw.githubusercontent.com/Attory/astro-passport/astropassport-schema-v1.0.0/contracts/astropassport/v1/schema.json`.
AAC must approve exact bytes/digest and rights before that immutable tag/release is created.
Record the tag's resolved Git SHA and protect deletion/retagging; clients additionally pin SHA-256.
Do not treat a floating main URL, generated OpenAPI, or private governance copy as an authority.
These accepted, unreleased schemas are AGPL-3.0-only like the repository. A separate neutral schema licence
is a rights/approval gate, not an implied Apache-2.0 grant or permission to copy private code.

## Request

`POST /v1/passports`, HTTPS only. No query string. Required headers:
`Authorization: Bearer apt1.<16 lowercase hexadecimal key-id>.<64 lowercase hexadecimal secret>`,
`X-APT-Contract-Version: 1.0.0`, and `Content-Type: application/json`.
No redirects, cookies, CORS trust or client-specific shortcuts. Clients verify certificates/hostnames,
disable credential-bearing redirects, use bounded connect/read/total timeouts and no implicit retry.
Each attempted authenticated calculation reserves quota; replay/timeout/retry is charged again.

Request contains one self-contained selected place and unresolved local date/time. All keys are
required; `attribution` and `fold` are explicitly nullable. Unknown fields are rejected recursively.
Dates: valid Gregorian 1900–2100; local time: HH:mm[:ss[.ffffff]], without zone/offset/leap second.
Fold is null unless an explicitly approved ambiguous-time choice 0 or 1 is supplied. The pinned
resolver rejects gaps and requests a choice for folds; never guesses or adjusts civil inputs.

Place preserves actual finite binary64 latitude/longitude, selected label, opaque provider/source
ID, attribution, exact query and selection index/count/limit. No coordinate prerounding. Metadata
is caller assertion, not provider authentication. No search calls, session token, provider lookup,
freshness requirement or ranking occurs here. Manual-coordinate profiles are not introduced.
No person ID, account, sex/role, A/B role, compatibility, flags, server paths or URLs are accepted.

## Response and provenance

A successful response preserves the selected input, unique IANA boundary fact and dataset
identity/version/checksum, civil input, UTC/offset/fold, tzdb and TZif identity, then ordered Sun/Moon
raw longitude records. Each longitude retains binary64 hex and the canonical nine-decimal display.
Provenance separates source revision, runtime, binding/native identity, data hashes, flags,
projection, numerical/time-scale policies and limitations. No transport ID, timing, API key or
execution timestamp enters deterministic content. Currently shape/coherence checks do NOT prove
astronomical correctness by themselves. The extracted adapter now binds decimal output to its
native binary64 value. `app/canonical.py` implements only the accepted partial Sun/Moon profile,
with its unchanged encoded `-proposed` domain; it does not emit frozen full NCF/NAD identities.

Unsigned responses are usable only as direct authenticated-client results over verified TLS from
the trusted service. Do not accept arbitrary uploaded/deserialized passports as authentic, claim
offline provenance verification or confuse TLS with signatures/storage encryption.

## Failure and version policy

Errors contain only schema, contract version and fixed code; never validation input or native text.
Calculation errors: 400 invalid transport/framing, 401 unauthorized, 406 version mismatch,
408 bounded timeout, 413 oversized, 415 media/encoding, 422 malformed/invalid input, 429 quota,
503 disabled/busy/security-state unavailable/science unavailable, 500 unexpected failure.
Scientific failures use the exact accepted `accepted/errors.json` mapping: 422 for boundary/
civil ambiguity, no-match, gap and invalid fold; 503 for unavailable artifacts/runtime; 500 for
integrity/invalid-artifact/native/fallback/invalid-result failures. No partial passport is returned.
Absent routes/methods use framework 404/405; operational health uses its own
small envelope. These are not calculation error responses.
`forbidden` is reserved for a future reviewed scope distinction, not an emitted 403 in this scaffold;
the only configured scope is `passport:calculate`.

The server currently supports exactly `1.0.0` in both header and body. No implicit downgrade or
additive unknown-field acceptance. Future compatible releases need explicit support matrices and
conformance tests; incompatible changes require a new major route. Scientific profile, datasets,
numerical policy and source SHA remain separate from API version. Limits are operational policy,
not astrological constants. **Default disabled; missing artifacts/build/runtime prerequisites
fail readiness closed. Scientific implementation and parity evidence are under review; no
deployment or external activation is authorized.**
