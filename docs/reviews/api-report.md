# Independent Review — Gate 2: APT API/Auth/Privacy Contract Scaffold + Bootstrap Follow-up Closure

**Repository:** https://github.com/Attory/astro-passport
**Base (Gate 1):** `0a31c4b157398b86799d586f10dfb5b937fa8f4d`
**Exact HEAD reviewed:** `99056e6f10805df3aeef4b69a34c51b41f55482f`
**CI referenced:** run `35088583397`, conclusion `success` (operator-reported, not independently re-executed)
**Review method:** static inspection of the supplied public files only. No tools, network, git, or execution were used by this reviewer. All conclusions below are derived solely from the file contents/hashes as supplied.

---

## 0. Essential evidence limitations (apply to every finding below)

- This reviewer has no tool access: CI conclusions, "58 passing tests," Docker smoke results, and Ruff/mypy/lock/schema check outcomes are taken as **operator-reported**, not independently reproduced.
- File integrity (sha256 headers) is assumed accurate as supplied; no independent hash recomputation was performed.
- No git history beyond what Gate 1's `bootstrap-evidence.json` already established (root commit, zero parents) was re-verified; nothing in this snapshot contradicts it.
- No private AAC/ACE material was supplied or requested, consistent with the stated architecture boundary; this review cannot and does not assess private-repo governance, scientific correctness, or ACEP1 conformance.
- PyPI/registry authenticity beyond the previously reviewed `bootstrap-evidence.json` metadata was not re-checked.

None of these limits block a scaffold-level verdict; they bound its authority.

---

## 1. Gate 1 disposition verification (ledger.md claims checked against this snapshot)

| Item | Disposition claimed | Verified in this snapshot? |
|---|---|---|
| M1 (root-commit provenance) | Evidence retained in `bootstrap-evidence.json` | ✅ Present, unchanged, still references root SHA with `"parents": []` |
| M2 (CI reproducibility) | Job/step-level evidence retained | ✅ Present in `bootstrap-evidence.json` |
| L1/L2 (no HEALTHCHECK / no container HTTP smoke) | Docker `HEALTHCHECK` + CI network-none smoke test added | ✅ `Dockerfile` has `HEALTHCHECK`; `.github/workflows/ci.yml` runs `scripts/container_smoke.py` inside `--network none --read-only --cap-drop ALL --security-opt no-new-privileges` container |
| L3 (unfamiliar mypy transitive deps) | PyPI registry metadata confirms `ast-serialize`/`librt` | ✅ Present in `bootstrap-evidence.json`; consistent with `uv.lock` entries and versions |
| L4 (no SPDX headers) | Headers added to source/tests/scripts | ✅ Confirmed present in every `app/*.py`, `tests/*.py`, `scripts/*.py` file supplied |

All five Gate 1 follow-ups are closed with concrete, checkable artifacts rather than assertions. No new bootstrap-layer regression found.

---

## 2. Findings

### CRITICAL
None identified.

### HIGH
None identified.

### MEDIUM
None identified as a genuine scaffold-level security defect. (See LOW/OBSERVATION for design nits that are candidates for hardening before activation, not blocking here.)

### LOW

**L1 — Admission-control check-then-acquire race in `install_api` (`app/api.py`).**
- Evidence: `if slots.locked(): return error(503, "busy")` is evaluated, then `async with slots:` performs the actual `acquire()`. Between these two statements another coroutine can take the last permit, so this request's `acquire()` can block rather than fail fast with 503 as the "busy" design intends.
- Impact: under concurrent load this can produce a brief queuing/convoy effect instead of the documented immediate-reject admission control. Not exploitable for authentication bypass, data leakage, or resource exhaustion beyond the existing 4-slot bound; bounded by per-request timeouts (2s body / 6s engine) once inside.
- Blocking for this checkpoint: **No.** Science is unimplemented (`UnavailableScience` raises immediately), so the race window is negligible in practice today.
- Recommend before activation: use an atomic non-blocking acquire pattern (e.g. `acquire_nowait`-equivalent, or a bounded `asyncio.wait_for` with immediate timeout) so "busy" is guaranteed race-free once a real engine adds latency.

**L2 — `ErrorCode` includes `"forbidden"` with no emitting code path.**
- Evidence: `app/contracts.py` `ErrorCode` Literal and `contracts/astropassport/v1/schema.json` enum both list `"forbidden"`; `app/api.py` never returns HTTP 403 / this code.
- Impact: none today (unused enum value, no dead-code security exposure). It is a reserved slot for a future authorization-scope error.
- Blocking: No. Purely a documentation/forward-compat note.

**L3 — Header-budget check occurs after ASGI-layer header parsing.**
- Evidence: `MAX_HEADERS` (16 KiB) is enforced in `app/api.py` against `request.scope["headers"]`, i.e., after uvicorn/h11 has already parsed the full header block into memory.
- Impact: this is explicitly and correctly documented as an application-layer budget, not a network-parser bound (`docs/security.md`: "application limits do not bound the network parser... reverse proxy must impose... before activation"). Not a new defect — confirms the doc's own caveat is accurate.
- Blocking: No.

### OBSERVATION

- **O1 — Runtime license inventory is closed and exact.** Cross-checking `pyproject.toml` runtime dependencies (`fastapi`, `pydantic`, `uvicorn`) against `uv.lock`'s transitive closure yields exactly the 13 packages listed in `docs/runtime-licenses.json` (fastapi, pydantic, uvicorn, annotated-doc, starlette, typing-extensions, typing-inspection, anyio, idna, annotated-types, pydantic-core, click, h11) — no missing and no extraneous entries. Dev-only packages (mypy, ruff, pytest, httpx and their transitives) are correctly excluded from the runtime image via `uv sync --frozen --no-dev --no-install-project` in the Dockerfile builder stage.
- **O2 — Documented operational limits match code exactly.** `docs/security.md`'s stated limits (≤16 credentials, 1–60/minute, 16 KiB body/headers, 2s body deadline, 6s engine deadline, 4 concurrent admissions, ≤1 MiB/128-row quota file) are all traceable 1:1 to literal constants/validators in `app/api.py` and `app/security.py`. No doc/code drift found.
- **O3 — Fail-closed posture is consistent and tested.** `/health/ready` is unconditionally 503; `Settings.enabled` defaults `False`; `authenticate`/`reserve_quota` raise `SecurityStateError` (→503) on any missing/oversized/wrong-permission/wrong-owner/symlinked key or quota file rather than degrading silently. `tests/test_api.py::test_credentials_fail_closed` exercises missing/permissions/corrupt/symlink/expired/revoked cases; `test_quota_survives_restart_and_unavailable_state` exercises deleted quota state. This is real negative-path test coverage, not just documentation.
- **O4 — No private-service coupling detected.** The AAC baseline hash is used only as a static string constant in `app/build.py` output; no network/filesystem read of a private path, no ACE/AIS hostnames, credentials, or shared imports appear anywhere in the supplied files.
- **O5 — No premature scientific or schema-release claim detected.** `contracts/manifest.json` has `"status": "candidate_not_released"` and `"release_git_sha": null`; `contracts/README.md` and `docs/governance.md` explicitly disclaim ACEP1/full-identity parity; `pyproject.toml` has no ephemeris/timezone dependency; `scripts/schema.py --check` (run under `make check`) enforces the generated schema bytes match the committed candidate file and manifest digest, preventing silent schema drift.
- **O6 — Privacy-by-construction is deeper than a policy statement.** `Wire.__repr_args__` returns `[]` to suppress field values from `repr()`; `hide_input_in_errors=True` on all wire models prevents Pydantic from echoing rejected input in validation errors; `unique_json` rejects duplicate JSON keys and JSON constants (`NaN`/`Infinity`) before Pydantic even parses; `tests/test_api.py::test_valid_request_unavailable_and_private` asserts specific synthetic secrets/PII-shaped values never appear in logs or response bodies. This is enforced behavior, not just a comment.
- **O7 — Forbidden private/identity fields are actively tested, not just documented.** `test_private_or_computed_inputs_forbidden` parametrizes `sex`, `gender`, `account_id`, `astro_id`, `score`, `timezone`, `flags` and asserts `extra="forbid"` rejects all of them — directly enforcing the AGENTS.md/governance constraint against copying participant/sex/identity logic into the public wire format.
- **O8 — TLS-scheme fail-closed behavior matches its own documented future gate.** `app/api.py` rejects any request where `request.url.scheme != "https"`; combined with `--no-proxy-headers` in the Dockerfile `CMD`, a plain-HTTP-terminating reverse proxy would currently cause all computational requests to 400. `docs/deployment-plan.md` explicitly flags this as a required pre-activation design decision ("a reviewed exact-peer or private Unix-socket... is required"). This is a known, self-disclosed future-activation gate, not a hidden scaffold defect.
- **O9 — Version/base-image pinning is fully consistent.** `uv==0.12.10` is pinned identically in `.github/workflows/ci.yml`, `Dockerfile` (by digest), and `pyproject.toml` (`required-version`); Python `3.12.14` is pinned identically in CI and both Dockerfile stages. No drift.

---

## 3. Explicit non-findings (things this review does NOT claim)

- This review does **not** assert astronomical/scientific correctness of anything — there is no scientific code in this snapshot to assess (`UnavailableScience` is the only "science" present, and it always fails).
- This review does **not** approve the candidate schema (`contracts/astropassport/v1/schema.json`) as a canonical release — its own manifest correctly marks it `candidate_not_released`.
- This review does **not** approve any deployment — none is described as performed, and `docs/deployment-plan.md` is explicit that no host operations have occurred.
- This review does **not** independently verify the operator's claimed "58 passing tests" or exact CI run logs beyond the JSON summary supplied; it verifies that the test files present are structurally capable of producing substantial coverage of the security/privacy paths described.
- The LOW findings above (admission-control race, unused error code, header-budget scope) are **code-quality/robustness observations relevant to future activation**, not exploitable defects in the current disabled-by-default, no-science scaffold. They are surfaced rather than waived, per instructions not to excuse real defects just because the feature is inactive — but none of them rises above LOW because none is exploitable given the current fail-closed default state and absence of a real engine.

---

## 4. Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

Rationale: No CRITICAL or HIGH findings. The scaffold stays within its declared scope (default-disabled API, no scientific engine, `/health/ready` always 503, no canonical schema release, no private-service coupling, no deployment). Security/auth/quota/privacy controls are implemented with real fail-closed behavior and are exercised by targeted negative tests, not merely asserted in prose. AGPL/public-source boundary is intact (unmodified LICENSE, complete and cross-checked THIRD_PARTY_NOTICES/runtime-license inventory, immutable fail-closed build identity, `/source` and `/health/version` unauthenticated as required). All five Gate 1 follow-up items are demonstrably closed in this snapshot with concrete artifacts. The three LOW items (semaphore race, unused `forbidden` code, header-budget scope note) and the documented-but-worth-reiterating TLS-scheme/proxy-trust gate are legitimate forward-looking hardening items for the **future activation gate**, not defects that block acceptance of this contract-scaffold checkpoint.

This verdict covers scaffold/API-contract/security-privacy/licensing-boundary acceptance only. It does not constitute, and should not be cited as, approval of scientific parity, canonical schema/tag release, ACEP1/full-identity claims, or any public deployment — each of which remains an explicit, separate, not-yet-reached gate per `docs/governance.md`, `docs/extraction-plan.md`, and `docs/deployment-plan.md`.
