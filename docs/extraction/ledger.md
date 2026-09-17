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

## Hardening checkpoint 94c8103

Exact revision: `94c81038e5fa100068a113168ddd4b23ef845abf`.
All 155 local tests and 44 Node vectors passed. Exact image/source receipt and fresh measured
HTTPS parity are retained in `image-source-94c8103.json` and `https-parity-94c8103.json`:
23 public synthetic cases, zero mismatches, exact partial ACEP1 bytes. ACE was unchanged.

Complete source assembly was reproduced twice byte-for-byte (1,147,299,840 bytes):
`d59e61e2a551bd947085d65b3fcfe6f69eaf7e98b54becaaac845b81a9b66061`.
The third-party bundle remains
`6a02fb511282c5519f53d5df54de0d3373d7ede482ec5599c6ec9c0fae1c82ef`.
The full offline native/OS correspondence report equals the reviewed committed report.
Bundles are retained locally, not publicly activated/released; anonymous retained-bundle
delivery and downstream source-offer verification remain pre-distribution/activation gates.

GitHub run `35157462145`: source correspondence/bundle job ran independently; application
tests/build passed, but the local HTTPS fixture failed creating a static-address container.
The fixture now explicitly configures the subnet selected for its own empty internal network,
as required by [Docker's static-IP contract](https://docs.docker.com/reference/cli/docker/container/run/).
It changes no existing network and fails on allocation conflicts. Bounded Docker diagnostics
and cleanup cover failed starts. Production scientific code is unchanged by this portability fix.

## Green transport checkpoint and focused reviews

`3617ab0c208cbd56927e0b84574b778e832ca8a1`: GitHub CI **35157967778 successful**, including
application/scientific/local-HTTPS container checks and exact native-source audit/bundle reproduction.
Disclosure manifests committed at `5b5007e2f62d78467e34b4e6ccdfff3e2e25902a` (CI **35158491554 successful**).
Complete five A–E reports and two quota-error outputs retained by commit `790ddb1`.
All five completed reviews: APPROVE WITH NONBLOCKING FOLLOW-UPS; no blocking finding.
F/G returned no actual review (Claude session limit, reset reported 10:50 Australia/Sydney).
They do not count as approvals. Full disposition: `review-dispositions.md`.

## Comparator/resource-test repair checkpoint

Exact revision: `aeb0bca2857f4921656464e18e0713cb82ac510f`.
212 local tests and 44 independent Node vectors passed, along with Ruff, format, mypy,
accepted-schema comparison, compliance metadata, uv lock and diff checks. Existing two
upstream test-client deprecation warnings are retained; no dependency upgrade made.
Application/scientific code under `app/` is unchanged from the reviewed 3617ab0 tree.
The executable comparator gained full retained-stage error dispatch/tests; F review must
cover this revision or later. Runtime native limits are now tested in real child processes.

Fresh separate frozen-ACE → authenticated, certificate-verified local HTTPS APT parity:
`https-parity-aeb0bca.json` and exact `image-source-aeb0bca.json`. All 23 independently public
synthetic cases passed (13 successes, 10 errors). Repeated calls and exact partial ACEP1 bytes
matched. Failures were compared to freshly executed old-stage evidence, not just static goldens.
All seven mismatch-classification counts are zero; DELIVERY_METADATA_ONLY has zero comparisons
for this successful-output/bounded-error corpus, not a fabricated coverage count.
No real-person migration corpus was used or published. Restricted helper hashes and both exact
image IDs are retained; private pair manifests stayed in process memory. No forensic RAM-erasure
claim is made. Host swap policy was not changed; containers disabled swap/core dumps.

Complete Corresponding Source reproduced twice and compared equal locally:
1,147,535,360 bytes, SHA256
`a62fe004056ee922cf90825fc044c1ecdf8443bb99f509a61ccb1c7adc00165f`.
Exact APT source archive hash:
`ed606211e166e33a5c9dc00763bd8b46994bd7a99d3911d53d6d687ebb2cdb80`.
Third-party bundle hash and all 396 source pins unchanged. No binary distribution or activation
has occurred; anonymous complete-bundle delivery remains a pre-distribution/activation gate.

Preservation: AAC main `59500ec0951e082dd4c3984999b8a42fe4ce53c8` clean/synchronized;
ACE main `18a3776bc1ab1dc52212b4de48a0df36709d72d2` unchanged/clean;
frozen annotated architecture tag peels to `04b20c8eaed9106e3b299e8d97bdf6fc4452c82d`.
No SSH/VPS deployment, ACE client/cutover or scientific code removal performed.

## Resumed final reviews — d5d659c

Reviewed target: `d5d659ce44dab90049019d0df9f8f848dd2fed33`; exact-head CI
**35159954335 successful**. No extraction or scientific execution is restarted for review.
Existing exact target receipts are now committed: `https-parity-d5d659c.json`,
`image-source-d5d659c.json`, `source-bundle-d5d659c.json`.
Complete source bundle: `4336febf4f83918e7cd2ea9bab0a81339665f01f4d5bbbe2ba389da51c45941c`,
1,147,545,600 bytes, two independent assemblies equal (retained copies rehashed during review).
Fresh previous measured HTTPS parity remains 23/13/10, zero mismatches, exact canonical bytes.

New public-only disclosure manifests were committed at `5885fcc549d1a2ccefc91d2699badfb920ed0675`
before invoking tool-disabled F/G calls. Both completed actual reports with verdict
**APPROVE WITH NONBLOCKING FOLLOW-UPS**. No required source/build absence or blocking scientific
comparator defect found. Reports are retained in full, including reviewer arithmetic mistakes;
correct dispositions and precise scope of non-equality classes are in `review-dispositions.md`.
Supplementary read-only public-archive evidence resolves the missing-documentation points without
changing runtime, science, comparator, dependency pins, accepted contracts or source-bundle tooling.
H and final exact-head gates remain required. No new A–E review is needed absent a material repair.

## Whole-extraction review completion

H target: **8c45ff11c5ecb13f9e270a8aa5f670cc53e5e2b9**; exact-head CI **35207611341 SUCCESS**.
H disclosure commit: **44cfa8bdc3f6bbe00aab5b0bf81514aa7918dd87**.
H verdict: **APPROVE WITH NONBLOCKING FOLLOW-UPS**. No earlier nonblocking finding became blocking.
Complete report/process output and disclosure manifest retained; dispositions correct two reviewer
evidence-reading errors without rewriting the original report or overclaiming review coverage.

The new H evidence condition is closed by `review-h-diff.json`, proving every non-docs file at
H target equals the measured d5d659c checkpoint. All resumed changes are docs/review evidence only;
no extraction restart, scientific/comparator/runtime repair, dependency/pin or normative byte change.
Therefore measured d5d659c HTTPS parity is retained rather than falsely relabeled as a later run.

Precise measured checks: **4,820 classified row checks** = 4,144 cross-path value/error rows
(3,718 exact + 234 mapped derivations + 130 identity substitutions + 62 outcome/errors), 156
old composed-digest retention checks, 364 intentional-absence and 156 non-comparable manifest
checks. Delivery-only has zero exercised checks. All seven mismatch counts are zero. This is
not equality of private pair methodology/identity or independent astronomical accuracy.

Final handoff must include final exact-head CI and two identical complete source assemblies of
the final evidence commit. The d5d659c bundle remains historical and is not reused as that hash.
No scientific change requires repeating private parity or A–E. All normal local gates will be
rerun after H; source assembly follows the final evidence commit to avoid self-referential hashes.
Post-H local result: **212 tests and 44 independent Node vectors passed**; Ruff, formatting,
mypy, exact accepted schema, compliance validation, uv lock check and git diff check passed.
Only the two previously recorded upstream test-client deprecation warnings remain.
No deployment, source-offer activation, client cutover or ACE modification is authorized/performed.
