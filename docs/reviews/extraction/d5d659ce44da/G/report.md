# Review G — Corresponding Source / Exact Image Composition
**Target:** `d5d659ce44dab90049019d0df9f8f848dd2fed33` · **Base:** `dae015fd06...` · **AAC:** `59500ec0951e08...`

## Evidence basis and limitations (stated up front)
This review is based solely on the committed files supplied (Dockerfile, `compliance/*.py`, `compliance/*.json`, `docs/extraction/*`, `contracts/*`, `THIRD_PARTY_NOTICES.md`) and the human-supplied exact-head CI result (run `35159954335`, conclusion `success`) and the human's reported execution evidence (23-case parity result; "reproduced twice SHA256 `4336febf...`"). **I did not execute any tooling.** The reported bundle-reproduction hash and the 23-case parity numbers are asserted by the user in the task framing; I have **no committed artifact at the exact target SHA** (no `docs/extraction/ledger.md` entry, `image-source-d5d659c.json`, or `https-parity-d5d659c.json`) that reproduces those numbers for independent inspection — the most recent committed checkpoint artifacts in the material shown are for `aeb0bca2857f...`. The green exact-head CI run does re-execute the identical fetch/audit/pack-twice/cmp pipeline described in `ci.yml`'s `corresponding-source` job, which is meaningful corroboration, but is not itself a visible hash I can cross-check. This is an **evidence limitation**, not a claim that the work did not happen.

I make no claim of legal certification. Findings below distinguish **implemented extraction/parity/source-tooling** (in scope) from **forbidden future deployment/ACE cutover** (explicitly out of scope and not evaluated for readiness).

---

## Findings

### MEDIUM — M1: No committed evidence artifact for the exact reviewed revision
**File(s):** `docs/extraction/ledger.md`, `docs/extraction/image-source-*.json`, `docs/extraction/https-parity-*.json`
**Impact:** The specific claims for `d5d659c...` (23/13/10 case parity, "reproduced twice SHA256 `4336febf...`") exist only in the task's human-supplied summary, not in any committed, independently-inspectable file, unlike prior checkpoints (`948f6a2`, `94c8103`, `aeb0bca`) which each have a paired `image-source-*.json` + `https-parity-*.json` and a ledger entry. Exact-head CI success at `d5d659c` re-runs the same fetch/audit/release-pack-twice/`cmp` pipeline, which meaningfully corroborates the *mechanism*, but does not surface the specific digest for review-time comparison.
**Bounded repair:** Before relying on this checkpoint for any subsequent gate, commit `docs/extraction/image-source-d5d659c.json`, `docs/extraction/https-parity-d5d659c.json`, and an updated `ledger.md` entry mirroring the format used for `aeb0bca`, so the reported hashes are independently checkable artifacts rather than out-of-band assertions.

### MEDIUM — M2: Inconsistent depth of native-binary correspondence proof (GEOS/Shapely, pysweph/Swiss) vs. NumPy/OpenBLAS/gfortran/quadmath and Rust
**File(s):** `compliance/audit.py` (`compare_sections`, `swiss_source_equal` block, `geos_build_controls` block)
**Impact:** For libgfortran/libquadmath/openblas, `audit.py` performs byte-level ELF-section equality between AlmaLinux-source-derived RPM binaries and what ships inside the NumPy wheel. For the Rust-linked pydantic-core `.so`, it independently confirms the embedded `rustc` commit/version string matches the pinned `rustc-1.98.0-src.tar.xz`. By contrast, GEOS/Shapely correspondence rests only on a `GEOS_VERSION: "3.13.1"` string found in a *build workflow YAML*, and pysweph/Swiss correspondence rests only on exact **source-file** hash equality of 27 vendored C/header files against upstream — neither includes any binary-artifact cross-check against the actual compiled `.so` shipped in the respective wheels. Full corresponding source and build instructions ARE retained for both (satisfying the baseline legal requirement), but the audit's assurance that the *shipped compiled artifact* actually derives from that exact retained source is weaker and inconsistent with the rigor applied elsewhere.
**Bounded repair:** Add an ELF section/build-id or embedded-version-string check for the compiled `libgeos_c` inside the Shapely wheel (comparable to the GEOS source-controlled build) and for the compiled Swiss `.so` inside the pysweph wheel, mirroring the existing `compare_sections` pattern.

### MEDIUM — M3: Build-control archives are hash-pinned but content-unverified
**File(s):** `compliance/source-lock.json` (`numpy-release-build-controls.tar.gz`, `openblas-libs-build-controls.tar.gz`), `compliance/README.md` ("Modification/replacement/relinking")
**Impact:** These two archives are acquired and SHA256-pinned but `audit.py` never opens or asserts anything about their contents (unlike the GEOS workflow file, which is opened and grepped for the version pin). The compliance README's specific relinking claims (ILP64 flags, wrapper patches) are therefore prose assertions, not machine-checked correspondence.
**Bounded repair:** Add a minimal automated content check (e.g., grep for the expected ILP64 build flag or patch filename) analogous to the existing GEOS check, or explicitly annotate these two entries as "acquired, not content-verified" in `correspondence.json` to avoid over-implying parity with the GEOS/Swiss checks.

### LOW — L1: Long-term availability risk for Debian snapshot-hosted sources
**File(s):** `compliance/source-lock.json` (73 `debian:*` entries), `compliance/README.md`
**Impact:** All 73 Debian source packages resolve only to `snapshot.debian.org` URLs. This is already explicitly and correctly flagged in `compliance/README.md` as an operator responsibility ("mirror/retain the bundle... rather than relying forever on upstream URLs"), and no distribution has occurred, so this is not a current defect — only a pre-distribution durability risk under AGPL's "available for as long as needed" expectation.
**Bounded repair:** Before any binary distribution/activation, mirror the full 396-artifact bundle (or at minimum the 73 Debian source packages) to an operator-controlled, redundant location and record that location in the release manifest, as `compliance/README.md` already anticipates.

### LOW — L2: No GPG signature verification of upstream `.orig.tar.*` against retained `.asc` files
**File(s):** `compliance/audit.py`, `compliance/bundle.py`, `compliance/README.md`
**Impact:** `.asc` signature files are retained and hash-pinned, but no signature verification is performed; integrity relies solely on SHA256. This is transparently disclosed ("Debian signature verification is not claimed") — not a hidden gap.
**Bounded repair:** Optional hardening only; not required for this checkpoint given the explicit, accurate disclosure already in place.

### OBSERVATION — O1: Scientific data is deliberately excluded from the Docker image
**File(s):** `Dockerfile`, `scripts/scientific_artifacts.py`, `app/main.py`
**Note:** TBB geometry/catalog, IANA tzdata/tzcode, and Swiss DE441 ephemeris files are fetched into an external `science_directory`, never `COPY`'d into the image. This is architecturally sound (keeps AGPL application-source concerns separate from ODbL/public-domain data-licensing concerns) and matches `/health/ready` correctly returning `not_ready` until that directory is explicitly configured. No action needed now; this externalization must be explicitly re-examined at the future activation/distribution gate, as `compliance/README.md` already anticipates ("No scientific image may be distributed without its extracted code and generated TZif controls public at that image's exact revision").

### OBSERVATION — O2: Consistently conservative, non-overclaiming language
**File(s):** `THIRD_PARTY_NOTICES.md`, `compliance/README.md`, `compliance/audit.py`, `compliance/release.py`, `compliance/build.py`
**Note:** Every place that could be overclaimed is explicitly scoped down: `"scientific_execution": false`, `"upstream_compiler_bit_reproducibility": "not claimed"`, `"status": "discovery_not_clearance"`, PyPI publication evidence explicitly disclaimed as non-Sigstore. This is good practice and should be preserved verbatim in future revisions rather than tightened into unqualified claims.

---

## What is and is not established by this evidence

**Implemented and reasonably well-evidenced (extraction/source-tooling, in scope for this review):**
- A 396-artifact, SHA256-pinned, credential-free-HTTPS source lock covering CPython, Debian (73 source packages), GEOS, Rust toolchain, pysweph/Swiss (+DE441 data), NumPy/OpenBLAS/gfortran/quadmath, Shapely build controls, IANA tzdata/tzcode, TBB geometry, and the full runtime Python dependency closure (wheel **and** sdist for each).
- Deterministic, twice-reproducible packaging (`compliance/bundle.py:pack`, `compliance/release.py:assemble`) verified in CI via `cmp` at the exact target revision.
- Native/OS correspondence auditing with genuine byte-level ELF-section proofs for the GCC/OpenBLAS chain and Rust build-identity proof for pydantic-core, plus exact source-file matching for the vendored Swiss C sources.
- Deduplicated, hash-verified verbatim third-party notice preservation (`compliance/native-notices.json`) spanning the full Rust vendor tree and Python wheel license files.
- Docker image build pinned by digest, built from `git archive HEAD` (not working tree), immutable revision baked in, `/source`/`/health/version` exposing exact commit and license link, uv excluded from the final image.

**NOT established by this evidence, and explicitly out of scope here — must not be read as authorized:**
- No public binary/image distribution or schema-tag release has occurred or is authorized by this material.
- No ACE cutover, client migration, or removal of the existing calculation service is authorized or evaluated.
- No claim of bit-reproducible upstream compiler output is made or should be inferred anywhere in this system (explicitly and repeatedly disclaimed in the source itself).
- No independent legal certification of license compliance is made by this review or by the reviewed tooling.
- Long-term source availability (mirroring beyond upstream/snapshot hosts) remains an unmet pre-distribution obligation, already correctly flagged as such by the maintainers.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

The Corresponding Source machinery for this extraction/parity checkpoint is substantially complete, honestly scoped, and unusually rigorous in several areas (Rust build-identity proof, GCC-chain ELF section proofs, exact Swiss source-file matching, deterministic twice-reproduced bundling verified in CI). The identified gaps (M1–M3) are about **evidentiary traceability and verification-depth consistency**, not about a fundamental absence of required source or build material, and none of them block the currently-authorized scope of extraction and isolated parity validation. They should be closed before this checkpoint is used to support any future activation/distribution/cutover decision.
