# SPDX-License-Identifier: AGPL-3.0-only
"""Executed inside a network-none CI container; no public deployment or provider calls."""

import json
import os
import time
import urllib.error
import urllib.request


def fetch(path: str) -> tuple[int, dict[str, str], bytes]:
    try:
        response = urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=2)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, dict(response.headers.items()), response.read()


for attempt in range(30):
    try:
        assert fetch("/health/live")[0] == 200
        break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(0.2)
assert fetch("/health/ready")[0] == 503
for path in ("/source", "/health/version"):
    status, headers, body = fetch(path)
    assert status == 200
    assert {k.lower(): v for k, v in headers.items()}["cache-control"] == "no-store"
    value = json.loads(body)
    assert value["git_sha"] == os.environ["EXPECTED_SHA"]
    assert value["source_archive"].endswith("/" + os.environ["EXPECTED_SHA"] + ".tar.gz")
for path in ("/docs", "/openapi.json", "/admin"):
    assert fetch(path)[0] == 404
print("container liveness/readiness/source/version/route boundary passed")
