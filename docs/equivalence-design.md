# Equivalence harness design — not yet executed

Two independent corpora: a restricted migration corpus retained outside public Git/CI, and an
independently authored public synthetic corpus containing no copied/redacted private cases. Public
build/conformance requires no private fixture. New geographic labels below are coverage targets,
not real-person births or asserted reference results.

Harness process: retain immutable baseline scientific runtime/image/artifacts; run its approved
scientific path in a restricted subprocess; send identical selected inputs to the new service via
its actual authenticated HTTPS API. No cross-repository imports or shared DB. Retain both complete
outputs in the appropriate corpus store plus explicit comparator report. The public suite separately
uses self-contained synthetic fixtures and approved expected outputs. Never log birth payloads or
private per-case fingerprints in normal CI. No reference runs have been made by this scaffold.

## Proposed comparator mapping (approval required)

| Old scientific field group | Candidate APT field | Rule |
| --- | --- | --- |
| actual selected provider/id/label/attribution/query/index/count/limit | selected_place | exact strings/integers/null |
| selected latitude/longitude | selected_place.latitude/longitude | exact binary64 hex after roundtrip; no E7 preround |
| unresolved local date/time, explicit fold | civil input and civil_input | same semantic date/time and retained precision; detailed byte encoding approval pending |
| boundary outcome/zone/resolver/dataset pins | boundary or typed error | exact outcome, zone, versions/checksums |
| UTC, offset, fold and tzdb/TZif | civil | exact instant/microseconds/offset/choice/checksums |
| native/body inputs, TT/UT1, flags, projection, data, limits | provenance | exact runtime/hex/policy/data identities |
| Sun/Moon raw binary64 and canonical E9 output | bodies | exact ordered bodies, hex and approved nine-decimal representation |
| repository/source revision | provenance.source_repository/source_revision | explicit expected old→new identity substitution, retain both |
| transit/instance metadata | separate delivery report | enumerated outside content, never blanket-ignore metadata |
| content/manifest digests affected by source/wire change | future comparison report | retain both and enumerate derivation; never force equal NAD |

This is a group-level design, NOT the complete approved leaf-path comparator or ACEP1 profile.
Before scientific extraction approval, inventory every old/new leaf including error/absence/null,
ordering, canonicalization, limitation fields and derivatively changed digests. Fail on unclassified
leaves. Preserve the current client's raw-place-query versus selected-query coherence rejection in
the migration adapter: both must match before creating the request. The wire has one selected query;
this simplification must not silently make inconsistent legacy inputs acceptable.

Same-platform extraction has **zero tolerance**: exact discrete facts, binary64 intermediates and
canonical decimal outputs. Equal canonical identity requires exact approved bytes, never epsilon.
For a new platform, measure absolute/ULP errors with units and circular-angle distance; no nonzero
tolerance is approved. A new native runtime identity and human scientific qualification are required.
Canonical mismatch remains different content even if future numerical qualification passes.

## Synthetic coverage to author and independently verify

- Saint Petersburg geography, artificial local noon on 1976-06-15.
- Krasnoobsk/Novosibirsk geography, artificial local noon on 1985-02-15.
- Sydney summer/winter geography; 2020-04-05 02:30 fold (null/0/1); 2020-10-04 02:30 gap.
- Sun/Moon positions across UTC date edges, 1900/2100 range limits, microseconds and repeated runs.
- Boundary/intersection/ambiguity/no-match, ocean, poles/dateline, exact and adjacent binary64
  coordinates; use dataset-certified geometry, not rounded guessed border coordinates.
- Pre-1972 UT1 proxy, documented 1972 seam and frozen-future-leap limitations retained unchanged.
- Half-even ties, signed zero, 360/0 wrap, E9 thresholds; malformed/nonfinite/out-of-range input.
- Missing/corrupt artifacts, fallback/native warnings, concurrent/timeout/worker failure.
- Approved full ACEP1 vectors in an independent language once full profile is authorized; the current
  Sun/Moon JSON is not such a vector and cannot stand in for one.

Coordinates and expected scientific answers are deliberately not fabricated in this design. Pin
them with case provenance and independent expected-value review during the authorized harness phase.
Compare old/new science separately from private downstream methodology. Agreement proves migration
equivalence, not independent astronomical accuracy. Gate report records exact runtimes, artifact
hashes, corpus revision, comparator version, all mismatches, CI and independent-review verdict.
