# Astro Passport Transformer (APT)

Public **AGPL-3.0-only** service. **Scientific extraction under validation; not deployed.**
APT produces deterministic geographic, civil-time and astronomical facts for one
person. It does not calculate compatibility, scores, interpretation or social/account identity.

Canonical AAC architecture baseline: `59500ec0951e082dd4c3984999b8a42fe4ce53c8`.
See [governance](docs/governance.md), [licensing/source](docs/licensing.md) and
[third-party notices](THIRD_PARTY_NOTICES.md). No private repository is needed to build or test.

## Local development

Python 3.12.14 on Linux amd64, uv 0.12.10, GNU Make, GCC and Git are required.

```sh
uv sync --frozen
make check
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

`GET /health/live` reports process liveness. `/health/ready` returns 503 unless explicit local
scientific configuration and all pinned execution prerequisites validate. `/health/version` and `/source`
expose only safe source/build metadata. An unbuilt checkout returns 503 from these identity
endpoints rather than pretending its source revision is known. `/docs`, `/openapi.json` and
`/admin` are absent. All responses are `no-store`. No automatic deployment exists.

The [accepted contract](contracts/README.md) defines `/v1/passports` and typed wire envelopes;
the API remains default-disabled. See [security](docs/security.md),
[extraction plan](docs/extraction-plan.md), [equivalence design](docs/equivalence-design.md) and
[deployment plan](docs/deployment-plan.md). No canonical schema tag/release is approved yet.

Run the full scientific tests with exact publicly acquired artifacts (no private repositories):

```sh
uv run --frozen python -m scripts.scientific_artifacts --cache /tmp/apt-public-cache --output /tmp/apt-public-artifacts
APT_TEST_ARTIFACTS=/tmp/apt-public-artifacts make check
node conformance/acep1.mjs
```

CI always prepares these artifacts and runs the scientific corpus. Tests without the explicit
artifact location report scientific skips; that is not a full scientific acceptance run.
See [extraction evidence](docs/extraction/checkpoint.md) for provenance and remaining review gates.

Build a clean committed revision using Docker:

```sh
docker build --build-arg GIT_SHA="$(git rev-parse HEAD)" -t astro-passport:local .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m -p 127.0.0.1:8000:8000 astro-passport:local
```

Do not expose this service to external users yet. A source link and public GitHub repository alone
are not an activation approval or proof of a future deployed source/runtime match.
