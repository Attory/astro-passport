# Lens B Review — Pinned Geographic Timezone & Historical Civil-Time Correctness

**Scope reviewed:** `app/science/boundaries/*`, `app/science/civil/*`, `app/science/raw_input.py`, `app/science/pipeline.py`, `scripts/build_tzdb_artifact.py`, `scripts/scientific_artifacts.py`, `scripts/public_corpus.py`, `tests/test_science.py`, `tests/test_public_reference.py`, `tests/data/public-scientific-reference.v1.json`, `contracts/accepted/{semantics.md,tbb-manifest.json}`, `docs/extraction/*`, CI/Docker config, at exact head `3617ab0c208cbd56927e0b84574b778e832ca8a1`.

This is a review of what is **implemented in this commit** (boundary resolution, civil-time replay, fold/gap handling, limitations disclosure). It is **not** a review of, and does not certify, any future deployment, ACE cutover, schema tag publication, or activation — none of those are claimed by the material and README/docs/Dockerfile all explicitly disable them (`/health/ready` gate, no `/docs`/`/admin`, `vps_deployment: not performed`, `distribution: not published`).

## Findings

**MEDIUM — No source-of-truth for cross-file pinned dataset identity constants**
Files: `app/science/boundaries/identity.py`, `app/science/boundaries/tbb.py`, `app/science/civil/contracts.py`, `contracts/accepted/tbb-manifest.json`, `scripts/scientific_artifacts.py`.
The TBB release/archive/geometry/catalog/manifest SHA-256 values and the tzdb archive hash are hand-duplicated as literals in five separate locations. In this snapshot they are internally consistent (cross-checked: `MANIFEST_SHA256`, `ARCHIVE_SHA256`, `GEOMETRY_SHA256`, `CATALOG_SHA256`, `TZIF` all match across files). Impact: any future dataset rotation (new TBB/tzdb release) risks silent drift between files if only some are updated, which the current model validators (`coherent_outcome`, `pinned_provenance()` equality check in `validate_registered_boundary_fact`) would catch at runtime (fail-closed), but only after the fact. Bounded repair: consolidate these constants into a single generated/reviewed constants module imported by all four sites, with a CI check diffing them against the manifest; purely a maintainability change, not a policy or byte-content change, so it does not reopen any human-approved gate.

**LOW — Defensive exception handling gap around final `ResolvedCivilTime` construction**
File: `app/science/civil/tzdb.py`, `PinnedCivilTimeResolver.resolve()`.
The try/except around zone lookup and fold-candidate computation catches `(ValueError, KeyError, OSError)`, but the final `return ResolvedCivilTime(...)` call (which re-runs the model's `coherent` validator) is outside that block. A pydantic `ValidationError` raised there would not be mapped to a `CivilTimeError`, and `PassportScience._calculate` only catches `(TimezoneBoundaryError, CivilTimeError, EphemerisError, NatalError)` (`app/science/pipeline.py`), so such an exception would propagate unmapped. In practice this is low-likelihood: TZif offsets are always whole seconds by format definition, and `local_date`/`local_time` are already validated upstream, so the coherence check should hold for all reachable inputs in the current corpus. No failing case was observed in the provided evidence. Bounded repair: wrap the final construction in the same try/except (or a dedicated one) mapping any `ValidationError` to `CivilTimeError(ARTIFACT_INVALID)`, and add one explicit regression test forcing a hypothetical mismatch (e.g., via a monkeypatched offset) to prove the fail-closed path. Non-blocking; does not touch numerical policy or tolerances.

**LOW — Fold/gap public corpus coverage is narrow**
Files: `scripts/public_corpus.py`, `tests/data/public-scientific-reference.v1.json`, `tests/test_science.py`.
Ambiguous (`civil_ambiguous`), nonexistent (`civil_nonexistent`), and unnecessary-fold (`invalid_fold`) cases are all exercised only against `Australia/Sydney` in 2020. There is no synthetic case for a Northern-Hemisphere fall-back ambiguity (e.g., `America/New_York`), a fractional-hour offset zone (e.g., +5:45/+5:30 zones), or a zone with historical sub-standard offsets. The underlying resolver logic (`_utc_candidates`) is zone-agnostic and generic, so this is a coverage gap rather than a demonstrated defect, but it leaves the "complete leaf classification" goal referenced in `docs/extraction/checkpoint.md` only partially exercised for the fold/gap dimension specifically. Bounded repair: extend `scripts/public_corpus.py` with one Northern-Hemisphere fold pair and one non-hour-offset zone case; re-run `scripts.scientific_artifacts` + `make check` to regenerate golden answers via the same unchanged reference process already used for the existing cases.

**OBSERVATION (positive) — Boundary seam/ambiguity tests derived from the live pinned dataset**
File: `scripts/public_corpus.py`.
Rather than hardcoding coordinates, the corpus generator locates an actual vertex of the first geometry (for the "boundary" case) and searches the real STRtree for a genuine polygon-overlap interior point (for the "ambiguous" case), asserting the expected status before adding it. This gives real assurance that `boundary`/`ambiguous` states are reachable against the actual pinned TBB 2026c artifact rather than only against synthetic code paths, and both cases are present with matching expected outcomes in `tests/data/public-scientific-reference.v1.json` (`certified-dataset-vertex`, `certified-dataset-overlap`).

**OBSERVATION — "Boundary wins over ambiguous" is an intentional conservative rule**
File: `app/science/boundaries/tbb.py`, `_outcome()`.
If any matched geometry is touched-but-not-contained, the whole point is classified `boundary` even if it is also strictly interior to a second candidate zone; only when no geometry is boundary-touching does multi-candidate interior overlap classify as `ambiguous`. This matches the documented contract ("no partial passport", reason/candidate diagnostics withheld from the public API per `contracts/accepted/semantics.md`) and is not a defect, but reviewers should be aware this is a chosen conservative precedence, not a completeness statement about which zone is "correct."

**OBSERVATION — UTC/offset edge-window consistency verified**
Cross-checking `contracts/accepted/acep1-profile.md`'s stated UTC bound ("1899-12-31 inclusive through 2101-01-02 exclusive") against the civil year bound (1900–2100 local) and real-world extreme offsets (e.g. +14 at the low end, ≈-12 at the high end) shows the window is correctly sized to prevent overflow when local-to-UTC conversion crosses a year boundary at the extremes (`tests/data/public-scientific-reference.v1.json` "year-minimum"/"year-maximum" cases exercise exactly this). No inconsistency found.

**OBSERVATION — No policy/tolerance changes detected**
All comparisons in the reviewed civil/boundary code are exact (`==`), `offset_seconds` remains a strict integer with the unchanged `(-86400, 86400)` exclusive bound, fold is a strict nullable 0/1, and all provenance/hash fields are `Literal`/pattern-pinned with no epsilon anywhere. The parity manifests (`docs/extraction/https-parity-*.json`) report `zero_tolerance: true`, `canonical_bytes_equal: true`, and zero mismatches across all comparator classifications, consistent with the zero-tolerance requirement. I did not execute anything; this is a reading of the committed values only.

**OBSERVATION — Extraction scope matches the 16 approved origins**
`docs/extraction/origins.json` maps 13 of 16 listed ACE origins to `app/science/*`/`scripts/*` destinations and explicitly leaves 3 uncopied (place-search plumbing), each annotated "no scientific algorithm change." No synastry, scoring, participant/sex, or compatibility code appears anywhere in the boundary/civil-time material reviewed. This is consistent with the human-approved extraction/parity gate and does not appear to reopen it.

## Evidence limitations

- I did not execute any code, tests, Docker build, or CI. The exact-head CI record (`35157967778`, conclusion `success`) is treated as reported, attested evidence only, not independently reproduced.
- I cannot independently verify that the per-file SHA-256 "Reference revision" tags in `app/science/boundaries/*` and `app/science/civil/*` actually match byte-for-byte private ACE source at `18a3776bc1ab1dc52212b4de48a0df36709d72d2`; only internal consistency of the hashes across the *public* files supplied here was checked.
- The correctness of the underlying pinned tzdata 2026c and TBB 2026c *content* (i.e., whether the real-world zone rules/geometries themselves are accurate) is outside what this file set can establish; only that the code consumes them deterministically and fails closed on integrity mismatch was verified.
- No FastAPI route/exception-handler code was in scope, so I cannot confirm how an unmapped exception (see MEDIUM/LOW findings above) would ultimately surface at the HTTP layer.
- This is a technical/documentation review, not a legal or compliance certification of licensing, rights, or governance approval validity.

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

The pinned-timezone and civil-time extraction is internally consistent, fails closed on integrity/runtime mismatches, preserves zero-tolerance exactness with no policy changes, keeps fold/gap/ambiguity/boundary semantics aligned with the accepted contract text, and stays within the scope of the already-resolved human extraction/parity gate. The identified items (constant duplication, one narrow defensive-coding gap, and corpus coverage breadth for folds/gaps) are maintenance/hardening follow-ups, not blockers, and none require reopening the AAC baseline, the normative contract checkpoint, or the extraction authorization.
