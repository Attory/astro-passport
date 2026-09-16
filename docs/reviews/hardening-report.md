# Independent Review — Gate 2 Hardening (Delta Review)

**Repository:** https://github.com/Attory/astro-passport
**Prior fully-reviewed base:** `99056e6f10805df3aeef4b69a34c51b41f55482f`
**New exact HEAD reviewed:** `82d14724028384ce5ee104953197e05bd70c5581`
**CI evidence supplied:** run `35089402312` → `success` at exact HEAD; prior run `35089255656` at `4763bb0efcd8e79f14b54acbf0454f5bc36841d8` → failure, disposition retained in `docs/reviews/ledger.md` (not waived)
**Method:** static reading of the exact diff and full current file contents supplied above. No tools, network, git, or execution available to this reviewer. CI conclusions and "59 tests" are operator-reported, not independently re-executed. This is a **fresh** review of the delta — the prior Gate 2 self-report (`api-report.md`) is treated as one input, not as pre-approval carried forward.

---

## 1. Verification of the four closure items

**(a) L1 — admission control race (`app/api.py`).**
Replaced `asyncio.Semaphore` + `if slots.locked(): ... async with slots:` with a pre-filled `asyncio.Queue(maxsize=4)` and `slots.get_nowait()`/`except asyncio.QueueEmpty`. Verified:
- `get_nowait()` is synchronous and non-blocking; there is no `await` between the admission check and the protected region, so the "busy" decision and permit acquisition are now a single atomic statement, eliminating dependence on event-loop fast-path reasoning.
- Every successful `get_nowait()` is followed by a `try/finally: slots.put_nowait(None)` that unconditionally restores the token, including on `SecurityStateError`, `ScienceUnavailable`, `TimeoutError`, generic `Exception`, and (since `put_nowait` is a synchronous call reached during unwind) task cancellation.
- Token accounting is exactly balanced: the queue starts with exactly 4 items, and every `get` has exactly one paired `put` on all code paths. No double-release or leak path found.
- Genuinely fixes the previously identified issue rather than merely reframing it. **Confirmed closed.**

**(b) L2 — reserved `forbidden` error code.** `contracts/README.md` now states it is reserved, not emitted, and that `passport:calculate` is the only configured scope. No code or schema enum change, no new emission path introduced. Doc-only, consistent with the actual code (`app/api.py` never returns 403). **Confirmed closed as documentation.**

**(c) L3 — ingress-parser activation gate.** No code touched; `docs/security.md` unchanged in this respect (already stated the app-layer header budget is not a transport-parser bound). Prior finding was already a documentation-consistency observation, not a defect; nothing regressed. **Confirmed preserved.**

**(d) Private-key-hash file ownership clarification.** `docs/security.md` now states the container's numeric owner must be the service UID (10001) and that a root-owned 0600 host bind is not readable merely by being mounted. Cross-checked against `app/security.py::private_file`: `os.open(..., O_NOFOLLOW|O_NONBLOCK)` will itself fail with `EACCES` for a root-owned 0600 file when the process runs as non-root UID 10001 (per `Dockerfile USER 10001:10001`), *before* the subsequent application-level `st_uid not in (0, os.getuid())` check is even reached. The doc's operational guidance is accurate for the actual non-root container deployment path; the app-level check's acceptance of UID 0 is unchanged pre-existing code (relevant only if the process itself ran as root, e.g., non-container dev use), not a new gap. **Confirmed accurate, no regression.**

---

## 2. New regression test (`test_admission_saturation_is_immediate_and_releases_tokens`)

- Establishes 4 held engine calls **sequentially**, confirming each one actually reached the engine (`entered.get()` with a bounded 2s wait and an explicit failure message distinguishing "early error code returned" from "timeout") before starting the next — directly correcting the flaw that caused the prior CI failure (`35089255656`), where the old fixture fired 4 requests concurrently and blocked on an undifferentiated wait.
- Confirms the 5th request is rejected with `503/busy` within 1s (bounding the fail-fast requirement) and that `science.calls == 4` at that point (engine never invoked for the rejected request).
- Releases the held calls, drains all 4 (`science_unavailable`), then issues a 6th request and asserts `science.calls == 5` with a normal `science_unavailable` response — proving token restoration, not just rejection.
- This is a real, non-trivial concurrency test that exercises the exact mechanism changed, not a superficial assertion. **Sound and sufficient evidence for L1 closure.**

## 3. Disposition of the prior failed run

The ledger's account (SQLite `BEGIN IMMEDIATE` contention plausibly delaying some of 4 concurrently-fired requests reaching the engine, with the old fixture's single undifferentiated wait hiding *which* request stalled and why) is a credible, falsifiable explanation, and the fix (sequential admission confirmation with per-step timeout and diagnostic failure message) is the correct engineering response — not a retry-until-green waiver. This satisfies "detailed disposition retained, not waived."

---

## 4. Findings

### CRITICAL — none
### HIGH — none
### MEDIUM — none

### LOW

**L1 (new, minor) — theoretical double-release path if `put_nowait` in `finally` ever raises.**
If the queue's exact-balance invariant were ever violated by a future edit (e.g., an extra manual `get`/`put` added elsewhere), `slots.put_nowait(None)` in the outer `finally` would raise `QueueFull`, and that exception is **outside** the inner `except Exception` handler, so it would propagate unhandled to Starlette's default error path instead of the app's controlled `error(500, "internal_error")` response — a theoretical departure from the "never leak tracebacks" posture. Not exploitable today (invariant currently holds exactly), but there is no defensive `try/except` around the release. Non-blocking; consider guarding or asserting in a follow-up.

**L2 (carried, now doc-only, effectively closed) —** `forbidden` remains an emitted-nowhere enum value in `contracts/astropassport/v1/schema.json` and `app/contracts.py`. Now correctly documented as reserved. No action required at this checkpoint.

### OBSERVATION

- **O1** — Admission-slot check still precedes authentication (`slots.get_nowait()` before `authenticate()`), meaning an unauthenticated caller can distinguish "busy" from other rejections without valid credentials. This is unchanged from the prior-reviewed base (not introduced by this diff) and is a pre-existing, already-accepted design property, not a new finding.
- **O2** — The fix removes reliance on "asyncio has no preemption between non-await statements" reasoning (which the ledger itself notes was never demonstrated as an actual race) and replaces it with a primitive whose atomicity does not depend on scheduler internals. This is a genuine robustness improvement independent of whether the original issue was exploitable.
- **O3** — No change touches `app/security.py`, `app/contracts.py`, `contracts/astropassport/v1/schema.json`, `contracts/manifest.json` (still `"status": "candidate_not_released"`, `"release_git_sha": null`), dependency pins, or the Dockerfile beyond what's shown — consistent with "unchanged dependencies/schema bytes covered by the prior full report" and with no scientific/schema release occurring here.
- **O4** — `/health/ready` still unconditionally 503 in the unchanged `app/main.py`; no science/engine code introduced; no new network egress, credentials, or private-service coupling appears anywhere in the diff.
- **O5** — Ledger's disposition of the CI Node-20-deprecation annotation and the source-archive HTTP-200 availability probe are both explicitly and correctly scoped as non-authoritative/non-blocking informational notes, not proof of a deployed runtime.

---

## 5. Explicit non-findings (scope boundaries honored)

- No scientific implementation, comparator, or ephemeris code is present or claimed; `UnavailableScience`/`science_unavailable` remains the only behavior.
- No canonical schema release, tag, or ACEP1/full-identity parity claim is made or implied; manifest status is unchanged (`candidate_not_released`).
- No deployment occurred or is claimed; `docs/deployment-plan.md` is unchanged and remains explicitly non-authorizing.
- This review does not independently re-execute CI, recompute file hashes, or verify the "59 local+CI tests" / smoke-test claims beyond structural plausibility of the supplied test code.

---

## 6. Blockers for THIS scaffold checkpoint

**None.** All four items in scope (L1 code race, L2 doc, L3 doc, key-file ownership doc) are closed with either a correct atomic-primitive fix plus a real regression test (L1) or accurate documentation with no code/behavior change (L2/L3/ownership). No security, privacy, licensing, or source-boundary regression was found versus the prior fully-reviewed base. Production limits are unchanged.

## 7. Separate pre-activation gates (not evaluated/authorized here, unchanged from prior gates)

- TLS/forwarded-header trust topology and reverse-proxy connection/header/rate budgets (`docs/deployment-plan.md`, `docs/security.md`).
- Real scientific engine isolation, native-worker resource/kill limits, and equivalence-harness execution (`docs/equivalence-design.md`).
- Canonical schema tag/release and AAC approval of exact bytes/rights (`contracts/README.md`, `contracts/manifest.json`).
- Durable credential/quota provisioning and rotation procedure; any actual deployment sequence (`docs/deployment-plan.md`).
- The LOW L1(new) finally-block hardening item above is a reasonable candidate for the next hardening pass but does not block this checkpoint.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

The Gate 2 hardening delta genuinely closes the prior L1 finding with an atomic, testable fix rather than argumentation, correctly documents L2/L3/key-ownership without unauthorized behavior change, and the CI failure at the intermediate commit is transparently and credibly disposed of rather than waived. No CRITICAL/HIGH/MEDIUM issues found in this delta. This verdict covers only the API/security/privacy scaffold and its hardening at exact HEAD `82d14724028384ce5ee104953197e05bd70c5581`; it is not scientific, schema-release, or deployment approval, all of which remain separate, not-yet-reached gates per the repository's own governance documents.
