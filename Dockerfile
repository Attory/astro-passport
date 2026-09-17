FROM ghcr.io/astral-sh/uv:0.12.10@sha256:2bb3ebca0a796a155094a27773d290c4b074572e6107f171d88d086682fd2500 AS uv
FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /opt/apt
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
ARG GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/Attory/astro-passport" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.revision="${GIT_SHA}"
WORKDIR /opt/apt
ENV PATH="/opt/apt/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 aptservice && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin aptservice
COPY --from=builder /opt/apt/.venv /opt/apt/.venv
COPY app ./app
COPY LICENSE THIRD_PARTY_NOTICES.md /usr/share/doc/astro-passport/
COPY docs/runtime-licenses.json /usr/share/doc/astro-passport/
COPY compliance/source-lock.json compliance/correspondence.json compliance/README.md /usr/share/doc/astro-passport/compliance/
COPY compliance/native-notices.json /usr/share/doc/astro-passport/compliance/
RUN GIT_SHA="$GIT_SHA" python -c 'import os,re,pathlib; s=os.environ["GIT_SHA"]; assert re.fullmatch("[0-9a-f]{40}",s); pathlib.Path("app/_revision").write_text(s+"\n",encoding="ascii")'
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live',timeout=2).read()"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers", "--workers", "1"]
