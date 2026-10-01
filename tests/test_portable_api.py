"""Authenticated compact issuance, offline trust, unavailable time and no retention."""

import copy
import json
import logging
import sqlite3
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.main import create_app
from passport_codec import CodecError, input_digest, unpack, verify
from tests.test_api import HEADERS, Spy, provision
from tests.test_science import science as science_fixture
from tests.test_western import western_request

science = science_fixture
PORTABLE_HEADERS = {**HEADERS, "X-APT-Contract-Version": "2.0.0"}


def signing(tmp_path):
    key = Ed25519PrivateKey.generate()
    path = tmp_path / "signing.pem"
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    return key, path


def body(unknown=False):
    data = western_request().model_dump(mode="json")
    data.update(schema_version="AstroPassportCompactRequest.v1", contract_version="2.0.0")
    if unknown:
        data["civil"]["time"] = None
    return data


def test_signed_issuance_offline_verification_and_no_payload_retention(science, tmp_path, caplog):
    settings = provision(tmp_path)
    key, path = signing(tmp_path)
    settings = replace(settings, signing_key_file=path, signing_key_id="synthetic-current")
    caplog.set_level(logging.DEBUG)
    with TestClient(create_app(settings, science), base_url="https://testserver") as client:
        data = body()
        response = client.post("/v2/passports", headers=PORTABLE_HEADERS, json=data)
        assert response.status_code == 200
        token = response.json()
        assert isinstance(token, str) and "=" not in token
        trusted = {b"synthetic-current": key.public_key().public_bytes_raw()}
        passport = verify(token, trusted, input_digest(data))
        actual = unpack(passport.payload()[5])
        old = client.post(
            "/v1/passports", headers=HEADERS, json=western_request().model_dump(mode="json")
        )
        assert old.status_code == 200 and actual == old.json()
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-apt-contract-version"] == "2.0.0"
        corrected = copy.deepcopy(data)
        corrected["civil"]["time"] = "12:01"
        with pytest.raises(CodecError, match="input_mismatch"):
            verify(token, trusted, input_digest(corrected))
        again = client.post("/v2/passports", headers=PORTABLE_HEADERS, json=data)
        assert again.json() == token  # Same facts/key; no issuance clock or request ID.
    with sqlite3.connect(settings.quota_file) as db:
        stored = "\n".join(db.iterdump())
    for private in (token, data["civil"]["date"], data["selected_place"]["query"]):
        assert private not in stored and private not in caplog.text
    assert {p.name for p in tmp_path.iterdir()} <= {"keys.json", "quota.sqlite3", "signing.pem"}


def test_unknown_time_signed_unavailability_without_precise_facts(science, tmp_path, monkeypatch):
    key, path = signing(tmp_path)
    settings = replace(provision(tmp_path), signing_key_file=path, signing_key_id="synthetic")
    calls = 0

    async def forbidden(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Unknown time must not invoke precise astronomy")

    monkeypatch.setattr(science, "calculate_portable", forbidden)
    with TestClient(create_app(settings, science), base_url="https://testserver") as client:
        response = client.post("/v2/passports", headers=PORTABLE_HEADERS, json=body(True))
        assert response.status_code == 200
        result = verify(
            response.json(),
            {b"synthetic": key.public_key().public_bytes_raw()},
            input_digest(body(True)),
        ).payload()
        assert result[4] == 1 and result[5] is None and result[6] is None
        assert unpack(result[3])["civil"]["time"] is None
        assert unpack(result[7])["reason"] == "unknown_birth_time"
        assert calls == 0


def test_portable_admission_and_missing_signer_do_zero_scientific_work(tmp_path):
    settings = provision(tmp_path)
    spy = Spy()
    with TestClient(create_app(settings, spy), base_url="https://testserver") as client:
        response = client.post("/v2/passports", json=body())
        assert response.status_code == 401
        response = client.post("/v2/passports", headers=HEADERS, json=body())
        assert response.status_code == 406 and response.json()["contract_version"] == "2.0.0"
        response = client.post("/v2/passports", headers=PORTABLE_HEADERS, json=body())
        assert response.status_code == 503 and response.json()["code"] == "state_unavailable"
        response = client.post(
            "/v2/passports", headers=PORTABLE_HEADERS, json={**body(), "member_id": "forbidden"}
        )
        assert response.status_code == 422
        assert spy.calls == 0


def test_portable_duplicate_json_and_nonfinite_inputs_reject(tmp_path):
    settings = provision(tmp_path)
    with TestClient(create_app(settings, Spy()), base_url="https://testserver") as client:
        raw = json.dumps(body())
        duplicate = raw[:-1] + ',"profile":"western-synastry-core.v1-mvp"}'
        assert (
            client.post("/v2/passports", headers=PORTABLE_HEADERS, content=duplicate).status_code
            == 422
        )
        invalid = raw.replace("-33.87", "NaN")
        assert (
            client.post("/v2/passports", headers=PORTABLE_HEADERS, content=invalid).status_code
            == 422
        )
