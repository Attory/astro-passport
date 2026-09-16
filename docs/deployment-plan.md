# Separate APT VPS deployment plan — no deployment authorized/performed

Target: the separately approved Ubuntu APT VPS; operator inventory holds its address. Domain/DNS,
host access and credentials are future operational inputs, not committed here. No SSH, firewall,
packages, remote files or other services are changed by this plan.

Topology: Internet → Caddy TLS (only 80/443 host ports) → APT private non-root service → local pinned
scientific data. No birth database. No shared network/database/runtime with ACE or AIS. Science has
no Internet egress. Caddy may reach ACME but not other private services. Never mount Docker socket,
use privileged/host networking or publish the app port. No deployment workflow in GitHub Actions.

Use dedicated deploy/service identities; deployment-user Docker access is host-root-equivalent and
must be explicitly approved. App UID/GID 10001, read-only root, no capabilities, no-new-privileges,
bounded RAM/CPU/PIDs, private tmpfs. Read-only key verification file and licensed artifacts; sole
writable persistent operational directory is the 0700 quota state, not scientific inputs/results.
Proposed layout `/srv/astro-passport/{releases,secrets,state,artifacts,evidence}` with exact modes
and safe artifact hashes validated before starting. Do not perform these host operations yet.

Before drafting executable Compose/Caddy deployment: verify host conflicts, TLS 1.2+ policy,
real domain, ACME operation and a private Unix-socket or exact-peer trusted-proxy scheme preserving
the external HTTPS assertion without trusting arbitrary X-Forwarded-* headers. Existing container
ignores forwarded headers deliberately. HTTP computational POSTs must be rejected, not redirected
with secrets/body; only harmless GETs may redirect. Request/global-rate/connection/body/time limits
must be enforced at ingress as well as app admission. No access/body/query/authorization logs,
no wildcard CORS, no admin/docs/OpenAPI exposure, all result/error pages no-store.

Deployment sequence after separate approval: fetch approved exact public SHA; verify clean source,
artifact hashes/licences and image identity; build/pin immutable image; provision separately approved
key hashes and durable quota state; start disabled/private; verify source archive anonymously;
test actual TLS/auth/proxy/size/quota/concurrency/privacy/egress/health/version boundaries; verify
scientific golden calls; only then enable computational access under explicit activation approval.
Liveness alone never proves scientific readiness. Current ready stays 503 and engine is unavailable.

Source gate: anonymously download the exact running revision's Corresponding Source and required
control/build sources; match image SHA and notices; verify downstream source offers, not merely
repository visibility. Preserve required TBB/tzdb/Swiss/native legal artifacts and retention plan.
Unsigned passports stay direct-client-only. Certificate compromise/rotation/revocation drill and
separate stored-data/signature decisions remain gates. No real credentials are provisioned here.

Rollback to a known-good APT image plus exact compatible data/profile/API; retain quota state so
restarts do not replenish budgets. Never reverse database migrations (none here) or hide errors by
restoring Swiss inside a proprietary client. Disable API on source/artifact/auth integrity failure.
Future cloud deployment preserves quota semantics and qualifies any changed native platform.
