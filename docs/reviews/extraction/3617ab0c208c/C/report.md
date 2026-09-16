# Independent Review — Lens C: Swiss Runtime / Native-Process Isolation / Flags / Fallback Refusal / Data & Binary Pins / Numerical & Time Policies / Cancellation & Worker Limits

**Scope reviewed:** `app/science/ephemeris/*`, `app/science/natal/*`, `app/science/pipeline.py`, `tests/test_science.py`, `tests/test_scientific_failures.py`, supporting CI/Docker/manifest material.
**Target:** `3617ab0c208cbd56927e0b84574b778e832ca8a1` (base `dae015fd0693…`, AAC baseline `59500ec0951…`, normative checkpoint `75092aac79c3…`).
**Evidence basis:** committed files as supplied and the single reported CI result (`run 35157967778`, conclusion `success`, exact head SHA match). I did not execute anything myself; I treat the CI record and doc claims (parity JSONs, ledger, checkpoint) as *reported* evidence, not independently reproduced.

This review only evaluates the **implemented extraction and isolated-parity plumbing** actually present in these files. It makes no finding about, and does not endorse, any deployment, external activation, ACE cutover, or schema/binary distribution — all of which the repo itself repeatedly and correctly marks as separate, ungranted gates.

---

## Findings

### HIGH — none identified in this lens
No High-severity defects were found in the reviewed Swiss/native-isolation material. The design shows deliberate, layered fail-closed behavior (binary/data pinning, flag verification, file-identity/generation checks, resource limits, bounded I/O, non-blocking capacity).

### MEDIUM-1 — Pinned native binary hash is duplicated with no automated cross-consistency check
**Files:** `app/science/ephemeris/identity.py` (`BINARY_SHA256`) vs `app/science/ephemeris/worker.py` (`BINARY_SHA256`, re-declared because the worker runs with `-I` and cannot import application code).
**Impact:** The two constants currently match, but they are independent literals with no test asserting they stay in sync. If a future update to one file is not mirrored in the other, the failure mode is *usually* fail-closed (mismatch → `unsupported_runtime`), but a maintenance slip that updates both to a *wrong-but-matching* value would not be caught by either side alone — the redundancy only protects against a single-file typo, not a coordinated pin update error.
**Bounded repair:** Add a unit test (e.g., in `tests/test_scientific_failures.py`) asserting `app.science.ephemeris.identity.BINARY_SHA256 == app.science.ephemeris.worker.BINARY_SHA256` (source-level string compare, not execution), so drift is caught at `make check` rather than at runtime.

### MEDIUM-2 — Module-level (not instance-level) capacity semaphore in the ephemeris adapter
**File:** `app/science/ephemeris/adapter.py`, `_CAPACITY = threading.BoundedSemaphore(2)` declared at module scope, shared by every `SwissEphemeris` instance in the process, whereas `PassportScience` (`app/science/pipeline.py`) correctly scopes its own `_capacity` per instance (`self._capacity = threading.BoundedSemaphore(2)`).
**Impact:** Today this is masked because exactly one `PassportScience`/`SwissEphemeris` pair exists per process and the two caps of 2 line up. But it is an implicit, easy-to-violate invariant: any second `SwissEphemeris` instantiation in the same process (additional test fixtures, a future multi-tenant or hot-reload pattern) silently shares native-process quota with an unrelated instance, producing spurious `busy` responses or, in the opposite direction, masking an intended per-instance limit if instances are supposed to be independent.
**Bounded repair:** Move `_CAPACITY` into `SwissEphemeris.__init__` as an instance attribute, matching the pattern already used correctly in `PassportScience`.

### MEDIUM-3 — Declared OS resource limits are not exercised by any test
**File:** `app/science/ephemeris/worker.py::main()` sets `RLIMIT_CORE`, `RLIMIT_CPU=2s`, `RLIMIT_AS=256MB`, `RLIMIT_FSIZE=8192`, `RLIMIT_NOFILE=32`.
**Impact:** `tests/test_scientific_failures.py` and `tests/test_science.py` verify the *parent-side* timeout path only via a monkeypatched `subprocess.TimeoutExpired` — they never spawn the real worker to confirm that, e.g., the 2‑second CPU limit or 256MB address-space limit actually trips before the 5‑second wall-clock timeout, or that `RLIMIT_FSIZE=8192` genuinely caps stdout as the parent's 8193-byte read assumes. This is a coverage gap on the defense-in-depth layer, not a demonstrated defect.
**Bounded repair:** Add a narrow, CI-safe integration test that runs the real worker subprocess (not mocked) with a deliberately pathological input/environment and asserts non-zero exit / expected truncation, to confirm the RLIMITs are load-bearing rather than dead configuration.

### LOW-1 — Native worker isolation relies on env/rlimits, not OS sandboxing for network egress
**File:** `app/science/ephemeris/adapter.py` (`subprocess.run(..., env={"PATH": os.defpath, "LC_ALL": "C", "TZ": "UTC"}, cwd=directory, timeout=5)`).
**Impact:** The isolated worker gets a scrubbed environment and strict resource limits, but nothing in the per-request subprocess invocation itself (as opposed to the container-level `--network none` used in the CI smoke test) prevents outbound network calls if the pinned native extension were ever compromised. Given the binary is hash-pinned and verified before import, residual risk is low, but this is a real difference between "CI/production container" isolation and "worker subprocess" isolation, and the README's plain `uv run uvicorn …` local-dev path has no such container network restriction at all.
**Bounded repair:** Document this explicitly as a defense-in-depth layering assumption (container network policy is the actual network control, not the subprocess), or consider `unshare --net` / seccomp for the worker subprocess itself as a future hardening item — non-blocking for the extraction/parity scope under review.

### LOW-2 — Concurrency cap is per-process, not per-host, and could be silently multiplied
**Files:** `Dockerfile` (`CMD [... "--workers", "1"]`), `app/science/pipeline.py`, `app/science/ephemeris/adapter.py`.
**Impact:** The `2`-slot bounded semaphores only bound concurrency *within one uvicorn worker process*. `--workers 1` is currently pinned, so the effective cap is well-defined, but this coupling between deployment configuration (`--workers`, replica count) and the hard-coded `2` is not enforced anywhere in code — a future operational change to `--workers` N or horizontal scaling would silently multiply real concurrent native-process load without any code change or test failure.
**Bounded repair:** Add a comment/assertion at startup (e.g., in `app/main.py` or a documented operational constraint in `docs/deployment-plan.md`) that ties the semaphore sizing assumption to single-worker deployment, so this is caught before any future cutover/deployment gate is opened.

### OBSERVATION-1 — Zero-tolerance numeric policy is consistently and correctly enforced (positive finding)
**Files:** `app/science/ephemeris/contracts.py` (`longitude_decimal`, `BodyLongitude.exact_projection`, `EphemerisResult.coherent`).
No epsilon, approximate-equality, or tolerance-based comparison of any kind appears anywhere in the reviewed lens-C code. Binary64→decimal conversion uses `Decimal(str(raw))` (shortest round-trippable representation) with explicit `ROUND_HALF_EVEN` quantization to 9 places, and `BodyLongitude` independently round-trips `binary64_hex` back through `float.fromhex` to assert byte-for-byte consistency with the decimal field. This matches the "scientific exact binary64 and canonical bytes have zero tolerance" requirement as implemented in this commit.

### OBSERVATION-2 — Anti-fallback and flag-integrity checks are implemented and test-covered
**Files:** `app/science/ephemeris/worker.py` (`flags != 2` → `fallback_rejected`; `get_current_file_data` path/generation/date-range check → `fallback_rejected`), `app/science/ephemeris/contracts.py` (`returned_flags: tuple[Literal[2], Literal[2]]`), `tests/test_scientific_failures.py::test_native_fallback_and_warning_never_become_success` (parametrized over `flags`, `warning`, `nonfinite`, `generation`, `file`, `delta_warning`).
This directly targets the "fallback refusal" requirement of this lens and is exercised by unit tests using a stub Swiss library — this is a synthetic fault-injection test, not a live-binary integration test, but it does verify the *code paths* that must reject silent precision downgrade or wrong-data-file use.

### OBSERVATION-3 — Cancellation semantics are deliberately shield-protected and tested
**File:** `app/science/pipeline.py::PassportScience.calculate` (`asyncio.shield(future)`, pre-await capacity acquisition, `finally: self._capacity.release()` inside the worker thread body, done-callback that swallows late exceptions without logging).
**Test:** `tests/test_scientific_failures.py::test_cancelled_waiters_do_not_release_running_science_slots`.
The implementation and its test correctly demonstrate that an HTTP-side cancellation does not free a capacity slot early or leak an unbounded queue of native processes — this matches the "cancellation and worker limits" requirement of this lens.

### OBSERVATION-4 — Contract/`-proposed` suffixes and normative checkpoint bytes are unchanged
**Files:** `contracts/accepted/acep1-profile.md`, `contracts/accepted/semantics.md`, `contracts/manifest.json` (`normative_checkpoint: 75092aac79c39c6893900a0758ab176a47fe0c7a`), `tests/data/public-scientific-reference.v1.json` (`apt.sun-moon-content.v1-proposed`, `APTCanonicalSunMoonContent.v1-proposed`).
No renaming or premature acceptance of the proposed encoding identifiers is present; this matches the requirement that resolved human gates and `-proposed` suffixes must not be reopened or altered.

### OBSERVATION-5 — Extraction vs. deployment separation is explicit and consistent throughout
**Files:** `README.md`, `docs/governance.md`, `docs/extraction/checkpoint.md`, `docs/extraction/ledger.md`, `Dockerfile` (non-root `10001:10001`, `no-store`/no `/docs`/`/admin` claims are asserted in README, not verified by me here).
All parity/HTTPS evidence JSONs (`https-parity-948f6a2.json`, `https-parity-94c8103.json`, `image-source-94c8103.json`) are explicitly scoped to specific past revisions, explicitly state `"vps_deployment": "not performed"`/`"deployment": "not performed"`, and are not claimed to apply to the exact-head revision under review here. The ledger and checkpoint documents correctly flag remaining work (reviews A–H, final parity/source/image verification) as outstanding. I have not independently re-run any of this parity tooling; I am relying on the documents' own self-scoping statements.

---

## Evidence limitations

- I reviewed only the text supplied; I did not execute `make check`, the scientific artifact pipeline, the Docker build/smoke tests, or the Node/ACEP1 conformance tooling. The single CI record supplied (`35157967778`, `success`, matching head SHA) is accepted as reported, not re-verified.
- I cannot independently confirm that the pinned hashes (`BINARY_SHA256`, `DATA` entries, `TZIF` constant, manifest hash) actually correspond to the real upstream artifacts they claim to identify — I can only confirm internal consistency across the files shown to me (e.g., `identity.py` vs `worker.py` vs `scripts/scientific_artifacts.py` vs the test fixture provenance blocks all agree numerically).
- I have no visibility into the private reference/ACE execution described in `docs/extraction/checkpoint.md` and the `https-parity-*.json` files beyond their self-reported content; I make no claim about the correctness of the underlying astronomical values.
- This is a source-review opinion, not a security audit, penetration test, or legal/license certification, and does not substitute for the still-outstanding independent reviews A–H referenced in the ledger.

---

## Verdict

**APPROVE WITH NONBLOCKING FOLLOW-UPS**

Rationale: no Critical or High findings were identified in the Swiss-runtime/native-isolation/numerical-and-time-policy material at this exact head; the zero-tolerance binary64 policy, fallback-refusal checks, and cancellation/worker-limit design are implemented and covered by targeted tests. The Medium/Low items above (hash-pin duplication without a cross-check test, module- vs instance-scoped capacity semaphore, untested RLIMIT enforcement, and the per-process concurrency-cap coupling) are maintainability and defense-in-depth gaps, not demonstrated correctness or containment failures, and do not implicate any of the resolved human gates, the frozen `-proposed` encoding, or the extraction/deployment boundary, all of which remain correctly and explicitly unopened.
