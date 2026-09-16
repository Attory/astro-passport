# APT bootstrap/API scaffold acceptance evidence

Date: 2026-09-16. Scope: public repository/bootstrap, candidate contract/security scaffold,
scientific extraction/equivalence design and VPS deployment plan. No scientific extraction,
golden execution, client cutover, credentials or remote deployment performed.

Canonical AAC merge baseline: `aa4373b5d7b2539adf5bc87c0b4cc7d392d2135d`, PR #1.
Parents: `c5fc9c7f58282d5ab7c5cab5f009fb21955e7855` and approved
`f7993f61797e2e8ca24e9248bd680316d4b250d8`. AAC main clean/synchronized; registries parsed;
there is no AAC CI workflow to claim. Existing private consumers/frozen architecture were preserved.

Public repository: <https://github.com/Attory/astro-passport>, default branch main.
Root/initial public commit: `0a31c4b157398b86799d586f10dfb5b937fa8f4d`, no parents, complete AGPL
licence present from commit zero. No private implementation/history copied. Public source availability
was tested anonymously; a deployed-version/source match cannot be tested because no service is deployed.

| Checkpoint | Exact SHA | Exact-head CI | Independent review |
| --- | --- | --- | --- |
| Bootstrap | `0a31c4b157398b86799d586f10dfb5b937fa8f4d` | [35086519869](https://github.com/Attory/astro-passport/actions/runs/35086519869), success | approve with nonblocking follow-ups |
| API/plans | `99056e6f10805df3aeef4b69a34c51b41f55482f` | [35088583397](https://github.com/Attory/astro-passport/actions/runs/35088583397), success | approve with nonblocking follow-ups |
| Admission hardening | `4763bb0efcd8e79f14b54acbf0454f5bc36841d8` | [35089255656](https://github.com/Attory/astro-passport/actions/runs/35089255656), failed regression fixture | not accepted as green |
| Corrected fixture / reviewed runtime | `82d14724028384ce5ee104953197e05bd70c5581` | [35089402312](https://github.com/Attory/astro-passport/actions/runs/35089402312), success | fresh approve with nonblocking follow-ups |

Latest code checkpoint: 59 tests pass; Ruff lint/format, mypy, frozen lock check, reproducible schema
bytes/digest and closed references, Git whitespace checks. CI builds pinned Docker, verifies UID/GID
10001, runs read-only/network-none/capability-free container and checks live/ready/source/version,
baked SHA, no-store and blocked docs/admin routes. No external scientific/provider call in tests.
Auth/quota/size/timeout/concurrency and privacy negatives use independently authored synthetic data.
Two upstream test-client deprecation warnings and older pinned Action Node annotation are retained
nonblocking maintenance items, not ignored test failures. Full outputs/dispositions: [ledger](../reviews/ledger.md).

Candidate API/schema `1.0.0` / `.v1` envelopes and `sun-moon.v1` profile are NOT canonical releases.
The manifest pins candidate bytes; no schema tag exists. The API defaults disabled and no engine
is installed; readiness always fails closed. Runtime packages are FastAPI/Pydantic/Uvicorn and their
recorded permissively licensed dependencies. No Swiss/TBB/tzdb/Shapely data or package is adopted yet.

**Scientific extraction not ready for implementation approval.** Remaining prerequisites:
AAC approval of detailed wire semantics and exact schema publication bytes/rights; complete reviewed
leaf comparator and required full ACEP1 profile/vectors (or explicitly approved bounded profile
scope); exact scientific artifact/native runtime rights/pins and public reproducible acquisition.
Then implement narrowly, run real-HTTP old/new scientific equivalence and obtain its mandatory
independent review. Source publication/licence review of the scaffold is not clearance for future
scientific distributions or the proprietary status of another service.

Separate later gates: human ACE cutover approval and downstream parity/rights review; whole-transition
audit; host/TLS/ingress/egress/resource and secret/quota provisioning review; public running-version
Corresponding Source verification; explicit deployment/activation approval. No root or secret is
needed to complete this documentation/scaffold checkpoint. The VPS plan makes no remote changes.
