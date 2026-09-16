# Scaffold security policy and future activation gates

Single process/worker, default disabled. `APT_API_ENABLED=1` only enables the fail-closed scaffold,
not science. `APT_KEYS_FILE` and `APT_QUOTA_FILE` identify local private files; no secrets in env
examples, Git, URL, response, repr, ordinary logs or command arguments. No provider credential exists.

Operational envelope: at most 16 configured credentials, each 1–60 attempts per UTC minute;
16 KiB request body; 16 KiB combined application header bytes; 2 s body deadline; 6 s future engine
deadline; four concurrent admissions including auth/body/engine. Reverse proxy must impose
connection/header/idle/global-rate budgets before activation; application limits do not bound the
network parser. Native workers must independently enforce kill/resource limits before any engine
is installed: cancelling an async call alone cannot safely cancel a native computation.

Credentials are independent high-entropy 256-bit secrets with 64-bit opaque IDs, explicit UTC
expiry, enabled/revoked flag and `passport:calculate` scope. Server stores SHA-256 verification
values, compares digests in constant time, reloads the bounded file each request. Configuration
example is the schema of `app.security.KeyRecord`, not a reusable secret. A future offline operator
provisioner must generate with a CSPRNG, transmit once via approved secret delivery, atomically
replace the verification file and bound rotation overlap. Do not provision real credentials now.

Credential file: root/service-owned regular 0600 file, read-only mount, no symlink/FIFO. Quota file:
service-owned 0600 regular file in a service-owned 0700 directory; bounded to 1 MiB/128 credential
rows. Use only trusted operator paths; parents must not be attacker writable. SQLite rollback
journals stay in this private directory. No birth data or outputs are stored: only key ID, UTC
minute bucket and count. No account/IP/user metadata or long-term usage history. The stdlib SQLite
file is minimal durable operational state, not a shared/application database or new dependency.

`initialize_quota(path)` is an explicit local provisioning operation with exclusive create;
never automatically invoked at startup. Missing/corrupt/inaccessible state fails closed. Atomic
transactions persist reservations across restarts; rollback clocks fail closed. Existing state
must not be deleted to bypass quotas. An operator retention/compaction policy is required before
128 lifetime IDs are reached. Scaling beyond this single-node design requires reviewed shared
quota semantics; per-replica independent files are prohibited. Counters may charge failed requests.

Authentication, version/media/size, quota and validation precede scientific work. Disabled,
unauthorized, expired/revoked, oversized, malformed and exhausted requests invoke no science.
No scientific or provider process exists in this checkpoint. Responses are no-store; API does not
log bodies, headers, errors or tracebacks. Uvicorn access logging is disabled. Proxy/host logging
must also exclude paths/query/auth/body details; no telemetry/exporter is present.

Before activation: independently reviewed actual TLS/forwarded-header topology, resource limits,
global abuse limit, durable secret/quota provisioning/rotation, zero-work negative tests through
proxy, scientific isolation, artifact integrity, source availability, downstream source offer and
explicit approval. Current Docker disables proxy-header trust and consequently rejects calculation
through an HTTP proxy connection. A reviewed exact-peer or private Unix-socket TLS-termination
configuration is required; never enable wildcard forwarded-header trust as a quick fix.

TLS does not encrypt stored datasets/state or sign passports. No birth retention is allowed here.
If retention is later approved it needs a separate encryption/key/retention design. Unsigned direct
client trust is intentionally restricted. Certificate/signature-key compromise and rotation policy
must be approved before the respective feature is activated; no identity signing is implemented.
