# SPDX-License-Identifier: AGPL-3.0-only
"""Independent synthetic contract/security fixtures; NOT a migrated birth corpus."""

import asyncio
import datetime as dt
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import api
from app.api import ScienceUnavailable
from app.contracts import AstroPassportRequestV1, AstroPassportResponseV1, CivilInput
from app.main import create_app
from app.security import KeyRecord, Settings, initialize_quota, reserve_quota

KEY_ID = "0" * 16
TEST_SECRET = "1" * 64  # Deliberately public, non-production test material.
AUTH = "Bearer apt1." + KEY_ID + "." + TEST_SECRET
HEADERS = {
    "Authorization": AUTH,
    "Content-Type": "application/json",
    "X-APT-Contract-Version": "1.0.0",
}


def payload() -> dict[str, object]:
    return {
        "schema_version": "AstroPassportRequest.v1",
        "contract_version": "1.0.0",
        "profile": "sun-moon.v1",
        "civil": {"date": "2000-01-02", "time": "03:04:05", "fold": None},
        "selected_place": {
            "schema_version": "SelectedPlaceInput.v1",
            "provider": "synthetic",
            "source_id": "not-a-person",
            "display_name": "Synthetic place",
            "latitude": 0.125,
            "longitude": 0.25,
            "attribution": None,
            "query": "synthetic  exact query",
            "requested_limit": 2,
            "selected_index": 0,
            "result_count": 1,
        },
    }


class Spy:
    def __init__(self) -> None:
        self.calls = 0

    async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
        self.calls += 1
        raise ScienceUnavailable


def provision(tmp_path: Path, limit: int = 60) -> Settings:
    keys = tmp_path / "keys.json"
    keys.write_text(
        json.dumps(
            [
                {
                    "key_id": KEY_ID,
                    "sha256": hashlib.sha256(TEST_SECRET.encode()).hexdigest(),
                    "expires_at": "9999-01-01T00:00:00Z",
                    "enabled": True,
                    "scope": "passport:calculate",
                    "per_minute": limit,
                }
            ]
        )
    )
    keys.chmod(0o600)
    quota = tmp_path / "quota.sqlite3"
    initialize_quota(quota)
    return Settings(True, keys, quota)


def test_valid_request_unavailable_and_private(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = provision(tmp_path)
    spy = Spy()
    caplog.set_level(logging.DEBUG)
    with TestClient(create_app(settings, spy), base_url="https://testserver") as client:
        response = client.post("/v1/passports", json=payload(), headers=HEADERS)
        assert response.status_code == 503 and response.json()["code"] == "science_unavailable"
        assert spy.calls == 1 and response.headers["cache-control"] == "no-store"
        assert "access-control-allow-origin" not in response.headers
        assert client.get("/source").status_code == 503  # Public without credentials; unbuilt.
    for secret in (TEST_SECRET, "2000-01-02", "synthetic  exact query", "Synthetic place"):
        assert secret not in caplog.text and secret not in response.text
    request = AstroPassportRequestV1.model_validate_json(json.dumps(payload()))
    assert "Synthetic" not in repr(request) and "2000" not in str(request)


def test_admission_saturation_is_immediate_and_releases_tokens(tmp_path: Path) -> None:
    settings = provision(tmp_path)

    async def scenario() -> None:
        release = asyncio.Event()
        full = asyncio.Event()

        class Holding:
            calls = 0

            async def calculate(self, request: AstroPassportRequestV1) -> AstroPassportResponseV1:
                self.calls += 1
                if self.calls == 4:
                    full.set()
                await release.wait()
                raise ScienceUnavailable

        science = Holding()
        app = create_app(settings, science)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://testserver"
        ) as client:
            tasks = [
                asyncio.create_task(client.post("/v1/passports", json=payload(), headers=HEADERS))
                for _ in range(4)
            ]
            try:
                await asyncio.wait_for(full.wait(), 2)
                denied = await asyncio.wait_for(
                    client.post("/v1/passports", json=payload(), headers=HEADERS), 1
                )
                assert denied.status_code == 503 and denied.json()["code"] == "busy"
                assert science.calls == 4
            finally:
                release.set()
                results = await asyncio.gather(*tasks)
            assert all(result.json()["code"] == "science_unavailable" for result in results)
            result = await client.post("/v1/passports", json=payload(), headers=HEADERS)
            assert result.json()["code"] == "science_unavailable" and science.calls == 5

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mutation,status",
    [
        ("auth", 401),
        ("version", 406),
        ("media", 415),
        ("encoding", 415),
        ("length", 413),
        ("query", 400),
        ("http", 400),
        ("duplicate", 400),
        ("disabled", 503),
    ],
)
def test_early_denials_zero_science(tmp_path: Path, mutation: str, status: int) -> None:
    settings = provision(tmp_path)
    spy = Spy()
    headers = dict(HEADERS)
    path = "/v1/passports"
    base = "https://testserver"
    if mutation == "auth":
        headers["Authorization"] = "Bearer invalid"
    if mutation == "version":
        headers["X-APT-Contract-Version"] = "2.0.0"
    if mutation == "media":
        headers["Content-Type"] = "text/plain"
    if mutation == "encoding":
        headers["Content-Encoding"] = "gzip"
    if mutation == "length":
        headers["Content-Length"] = "999999"
    if mutation == "query":
        path += "?credential=not-allowed"
    if mutation == "http":
        base = "http://testserver"
    if mutation == "disabled":
        settings = Settings()
    pairs = list(headers.items())
    if mutation == "duplicate":
        pairs.append(("Authorization", AUTH))
    with TestClient(create_app(settings, spy), base_url=base) as client:
        result = client.post(path, json=payload(), headers=pairs)
    assert result.status_code == status and spy.calls == 0


@pytest.mark.parametrize(
    "case", ["missing", "permissions", "corrupt", "symlink", "expired", "revoked"]
)
def test_credentials_fail_closed(tmp_path: Path, case: str) -> None:
    settings = provision(tmp_path)
    spy = Spy()
    assert settings.keys_file
    if case == "missing":
        settings.keys_file.unlink()
    elif case == "permissions":
        settings.keys_file.chmod(0o644)
    elif case == "corrupt":
        settings.keys_file.write_text("not-json-SECRET")
    elif case == "symlink":
        original = tmp_path / "actual"
        settings.keys_file.rename(original)
        settings.keys_file.symlink_to(original)
    else:
        data = json.loads(settings.keys_file.read_text())
        if case == "expired":
            data[0]["expires_at"] = "2000-01-01T00:00:00Z"
        else:
            data[0]["enabled"] = False
        settings.keys_file.write_text(json.dumps(data))
    with TestClient(create_app(settings, spy), base_url="https://testserver") as c:
        r = c.post("/v1/passports", json=payload(), headers=HEADERS)
    assert r.status_code == (401 if case in ("expired", "revoked") else 503) and spy.calls == 0
    assert "SECRET" not in r.text


def test_quota_survives_restart_and_unavailable_state(tmp_path: Path) -> None:
    settings = provision(tmp_path, 1)
    spy = Spy()
    for expected in (503, 429):
        with TestClient(create_app(settings, spy), base_url="https://testserver") as c:
            r = c.post("/v1/passports", json=payload(), headers=HEADERS)
        assert r.status_code == expected
    assert spy.calls == 1 and settings.quota_file
    settings.quota_file.unlink()
    with TestClient(create_app(settings, spy), base_url="https://testserver") as c:
        assert (
            c.post("/v1/passports", json=payload(), headers=HEADERS).json()["code"]
            == "state_unavailable"
        )
    assert not settings.quota_file.exists() and spy.calls == 1


def test_atomic_quota_clock_rollback_and_no_overwrite(tmp_path: Path) -> None:
    settings = provision(tmp_path, 1)
    assert settings.keys_file and settings.quota_file
    key = KeyRecord.model_validate(json.loads(settings.keys_file.read_text())[0])
    now = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: reserve_quota(settings.quota_file, key, now), range(4)))
    assert results.count(True) == 1
    assert reserve_quota(settings.quota_file, key, now + dt.timedelta(minutes=1))
    with pytest.raises(Exception, match="security state unavailable"):
        reserve_quota(settings.quota_file, key, now)
    with pytest.raises(FileExistsError):
        initialize_quota(settings.quota_file)


@pytest.mark.parametrize("body", [b'{"a":1,"a":2}', b"NaN", b"{", b"[]", b'"secret"'])
def test_malformed_body_safe(tmp_path: Path, body: bytes) -> None:
    settings = provision(tmp_path)
    spy = Spy()
    with TestClient(create_app(settings, spy), base_url="https://testserver") as c:
        r = c.post("/v1/passports", content=body, headers=HEADERS)
    assert r.status_code == 422 and spy.calls == 0 and "secret" not in r.text


def test_stream_size_and_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = provision(tmp_path)
    spy = Spy()
    app = create_app(settings, spy)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://testserver"
        ) as c:

            async def oversized():
                yield b" " * (api.MAX_BODY + 1)

            assert (
                await c.post("/v1/passports", content=oversized(), headers=HEADERS)
            ).status_code == 413
            monkeypatch.setattr(api, "BODY_SECONDS", 0.01)

            async def slow():
                yield b"{"
                await asyncio.sleep(0.1)
                yield b"}"

            assert (
                await c.post("/v1/passports", content=slow(), headers=HEADERS)
            ).status_code == 408

    asyncio.run(run())
    assert spy.calls == 0


@pytest.mark.parametrize(
    "field", ["sex", "gender", "account_id", "astro_id", "score", "timezone", "flags"]
)
def test_private_or_computed_inputs_forbidden(field: str) -> None:
    data = payload()
    data[field] = "not-allowed"
    with pytest.raises(ValueError):
        AstroPassportRequestV1.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "date,time,fold",
    [
        ("2000-02-30", "12:00", None),
        ("1899-12-31", "12:00", None),
        ("2101-01-01", "12:00", None),
        ("2000-01-01", "12:00Z", None),
        ("2000-01-01", "23:59:60", None),
        ("2000-01-01", "12:00", True),
        ("2000-01-01", "12:00", 2),
    ],
)
def test_civil_input_no_guessing(date: str, time: str, fold: object) -> None:
    with pytest.raises(ValueError):
        CivilInput.model_validate_json(json.dumps({"date": date, "time": time, "fold": fold}))


@pytest.mark.parametrize("value", [91, -91, float("nan"), float("inf"), True, "12.0"])
def test_invalid_coordinates(value: object) -> None:
    data = payload()
    data["selected_place"]["latitude"] = value
    with pytest.raises(ValueError):
        AstroPassportRequestV1.model_validate_json(json.dumps(data))


def test_exact_query_and_coordinates() -> None:
    data = payload()
    data["selected_place"]["latitude"] = 59.123456789012345
    checked = AstroPassportRequestV1.model_validate_json(json.dumps(data))
    assert checked.selected_place.query == "synthetic  exact query"
    assert checked.selected_place.latitude.hex() == (59.123456789012345).hex()
