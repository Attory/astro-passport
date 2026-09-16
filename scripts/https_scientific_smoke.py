# SPDX-License-Identifier: AGPL-3.0-only
"""Ephemeral local non-root/read-only container with real authenticated HTTPS.

No VPS, real tester credential, provider, public listener or private reference is used.
Temporary TLS/API secrets and operational quota state are removed on normal exit. Birth
inputs are independently public synthetic corpus cases; no real-person data is accepted.
"""

import argparse
import contextlib
import hashlib
import ipaddress
import json
import os
import secrets
import socket
import ssl
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from app.security import initialize_quota


def docker(*args):
    try:
        return subprocess.check_output(["docker", *args], stderr=subprocess.PIPE, text=True).strip()
    except subprocess.CalledProcessError as failure:
        # Docker arguments contain only local setup paths/identities, never API secrets.
        raise RuntimeError("local Docker operation failed: " + failure.stderr[:2000]) from None


@contextlib.contextmanager
def https_container(image: str, artifacts: Path):
    name = "apt-local-parity-" + secrets.token_hex(6)
    network = name + "-internal"
    docker("network", "create", "--internal", network)
    started = False
    try:
        network_info = json.loads(docker("network", "inspect", network))[0]
        subnet = ipaddress.ip_network(network_info["IPAM"]["Config"][0]["Subnet"])
        # Docker's static-IP contract requires an explicitly configured subnet.
        # Reuse the allocator-selected subnet of OUR empty network; do not guess a
        # host range or alter existing networks. A concurrent allocation fails closed.
        docker("network", "rm", network)
        docker("network", "create", "--internal", "--subnet", str(subnet), network)
        address = str(subnet.network_address + 2)
        with tempfile.TemporaryDirectory(prefix="apt-local-tls-") as temporary:
            folder = Path(temporary)
            subprocess.run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(folder / "key.pem"),
                    "-out",
                    str(folder / "cert.pem"),
                    "-days",
                    "1",
                    "-subj",
                    "/CN=localhost",
                    "-addext",
                    "subjectAltName=DNS:localhost,IP:" + address,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            (folder / "key.pem").chmod(0o600)
            secret = secrets.token_hex(32)
            key_id = secrets.token_hex(8)
            (folder / "keys.json").write_text(
                json.dumps(
                    [
                        {
                            "key_id": key_id,
                            "sha256": hashlib.sha256(secret.encode()).hexdigest(),
                            "expires_at": "2100-01-01T00:00:00Z",
                            "enabled": True,
                            "scope": "passport:calculate",
                            "per_minute": 60,
                        }
                    ]
                )
            )
            (folder / "keys.json").chmod(0o600)
            initialize_quota(folder / "quota.sqlite3")
            started = True  # Also clean up a created container if Docker start fails.
            docker(
                "run",
                "-d",
                "--name",
                name,
                "--network",
                network,
                "--ip",
                address,
                "--read-only",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--ulimit",
                "core=0",
                "--memory",
                "1536m",
                "--memory-swap",
                "1536m",
                "--pids-limit",
                "64",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=32m",
                "--mount",
                f"type=bind,src={artifacts.resolve()},dst=/science,readonly",
                "--mount",
                f"type=bind,src={folder},dst=/local-state",
                "--env",
                "APT_API_ENABLED=1",
                "--env",
                "APT_KEYS_FILE=/local-state/keys.json",
                "--env",
                "APT_QUOTA_FILE=/local-state/quota.sqlite3",
                "--env",
                "APT_SCIENCE_DIRECTORY=/science",
                image,
                "python",
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8443",
                "--ssl-keyfile",
                "/local-state/key.pem",
                "--ssl-certfile",
                "/local-state/cert.pem",
                "--no-access-log",
                "--no-proxy-headers",
                "--workers",
                "1",
                "--log-level",
                "critical",
            )
            inspection = json.loads(docker("inspect", name))[0]
            assert not inspection["HostConfig"]["PortBindings"]
            assert inspection["NetworkSettings"]["Networks"][network]["IPAddress"] == address
            assert json.loads(docker("network", "inspect", network))[0]["Internal"] is True
            url = "https://" + address + ":8443"
            context = ssl.create_default_context(cafile=str(folder / "cert.pem"))
            with httpx.Client(
                base_url=url,
                verify=context,
                trust_env=False,
                follow_redirects=False,
                timeout=httpx.Timeout(15, connect=2),
                transport=httpx.HTTPTransport(verify=context, trust_env=False, retries=0),
            ) as client:
                for _attempt in range(120):
                    try:
                        result = client.get("/health/ready")
                        if result.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("local scientific readiness failed")
                # Actual TLS negative tests, not a MockTransport construction assertion.
                try:
                    with httpx.Client(trust_env=False, timeout=2) as untrusted:
                        untrusted.get(url + "/health/live")
                except httpx.ConnectError:
                    pass
                else:
                    raise AssertionError("untrusted test certificate accepted")
                try:
                    with socket.create_connection((address, 8443), timeout=2) as connection:
                        with context.wrap_socket(connection, server_hostname="wrong.invalid"):
                            pass
                except ssl.SSLCertVerificationError:
                    pass
                else:
                    raise AssertionError("wrong TLS hostname accepted")
                headers = {
                    "Authorization": f"Bearer apt1.{key_id}.{secret}",
                    "X-APT-Contract-Version": "1.0.0",
                    "Content-Type": "application/json",
                }
                yield client, headers, name
    finally:
        if started:
            with contextlib.suppress(RuntimeError):
                docker("rm", "-f", name)
        with contextlib.suppress(RuntimeError):
            docker("network", "rm", network)


def smoke(image: str, artifacts: Path, revision: str):
    corpus = json.loads(Path("tests/data/public-scientific-reference.v1.json").read_bytes())
    with https_container(image, artifacts) as (client, headers, name):
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/version").json()["git_sha"] == revision
        assert client.get("/source").json()["source_archive"].endswith("/" + revision + ".tar.gz")
        for path in ("/docs", "/openapi.json", "/admin"):
            assert client.get(path).status_code == 404
        assert client.post("/v1/passports", json=corpus["cases"][0]["request"]).status_code == 401
        for case in corpus["cases"]:
            response = client.post("/v1/passports", headers=headers, json=case["request"])
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-apt-contract-version"] == "1.0.0"
            if "error" in case:
                assert response.status_code == case["status"] and response.json() == case["error"]
            else:
                expected = case["expected"]
                expected["provenance"]["source_revision"] = revision
                assert response.status_code == 200 and response.json() == expected
        logs = docker("logs", name)
        for case in corpus["cases"]:
            assert case["request"]["selected_place"]["query"] not in logs
            assert case["request"]["civil"]["date"] not in logs
        assert headers["Authorization"] not in logs
    print("Actual local HTTPS, exact source, scientific corpus, privacy and route checks passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    smoke(args.image, args.artifacts, args.revision)
