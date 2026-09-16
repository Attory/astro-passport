# Review Gate 1 — AGPL APT Bootstrap / Source-Publication & Architecture Boundary

**Repository:** https://github.com/Attory/astro-passport
**Reviewed SHA:** `0a31c4b157398b86799d586f10dfb5b937fa8f4d` (asserted root commit)
**CI referenced:** run `35086519869` on this SHA (success claimed, not independently re-executed)
**Review method:** static inspection of the 18 supplied files only. No tools, network, git, or execution were used.

---

## Findings

### CRITICAL
None identified in the supplied snapshot.

### HIGH
None identified in the supplied snapshot.

### MEDIUM

**M1 — "AGPL from first public commit" is unverifiable from the evidence given.**
- Path: repository history (not supplied).
- Evidence: Only a flat file snapshot at one SHA is provided; no `git log`, parent-commit list, or prior tags/refs were supplied. `docs/licensing.md` and `README.md` assert AGPL "from its first public commit," and the task frames `0a31c4b1…` as the "exact root commit" (implying no parent), which is internally consistent with the claim, but I cannot cryptographically or structurally confirm it.
- Impact: A load-bearing legal/compliance claim (no prior non-AGPL public history) cannot be independently confirmed at this gate.
- Recommendation: Supply `git log --all --oneline --parents` (or equivalent proof the SHA has zero parents) for independent confirmation before relying on this claim in downstream legal representations.
- Blocking: **Non-blocking** for this checkpoint (scaffold-only, not yet deployed), but must be closed before any network activation claim.

**M2 — CI success and pinned Action commit SHAs are asserted, not independently reproducible here.**
- Path: `.github/workflows/ci.yml`.
- Evidence: `actions/checkout@11d5960a…`, `actions/setup-python@a26af69b…` are pinned to 40-hex-char refs (good practice), and the run URL is cited as green, but I have no tool access to fetch run logs or confirm the refs resolve to genuine upstream Action releases.
- Impact: Supply-chain pinning is structurally sound, but its authenticity is unverified by this review.
- Recommendation: Attach CI run logs/artifacts (or checksums of the Action refs) to the review record for auditors without live GitHub access.
- Blocking: **Non-blocking.**

### LOW

**L1 — Dockerfile has no `HEALTHCHECK`.**
- Path: `Dockerfile`.
- Impact: Minor operational gap; irrelevant at scaffold stage since no deployment is authorized here.
- Recommendation: Add a `HEALTHCHECK` against `/health/live` before any real deployment gate.
- Blocking: No.

**L2 — CI never exercises the built container's HTTP surface, only `docker inspect` for UID/GID.**
- Path: `.github/workflows/ci.yml`.
- Impact: Non-root enforcement is verified; route/response behavior (no-store headers, 404 boundaries, fail-closed `/source`) is only verified via `pytest`/`TestClient`, not against the actual container network stack.
- Recommendation: Add a container-run smoke test (curl `/health/live`, `/health/ready`, `/source`) in a later gate.
- Blocking: No.

**L3 — `uv.lock` includes transitive mypy dependencies (`ast-serialize`, `librt`) unfamiliar from mainstream mypy's dependency graph.**
- Path: `uv.lock`.
- Impact: Could reflect legitimate newer mypy releases (dates in-file are 2026-dated, consistent with stated `currentDate`), but provenance is unverified by this reviewer without registry access.
- Recommendation: Confirm PyPI provenance/signature of these two distributions in a routine supply-chain pass; hash pinning already mitigates tamper risk if `uv lock --check` passed as claimed.
- Blocking: No.

**L4 — No per-file SPDX/AGPL header comments in `app/*.py` or `tests/*.py`.**
- Path: `app/__init__.py`, `app/main.py`, `app/build.py`, `tests/test_bootstrap.py`.
- Impact: AGPL only recommends (not mandates) per-file notices when a root `LICENSE` + SPDX `license` field in `pyproject.toml` exists, which this repo has; low practical risk.
- Recommendation: Add `# SPDX-License-Identifier: AGPL-3.0-only` per source file for maximal clarity in a future pass.
- Blocking: No.

### OBSERVATION

- **O1.** `app/build.py` correctly treats the AAC baseline (`aa4373b5d7b2539adf5bc87c0b4cc7d392d2135d`) as a static governance string embedded in output only — no filesystem/network read of a private AAC checkout, consistent across `AGENTS.md`, `README.md`, `docs/governance.md`, and code. No private-repo build dependency detected anywhere in the snapshot.
- **O2.** Build identity is fail-closed: `app/_revision` is written only inside the Docker build (`GIT_SHA` ARG validated by strict `[0-9a-f]{40}` regex before being persisted); a missing/invalid file yields `git_sha: null` and HTTP 503 on `/source` and `/health/version`, confirmed by `tests/test_bootstrap.py::test_immutable_source_identity`, including rejection of a path-traversal-style payload (`../../not-a-revision`).
- **O3.** Docker non-root is enforced at both declaration (`USER 10001:10001`) and CI-verified (`docker inspect --format '{{.Config.User}}'` check) — matches requirement.
- **O4.** Base images (`python:3.12.14-slim-bookworm`, `ghcr.io/astral-sh/uv:0.12.10`) are pinned by immutable `sha256` digest, not just tag, in both build stages — strong reproducibility posture.
- **O5.** Route surface is deliberately bounded and verified by test: only `/health/live`, `/health/ready` (always 503), `/source`, `/health/version` exist; `/docs`, `/openapi.json`, `/admin`, and a probed future route `/v1/passports` all 404 with `Cache-Control: no-store` — matches the "scaffold only, no extraction/API yet" scope claim.
- **O6.** Privacy posture is consistent: `--no-access-log`, no request/response-body logging code, no PII-capable fields anywhere in the scaffold, `no-store`/`no-referrer`/`nosniff` headers applied globally via middleware.
- **O7.** No Swiss Ephemeris/timezone/tzdb data or entitlement claims are present or implied (`THIRD_PARTY_NOTICES.md` explicitly disclaims this), and `README.md`/`docs/governance.md` explicitly disclaim deployment and scientific readiness — no premature scientific or deployment claim detected.
- **O8.** `/source` and `/health/version` are unauthenticated by design, matching the documented commitment that future API-key protection of computation "must not protect the source offer" (`docs/licensing.md`) — currently trivially true since no protected computation exists yet; flagged for re-verification at the next checkpoint when auth is introduced.
- **O9.** `.gitignore`/`.dockerignore` correctly exclude `app/_revision`, `.env*`, and `*.sqlite3*`, preventing accidental leakage of build-local or secret artifacts into the repository or image build context.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

The scaffold, as presented, stays within its declared scope: AGPL license text is complete and unmodified, third-party notices and runtime license inventory are present and preserved into the runtime image (`/usr/share/doc/astro-passport/`), build/source identity is immutable and fails closed rather than guessing, the AAC baseline is used strictly as a governance marker with no private-repo build/runtime dependency, Docker runs non-root with a CI-enforced check, the route surface is small and bounded with no extraction/auth/quota logic prematurely implemented, and documentation (README, governance.md, licensing.md, AGENTS.md) consistently avoids claiming scientific availability or deployment. No CRITICAL or HIGH issues were found in the supplied material.

Outstanding items (M1, M2, and the LOW/OBSERVATION items) are follow-ups, not blockers, for this scaffold-only gate — but M1 in particular must be closed with real commit-history evidence before any statement is made that a public network deployment inherits clean AGPL provenance from commit zero.

---

## Limitations

- This review is confined to the 18 files supplied in the snapshot; no git history, no live repository, no GitHub Actions logs, and no package registry were accessed.
- I did not execute `make check`, `uv lock --check`, `docker build`, or the test suite; their claimed pass results are taken as reported, not independently reproduced.
- I cannot confirm the authenticity of pinned third-party Action SHAs or PyPI wheel hashes beyond internal file consistency.
- I have no access to the private AAC repository and none was required or requested for this review, consistent with the stated architecture boundary.
- No deployment, scientific-accuracy, or legal-clearance determination is made or implied by this review; none was requested and none is offered.

## Essential material requests (for full closure of M1/M2, non-blocking for this gate)

1. `git log --all --oneline --parents` (or equivalent) proving `0a31c4b157398b86799d586f10dfb5b937fa8f4d` is a true root commit with no non-AGPL ancestor history.
2. CI run logs/artifacts for run `35086519869` (or a re-run transcript) for independent confirmation beyond the asserted "succeeded" status.
