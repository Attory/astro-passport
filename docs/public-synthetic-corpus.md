# Public synthetic scientific corpus specification

Specification identity: `apt-public-synthetic-corpus-spec.v1-proposed` (accepted bytes retain suffix).
Executed public reference: `tests/data/public-scientific-reference.v1.json`, 23 artificial cases,
13 successes and 10 classified failures. SHA256:
`00b09dbebcc61bc4ae4a3d28c3ebb2b19af66f58c0406caef8a0b5a66013a826`.
The source/image and per-checkpoint HTTPS measurements are in `extraction/ledger.md`.
All inputs below were authored as artificial examples, not copied or de-identified private births.
Named geography is a coverage label, not a person's birthplace or a claimed provider search result.

| Coverage | Synthetic input / required selection |
| --- | --- |
| Saint Petersburg | latitude 59.93, longitude 30.31; 1976-06-15 12:00 |
| Krasnoobsk / Novosibirsk | latitude 54.92, longitude 82.99; 1985-02-15 12:00 |
| Sydney summer / winter | latitude -33.87, longitude 151.21; 2000-01-15 / 2000-07-15 12:00 |
| Sydney fold | same coordinates; 2020-04-05 02:30, separate null/0/1 choices |
| Sydney gap | same coordinates; 2020-10-04 02:30 |
| Boundary / ambiguity | certify an actual edge and overlapping interiors against pinned geometry; do not guess rounded borders |
| Ocean / no-match | certify 0,-140 against comprehensive/no-oceans geometry |
| Dateline / poles | exact ±180 longitude / ±90 latitude and adjacent finite binary64 values |
| Local date range | 1900-01-01 and 2100-12-31; reject local years outside range |
| UTC date edge | artificial local clocks on either side of a verified UTC date transition |
| Time-policy seams | before 1970, the retained 1972 model seam, and 2017/future limitations |
| Numerical encoding | independent fixed numeric inputs in conformance/vectors.json; NOT astronomical expected positions |
| Artifact failure | controlled copies with missing data, changed bytes or wrong native identity |
| Worker / concurrency | bounded parallel repetitions, explicit busy/timeout/crash/native-warning outcomes |

Use clearly identified synthetic-provider snapshots with explicit query/index/count; do not invent
GeoNames authenticity. Selection uses actual finite unrounded coordinates. No live place search or
external timezone service participates in expected-value derivation.

Before generating scientific answers, approve exact source/image/runtime/data identities and the
reference protocol. Certify geometry memberships independently. Run the approved unchanged reference
scientific path in an isolated reference environment; retain original evidence privately. Publish
only reviewed scientific outputs for these independently public inputs after rights/notice checks.
Record immutable case IDs, corpus byte hash, derivation-tool version and exact runtime/native/data
identities. Independently corroborate historical civil-time and ephemeris policy seams. A migration
agreement proves equivalence, not independent astronomical accuracy.

After authorized extraction, compare through the actual authenticated HTTP API with the approved
leaf comparator. Missing/extra/unclassified leaves, wrong order, errors, nulls and limitations are
not ignored. Same-platform science is zero-tolerance; no epsilon is authorized. Internal diagnostics
not exposed on the public API require separate approved offline stage evidence, not a privileged
ACE-only endpoint. Public builds/CI must remain independent of private repositories or migration data.

Private migration corpus design/custody is separate. This public file contains no private payload,
person-derived digest, restricted case identifiers, credential, implementation code or private
methodology. Scientific expected outputs were derived from the unchanged frozen reference after
explicit extraction authorization. Measurements apply only to the image/revisions in their evidence
records. Fault-injection and real-process resource-limit tests are additional non-astronomical
coverage, not invented scientific goldens or claims that all faults were measured against old ACE.
No service deployment is authorized.
