# Extraction checkpoint and review ledger

Starting APT: `dae015fd069308e408280d980e10ff72ed722488`.
Canonical AAC: `59500ec0951e082dd4c3984999b8a42fe4ce53c8` (PR #2 merge).
Frozen ACE: `18a3776bc1ab1dc52212b4de48a0df36709d72d2`, unchanged.

## Implementation checkpoint 948f6a2

Exact revision: `948f6a2e0ffa682d85e368b9457f9e5d6a682a3c`.
Local gates: 144 tests including actual pinned scientific execution; Ruff/mypy/schema and
compliance metadata checks, uv lock check, diff check; 44 independent Node vectors.
GitHub CI `35156558992` failed in the new local HTTPS harness, after tests and image build:
Docker internal networking did not supply a host port binding. Disposition: connect to an
explicit container address on the isolated network, certificate-verified, with NO host ports.
No Internet access, host networking or disabled TLS verification workaround was introduced.

The actual checkpoint image passed local HTTPS and separate frozen-reference parity using
that repaired local transport harness. Evidence: `https-parity-948f6a2.json` (23 public synthetic
cases, 13 successes, 10 classified failures, zero observed mismatches). This evidence applies
to the exact recorded image only, not to later revisions. No private corpus/payload is included.
No independent extraction approval is claimed yet.

## Follow-up surface

Retained-rule civil replay before UTC consumption; actual wrong-CA and wrong-host TLS negatives;
explicit participant-index comparison test; complete source-bundle assembly/reproduction;
installed scientific notices and failure-path tests. These changes require new exact-head
CI and fresh independent review. Reviews A–H and final parity/source/image verification remain
outstanding until recorded below. No deployment or ACE cutover has occurred.
