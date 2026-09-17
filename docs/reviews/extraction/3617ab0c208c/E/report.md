# Independent Review — Lens E (API TLS/Auth/Expiry/Revocation/Quota/Concurrency/Size/Privacy/Readiness/Logs/No-Store/Zero-Work/Isolation)

**Target:** `3617ab0c208cbd56927e0b84574b778e832ca8a1` (base `dae015fd069308e408280d980e10ff72ed722488`, AAC `59500ec0951e082dd4c3984999b8a42fe4ce53c8`)
**Scope respected:** normative contract `75092aac79c39c6893900a0758ab176a47fe0c7a`, the 16 attested ACE origins, and the extraction/isolated-parity authorization are treated as resolved and are not reopened here. This review covers only what is implemented in this commit, not any deployment or ACE cutover.

---

## Findings

### HIGH — none identified for this lens
No defect found in the reviewed code that would independently block the extraction/parity checkpoint on TLS, auth, expiry, revocation, quota, concurrency, size, privacy, readiness, logging, no-store, zero-work, or isolation grounds.

### MEDIUM

**M1. Scheme-trust boundary for HTTPS is a known, still-open pre-activation gate.**
`app/api.py:install_api` — the only HTTPS enforcement is `request.url.scheme != "https"`, evaluated from the raw ASGI scope with `--no-proxy-headers` set (Dockerfile `CMD`). This is correct and fail-closed for the current topology (uvicorn terminating TLS directly, as used in `scripts/https_scientific_smoke.py`), but it is *not yet* a working mechanism for the documented production topology (Caddy TLS → private APT), which requires an exact-peer or Unix-socket scheme to safely mark scope as HTTPS (`docs/security.md`, `docs/deployment-plan.md`). This is already explicitly tracked as a pre-activation gate in those docs, not a new omission. **Impact:** none for extraction/parity; would fail closed (reject all real proxied traffic) rather than silently trust forwarded headers, which is the safe failure mode. **Repair (bounded, pre-deployment only):** implement and independently review the exact-peer/Unix-socket trusted-transport mechanism before any deployment approval; do not add generic `X-Forwarded-Proto` trust.

**M2. Header-size admission check is a coarse proxy, not a true framing-level bound.**
`app/api.py` sums `len(k) + len(v)` over ASGI header byte tuples for `MAX_HEADERS` (16 KiB), which omits header-name/value separators, request-line, and other framing overhead. This is explicitly caveated in `docs/security.md` ("application limits do not bound the network parser") as a pre-activation gate requiring reverse-proxy enforcement. **Impact:** none for this checkpoint (no proxy/deployment authorized yet). **Repair:** before deployment, confirm ingress enforces a real header/line/body budget independent of this application-level approximation.

### LOW

**L1. Admission slot consumption occurs before authentication completes.**
`app/api.py`: the 4-slot `asyncio.Queue` admission token is acquired *before* `authenticate()` and `reserve_quota()` run (only the zero-cost `enabled`/scheme/query/header-count/duplicate-header checks precede slot acquisition). An unauthenticated or otherwise-invalid-credential caller still occupies one of the 4 concurrent admission slots for the (bounded, fast) duration of the file-based auth check. `test_early_denials_zero_science` correctly verifies **no science work** occurs on these paths, satisfying the documented "zero-work" contract, but concurrency-slot pressure from invalid-credential floods is possible up to the hard cap of 4 — consistent with, but not explicitly called out by, `docs/security.md`'s note that "Authentication, version/media/size, quota and validation precede scientific work." **Impact:** low — bounded by the existing hard cap, not unbounded, and matches the documented isolation-before-science design; only a nuisance rate-limiting nuance for later reverse-proxy sizing. **Repair (non-blocking):** document explicitly in `docs/security.md` that admission slots are consumed during auth/quota checks, or (optional hardening) move slot acquisition after auth+quota if independent testing later shows it matters.

**L2. `content-length` mismatch is only detected after full-body streaming.**
`app/api.py` streams the full body (bounded by `MAX_BODY`) before comparing `len(body)` to the declared `Content-Length`. Bounded by `MAX_BODY` (16 KiB) regardless, so this is not a resource-exhaustion issue, just a minor ordering inefficiency. **Impact:** negligible. **Repair:** none required; optional early rejection if length is internally inconsistent before allocation.

### OBSERVATION

- **O1.** `reserve_quota`'s `COUNT(*) >= 128` defensive cap is effectively unreachable given the ≤16-credential limit enforced in `authenticate()`; harmless defense-in-depth, not a defect.
- **O2.** Constant-effort comparison in `authenticate()` (`hmac.compare_digest` evaluated for every record, no early exit) and content-length ASCII/decimal validation before `int()` parsing are good defensive patterns; noted for completeness, not required changes.
- **O3.** Evidence in `docs/extraction/https-parity-*.json`, `image-source-94c8103.json`, and `docs/extraction/ledger.md` (zero mismatches across classifications, exact image/source correspondence, TLS negative tests, log-content checks for query/date/Authorization) is **recorded evidence of a prior local execution**, not something I independently executed or can independently verify from static review. The exact-head CI result supplied (`35157967778`, `conclusion: success`) is likewise an attested record, not independently re-run by me.
- **O4.** No epsilon/tolerance logic, `np.isclose`, or approximate-equality construct was found anywhere in the reviewed longitude/contract code; `Longitude.representation()` enforces exact binary64 hex round-trip and exact half-even Decimal quantization — consistent with the zero-tolerance requirement stated for this review.
- **O5.** `-proposed` encoding identifiers (`apt.sun-moon-content.v1-proposed`, `APTCanonicalSunMoonContent.v1-proposed`) are unchanged in `contracts/accepted/acep1-profile.md` and referenced consistently elsewhere — no unauthorized renaming observed.

---

## Implemented extraction/parity vs. forbidden future items (explicit separation)

**Implemented and reviewed in this commit (in scope):**
- Fail-closed API scaffold with TLS-scheme check, bounded auth (expiry/revocation/HMAC-constant-time), durable atomic quota with clock-rollback protection, 4-way HTTP admission concurrency cap plus a separate 2-way native-worker capacity, strict body/header size bounds with streaming timeout, no-store/no-cache/nosniff/no-referrer headers on every response, disabled docs/openapi/admin routes, readiness gated on real science construction with a pinned self-check, immutable build-time (not env-overridable) source identity, non-root/read-only/no-new-privileges container isolation validated in CI, and zero-work guarantees for unauthorized/malformed/oversized/disabled requests (test-enforced).
- 16-origin scientific extraction accounting (`docs/extraction/origins.json`) with narrowed/renamed destinations and explicit non-copy of ACE wrapper/selection code.
- Contract 1.0.0 revision 2 bytes and ACEP1-proposed profile preserved unchanged.

**Explicitly NOT implemented, NOT claimed, and out of scope for this review's verdict:**
- No deployment, no VPS connection, no activation, no ACE cutover — confirmed absent from workflows, Dockerfile CMD, and docs (`deployment-plan.md` states host operations are not performed).
- No canonical schema tag/publication, no external distribution of the schema.
- No independent, tool-verified confirmation by me of the recorded HTTPS parity runs, TLS negative tests, or CI success — these remain attested records reviewed as evidence, not reproduced.
- No claim of scientific/astronomical accuracy beyond migration equivalence, per `docs/extraction/checkpoint.md`.

---

## Evidence limitations

- All CI, HTTPS-parity, image/source-correspondence, and container-isolation results are taken as **recorded/attested evidence** supplied with the task; I did not execute code, containers, or network operations, and cannot independently confirm these results beyond static code/document consistency review.
- Static review cannot fully validate runtime behavior (e.g., actual ASGI scope scheme propagation under the real proxy topology, actual timing-channel resistance, actual concurrency behavior under load) — these are inferred from code structure and the referenced test suite, not independently executed.
- This is a code/document consistency review, not a security certification or legal compliance determination.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

Rationale: no CRITICAL or blocking HIGH defect was found in the implemented API TLS/auth/expiry/revocation/quota/concurrency/size/privacy/readiness/logging/no-store/zero-work/isolation surface for this exact-head commit. The MEDIUM/LOW items above (M1 scheme-trust for the real proxy topology, M2 header-size approximation, L1 admission-slot timing before auth, L2 length-check ordering) are already substantially tracked in `docs/security.md`/`docs/deployment-plan.md` as pre-activation gates or are low-impact/bounded, and none require rework of the extraction/parity implementation itself. They should remain open follow-ups and explicit hard gates before any future deployment or activation decision, which remains unauthorized and unperformed here.
