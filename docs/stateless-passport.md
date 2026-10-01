# Additive stateless signed passport — candidate

2026-10-01 user-authorized custody/technical direction, AAC ADR0010 and additive
implementation contract in isolated codex/stateless-passport-20261001. Existing
accepted legacy scientific profiles are preserved, not redefined. This candidate
does not resolve CP006/CP003 or activate members. The later 2026-10-01
publication authorization grants Apache-2.0 to the new neutral codec/schema
only, with exact rights/source evidence required before release.
Base24f24000b735df8700e6eab3ee4ad46a9be166a3; source checkpoint recorded at commit.

## Service boundary

POST/v2/passports, X-APT-Contract-Version:2.0.0, strict
AstroPassportCompactRequest.v1 with existing selected-place snapshot and civil
date/time/fold. Profile remains western-synastry-core.v1-mvp.200 returns ONE JSON
string: unpadded Base64url(COSE_Sign1(deterministic CBOR)), Ed25519 configured kid,
no compression. Shared passport_codec freezes the field table/golden vectors.
Unsupported versions/fields, nonfinite results, wrong returned flags, missing
ephemeris and untrusted/malformed keys fail explicitly. No client permanent ID.

Actual legacy facts/settings/provenance and binary64 values are preserved. The
additive native speed supplement runs exact Swiss flags258 for11 ordered bodies,
returning longitude/latitude degrees, distance AU and daily rates. Existing flags2
positions, E9 strings, native Lahiri calculation, Placidus/angles and UTC→TT/UT1
remain unchanged. No sidereal shortcut or alternate house system. Unknown time
returns signed unavailable resource/boundary provenance, never noon or guessed facts.

APT holds inputs/results only transiently, never in SQL, logs, persistent caches or
jobs. Existing operational quota/auth state contains no member payload. Unbubble
owns durable work, input/result association and approved account-lifetime custody.
Signature proves origin/integrity; numerical references establish correctness.

## Configuration and compatibility

Existing APT_API_ENABLED, APT_KEYS_FILE, APT_QUOTA_FILE and APT_SCIENCE_DIRECTORY.
New APT_SIGNING_KEY_FILE (private operator-provisioned Ed25519 PEM) and
APT_SIGNING_KEY_ID. Private key never in Git/report/logs. Consumers configure public
keys offline, retaining older public verification keys. Missing signer disables/v2
without disabling a healthy legacy/v1 service. No routine natal expiration.

Start the existing factory with uv run --frozen python -m uvicorn app.main:app,
using the existing protected TLS/proxy configuration. Docker uses nonroot10001,
no access logging/proxy-header trust, no writable science resources. New
/v2/health/ready and /v2/health/version /v2/source expose operational evidence.
Operator must pin an actual source revision through existing image build machinery.

Rollout must be additive: existing ACE HTML validates APT source24f2400. Route only
/v2/* to a new candidate instance; leave/v1/roothealth/source identity unchanged.
Review aggregate resource/quota/source-offer isolation. No existing client key,
quota database or source offer may be silently reset or replaced. No deployment yet.

## Verification and reproducibility

Native direct comparisons at1900/2000/2100, DST folds and polar house unavailability,
legacy byte equality, all existing numerical/failure/reference cases. API tests cover
authenticated admission, signed input binding, unknown time, quota/log payload absence.
Shared offline conformance verifies4 frozen synthetic signatures, not mathematics.
Full make check245 tests passed/no skips with pinned public artifacts before the
final additional runtime-licence drift check; focused compliance28 tests then passed.
The final full rerun must cover the exact candidate. No old test evidence for later
runtime changes is claimed. Current source manifest447 artifacts/134Cargo crates;
full offline audit/notices and22-runtime-wheel licence closure regenerated/validated.
See compliance/README.md; binary activation still requires exact public source offer.

Clean-revision local measurement command (not a hosted performance claim):

```sh
uv run --frozen python -m scripts.benchmark_portable \
  --artifacts /absolute/pinned-science-artifacts \
  --output /absolute/new-apt-measurements.json \
  --synthetic-exchange /absolute/new-synthetic-signed-exchange.json
```

Four original synthetic cases, bounded repeats3; reports actual calculation/sign/
verification latency and encoded size. Only synthetic signed outputs/public keys
are written for the separate ACE conformance probe; private keys not retained.
This maintainer benchmark is not a service persistence feature. Production/member
data must never be supplied. Independent review, authenticated integration, hosted
measurements and reviewed rollout remain pending at this checkpoint.
