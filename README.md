# Astro Passport Transformer (APT)

Public **AGPL-3.0-only** service scaffold. **Not deployed; no scientific engine implemented.**
APT is intended to produce deterministic geographic, civil-time and astronomical facts for one
person. It does not calculate compatibility, scores, interpretation or social/account identity.

Canonical AAC architecture baseline: `aa4373b5d7b2539adf5bc87c0b4cc7d392d2135d`.
See [governance](docs/governance.md), [licensing/source](docs/licensing.md) and
[third-party notices](THIRD_PARTY_NOTICES.md). No private repository is needed to build or test.

## Local development

Python 3.12, uv 0.12.10, GNU Make and Git are required.

```sh
uv sync --frozen
make check
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

`GET /health/live` reports process liveness. `/health/ready` intentionally returns 503 until a
reviewed scientific implementation and its prerequisites exist. `/health/version` and `/source`
expose only safe source/build metadata. An unbuilt checkout returns 503 from these identity
endpoints rather than pretending its source revision is known. `/docs`, `/openapi.json` and
`/admin` are absent. All responses are `no-store`. No automatic deployment exists.

The [API contract candidate](contracts/README.md) defines `/v1/passports` and typed wire envelopes;
it is default-disabled and has no scientific engine. See [security](docs/security.md),
[extraction plan](docs/extraction-plan.md), [equivalence design](docs/equivalence-design.md) and
[deployment plan](docs/deployment-plan.md). No canonical schema tag/release is approved yet.

Build a clean committed revision using Docker:

```sh
docker build --build-arg GIT_SHA="$(git rev-parse HEAD)" -t astro-passport:local .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m -p 127.0.0.1:8000:8000 astro-passport:local
```

Do not expose the scaffold to external users. A source link and public GitHub repository alone
are not an activation approval or proof of a future deployed source/runtime match.
