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
