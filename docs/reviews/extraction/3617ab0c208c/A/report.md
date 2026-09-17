# Independent Review — Lens A (Extracted-Source Provenance, 16-Origin Authorization, No Private Method/Cross-Repo Runtime, AGPL/Source Separation)

**Target:** `3617ab0c208cbd56927e0b84574b778e832ca8a1` | **Base:** `dae015fd069308e408280d980e10ff72ed722488` | **AAC baseline:** `59500ec0951e082dd4c3984999b8a42fe4ce53c8` | **Contract checkpoint:** `75092aac79c39c6893900a0758ab176a47fe0c7a` (human-approved, not reopened here)

This review is confined to the supplied committed material. No independent execution was performed; CI result for the exact head (`35157967778`, conclusion `success`) is treated as attested evidence, not reproduced.

---

## Scope discipline confirmed up front
- I am reviewing **implemented extraction and isolated parity artifacts as committed**, not asserting that any deployment, ACE cutover, schema-tag release, or public binary distribution has occurred. None of those gates are claimed complete anywhere in the material, and several documents (`README.md`, `docs/governance.md`, `docs/extraction/checkpoint.md`) affirmatively disclose that they are *not* authorized/complete.
- The human-approved gates (rights attestation for 16 origins, contract checkpoint `75092a...`, extraction/parity authorization) are treated as resolved and are **not re-litigated**.

---

## Findings

### HIGH (positive control — satisfied) — Exactly-16 narrow origin authorization is structurally enforced
**Files:** `docs/extraction/origins.json`, `tests/test_extraction_boundary.py::test_authorized_origins_and_no_cross_repository_runtime`
`origins.json` lists exactly 16 entries (13 with destinations, 3 explicitly `null`/not-copied), matching `docs/extraction/checkpoint.md`'s "Thirteen … three are not copied" and `docs/extraction/ledger.md`. The test asserts `len(record["origins"]) == 16` and cross-checks `aac_baseline` against `app.build.AAC_BASELINE`, and that each destination file's committed SHA-256 provenance string appears in its own header.
**Impact:** Scope creep beyond the attested 16 origins would break CI, giving a mechanical (not just documentary) tripwire.
**Residual risk (LOW):** This is a same-PR self-referential guard — an author who wants to add a 17th origin edits `origins.json` and the file simultaneously; the test cannot detect *unauthorized* additions, only *inconsistent* ones. Bounded repair (nonblocking): require the origins count/hash to also be checked against a value recorded in a separately reviewed governance document (e.g., pin `origins.json`'s own SHA-256 inside `docs/governance.md` next to the checkpoint hash) so a single PR cannot silently expand scope.

### HIGH (positive control — satisfied) — Per-file provenance headers are consistent and hash-anchored
**Files:** every file under `app/science/**`, matched 1:1 against `docs/extraction/origins.json`.
Each extracted file carries `# Extracted under rights-holder authorization from <origin path>` + `Reference revision: 18a3776bc1ab1dc52212b4de48a0df36709d72d2; SHA256: <hash>`, and every hash I could check (raw_input.py, boundaries/{contracts,identity,tbb}.py, civil/{contracts,tzdb}.py, ephemeris/{contracts,identity,adapter,worker}.py, natal/{facts,service}.py) matches the corresponding `origins.json` entry exactly. All cite the same frozen reference revision, consistent with "ACE remains unchanged."
**Impact:** Strong, auditable provenance trail from a single frozen private commit to each public destination file.
**Evidence limitation:** I cannot independently verify that the cited SHA-256 values actually correspond to real bytes in the private ACE repository at that revision — that repository was correctly not supplied. This traceability is only as strong as the underlying (already human-approved) rights attestation; it is not something a public reviewer can re-derive, by design.

### MEDIUM — No committed content for several load-bearing scripts referenced by CI/origins
**Files referenced but not included in evidence:** `scripts/build_tzdb_artifact.py`, `compliance/bundle.py`, `compliance/audit.py`, `compliance/release.py`, `scripts/scientific_artifacts.py`, `scripts/https_scientific_smoke.py`, `scripts/container_smoke.py`.
**Impact:** These modules implement the "acquire exact matching public sources," "audit native/OS source correspondence," and "reproduce complete exact-revision source bundle" steps that are central to the AGPL corresponding-source and no-cross-repo-dependency claims in `ci.yml`. Their absence from the reviewed material means this lens cannot independently confirm their contents don't reach into a private path or fetch from a non-public origin — I can only confirm the *workflow calls* them and that the *headline* extraction files (app/science/**) are clean.
**Bounded repair:** Include these files in the next review package, or at minimum a hash manifest of them alongside `compliance/source-lock.json`, so provenance coverage extends to the full CI dependency graph, not just `app/science/**`.

### LOW — Cross-repository import guard is a finite denylist, not a structural allowlist
**File:** `tests/test_extraction_boundary.py` (`assert not node.module.startswith(("ace.", "ais.", "app.engines.western.synastry"))`)
**Impact:** Effective for known naming conventions (`ace.*`, `ais.*`, the specific synastry module) but would not catch a differently-named private import (e.g., a future `aac.*`, `internal.*`, or a relative import that resolves outside `app/science`). Sampled files show no such imports today (only `app.build`, `app.contracts`, `app.science.*`, and pinned third-party libs), so there is no current violation.
**Bounded repair (nonblocking):** Convert to an allowlist — assert every first-party (`app.*`) import target lies under `app.science`, `app.contracts`, or `app.build`, rather than only excluding known-bad prefixes.

### LOW — `"/home/soul/"` path-leak guard is a literal string match
**File:** `tests/test_extraction_boundary.py`
**Impact:** Catches the exact local-checkout path named in `AGENTS.md` for the private AAC repo; would not catch a differently mounted path, symlink, or environment-variable-derived path. No occurrence found in the reviewed files.
**Bounded repair:** Low priority; optionally broaden to a regex for absolute paths outside the repo root.

### OBSERVATION (positive) — `-proposed` encoding suffix bytes are protected by exact hash pinning
**Files:** `tests/test_extraction_boundary.py::test_exact_accepted_contract_and_manifest_bytes`, `contracts/accepted/{semantics.md,acep1-profile.md,schema.json,...}`
The test pins exact SHA-256 for `semantics.md` and `acep1-profile.md`, both of which retain the `-proposed` identifiers (`apt.sun-moon-content.v1-proposed`, `APTCanonicalSunMoonContent.v1-proposed`) as required. Any accidental rename would fail CI immediately.
**No repair needed.** This directly satisfies "Accepted -proposed encoding suffixes MUST remain unchanged."

### OBSERVATION (positive) — Zero-tolerance binary64/canonical handling, no epsilon found
**Files:** `app/science/ephemeris/contracts.py` (`BodyLongitude.exact_projection`, `longitude_decimal`), `app/science/ephemeris/adapter.py`, `app/science/ephemeris/worker.py`
Longitude values are round-tripped through exact hex (`float.fromhex(text).hex() != text` rejects any lossy re-encoding) and quantized with `Decimal`/`ROUND_HALF_EVEN` at fixed precision — no tolerance/epsilon comparison appears anywhere sampled. The parity JSON artifacts (`https-parity-*.json`) likewise report `"zero_tolerance": true` and 0 mismatches across all classification buckets.
**No repair needed** for what was reviewed. **Evidence limitation:** these parity JSON files are self-reported records of past executions (`948f6a2`, `94c8103`), not independently executed by me, and — importantly — **neither corresponds to the exact target head `3617ab0c...`**. `docs/extraction/checkpoint.md` itself lists "actual authenticated local HTTPS migration parity … exact-head GitHub CI and independent reviews A–H" as explicit **remaining checkpoint work**, so this gap is disclosed by the project, not concealed. It should remain an open, tracked item before any parity-completion claim is made for this exact head.

### OBSERVATION (positive) — AGPL/ODbL source separation correctly implemented
**Files:** `app/science/boundaries/identity.py`, `THIRD_PARTY_NOTICES.md`
`identity.py` is explicitly dual-tagged `SPDX-License-Identifier: AGPL-3.0-only AND ODbL-1.0`, with an in-code comment that the embedded TBB catalog is "not relicensed by ACE's program grant." `THIRD_PARTY_NOTICES.md` separately documents ODbL-1.0 attribution requirements, AGPL for `pysweph`, and BSD/LGPL for `shapely`/`GEOS`/`NumPy`. This is a correct, non-conflated separation of code license from embedded open-data license.
**No repair needed.**

### OBSERVATION (positive) — No private methodology, scoring, or participant data present
Reviewed files (`raw_input.py`, `natal/facts.py`, `natal/service.py`, pipeline) contain only date/time/place-query inputs and Sun/Moon longitude outputs; no compatibility, scoring, sex/participant, or identity fields exist anywhere in the extracted code or contracts. `origins.json` explicitly documents omission of the "selected-snapshot helper" and "ACE Western wrapper schema/projection identities," and the boundary test blocks import of `app.engines.western.synastry`. This matches the narrow-scope mandate.
**No repair needed.**

### OBSERVATION — Evidence limitations for this review
- I did not execute any code, CI, or Docker build; the CI success record for `3617ab0c...` and the parity/source-correspondence JSONs are taken as given records, not verified firsthand.
- Several compliance/build scripts central to the "no cross-repository runtime dependency" and full corresponding-source claims were not in the material set (see MEDIUM finding above).
- I cannot verify the private-side SHA-256 provenance claims against the actual ACE repository, by design/restriction.
- Parity/image-source evidence in the package predates the exact reviewed head; no artifact at `3617ab0c...` itself was supplied.
- This is an engineering/documentation review only; it is **not a legal AGPL compliance certification** and does not establish enforceability of licensing conclusions.

---

## Explicit separation: implemented vs. forbidden-future
**Implemented and in scope here (reviewed as committed fact):** 16-origin extraction mapping, per-file provenance headers, boundary-guard tests, AGPL/ODbL notice separation, zero-epsilon numeric handling in code, `-proposed` byte pinning, exact-head CI success record.
**Not claimed, not reviewed as done, and correctly not present in this material:** ACE modification, schema-tag/public release, public binary distribution, network activation/deployment, client cutover, full parity sign-off at the exact target head, independent reviews A–H completion.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

Rationale: Within Lens A's scope, the 16-origin extraction is narrowly and verifiably authorized, provenance headers are internally consistent and hash-anchored, no private methodology/scoring/participant logic or cross-repository runtime import was found, AGPL/ODbL source separation is correctly implemented, and the `-proposed` suffix bytes are protected by an exact-hash CI gate. The MEDIUM and LOW items above (missing compliance-script evidence, denylist-vs-allowlist import guard, path-string guard, and the disclosed-but-still-open exact-head parity gap) do not indicate a violation of the resolved human gates and do not by themselves block this lens's approval, but should be tracked as follow-ups before any subsequent readiness or cutover claim.
