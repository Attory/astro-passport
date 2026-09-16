# Review ledger

## Gate 1 — public bootstrap

Target/root SHA: `0a31c4b157398b86799d586f10dfb5b937fa8f4d`.
Exact-head CI: [35086519869](https://github.com/Attory/astro-passport/actions/runs/35086519869), success.
Independent Claude, tool-disabled/output-only, public 18-file snapshot only, no private content.
Complete report: [bootstrap-report.md](bootstrap-report.md); identity/hash: [bootstrap-review.json](bootstrap-review.json).
Verdict: **APPROVE WITH NONBLOCKING FOLLOW-UPS**; no critical/high findings.

Dispositions (changed behavior requires fresh Gate 2 review):

- M1: GitHub root commit has zero parents; root tree includes full LICENSE. Public evidence retained
  in [bootstrap-evidence.json](bootstrap-evidence.json). No private history requested or transmitted.
- M2: GitHub API exact-head conclusion and individual steps retained; upstream action SHA resolution
  recorded. These are operator-fetched evidence, not claims Claude ran CI itself.
- L1/L2: added live Docker HEALTHCHECK and CI HTTP smoke inside actual read-only/network-none,
  non-root container, including exact baked source revision and blocked routes.
- L3: official PyPI metadata confirms mypy's ast-serialize/librt dependencies and exact versions.
  No signature/attestation verification claimed. These are development-only packages.
- L4: SPDX headers added to source/tests/scripts.
- Clarification: root image retained dependency dist-info licences and top-level notices; the
  inventory JSON itself is copied into the image starting with the next checkpoint, not the root.

No review here approves scientific extraction, a canonical schema release, client cutover or deployment.

## Gate 2 — API/auth/privacy candidate

Target: `99056e6f10805df3aeef4b69a34c51b41f55482f`; exact-head CI
[35088583397](https://github.com/Attory/astro-passport/actions/runs/35088583397), success, 58 tests.
Full independent report [api-report.md](api-report.md), identity [api-review.json](api-review.json),
public-only transmitted inventory [api-disclosure-manifest.json](api-disclosure-manifest.json).
Verdict: **APPROVE WITH NONBLOCKING FOLLOW-UPS**; no critical/high/medium findings.
Gate 1 follow-ups verified closed. Anonymous exact-commit source archive probe: HTTP 200,
64,844 bytes (availability only, not proof of a deployed runtime).

- L1: reviewer raised semaphore check/acquire race. The current event-loop fast path normally does
  not suspend while a permit is available, so an actual race was not demonstrated. Nonetheless,
  replace the pattern with atomic `Queue.get_nowait`/`QueueEmpty`, `finally` token restoration and a
  four-held/fifth-denied regression test. This removes dependence on semaphore fast-path reasoning.
  Changed runtime behavior must pass exact-head CI and a fresh independent review before closure.
- L2: explicitly document `forbidden` as reserved, not a currently emitted error; no schema change.
- L3: application header budget is not a transport parser limit; retain reviewed ingress limits as
  a mandatory activation gate, not an implemented protection claim.
- Clarify effective key-file UID access for non-root containers; no group/world-read workaround.

CI's pinned older Action revisions emit a Node 20 deprecation annotation (runner uses Node 24);
jobs pass. Upstream Action upgrade is a routine future maintenance item, not a scientific/runtime change.
