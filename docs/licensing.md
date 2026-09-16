# Licensing and source delivery

This new scaffold is **AGPL-3.0-only from its first public commit**. See the complete [licence](../LICENSE)
and [notices](../THIRD_PARTY_NOTICES.md). There is no Swiss Professional entitlement claim.
The scaffold is newly authored; no private implementation or Git history is copied here.
The standard upstream AGPL licence text is not private implementation.

Public source: <https://github.com/Attory/astro-passport>. A release must retain its exact source
commit, lockfile, Docker/build instructions, editable contract sources and public synthetic tests.
No private repository, generator, dataset credential, corpus or package may be necessary to
obtain the service's Corresponding Source. Independently needed datasets and their build/control
sources must be legally available and pinned before they enter a runtime release.

The immutable build revision is baked into the image, not read from a runtime environment variable.
Unauthenticated `/source` and `/health/version` provide an exact Git source/tree/archive and licence
link. Unknown build identity fails closed. API-key protection of computation must not protect the
source offer. Downstream interfaces must prominently surface the exact running-version source
offer as applicable; do not assume developer-only visibility satisfies remote-user obligations.

Before any network activation, verify the running SHA matches public downloadable Corresponding
Source, rebuild instructions and retained notices/artifacts. Review downstream offer reachability
and applicable legal interpretation. No publication of unrelated private services is authorized.
AGPL rights already granted in another repository are not revoked by this extraction proposal.

Reference: [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.en.html), particularly its definitions
of Corresponding Source and remote-network interaction provision. This is an engineering
compliance checklist, not legal clearance for a future dependency/combined work.
