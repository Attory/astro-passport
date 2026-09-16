from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import build
from app.main import create_app


def test_inactive_boundaries() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        for path in ("/docs", "/openapi.json", "/admin", "/v1/passports"):
            response = client.get(path)
            assert response.status_code == 404
            assert response.headers["cache-control"] == "no-store"


def test_immutable_source_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "revision"
    monkeypatch.setattr(build, "REVISION_FILE", path)
    with TestClient(create_app()) as client:
        assert client.get("/source").status_code == 503
        path.write_text("a" * 40 + "\n")
        source = client.get("/source")
        assert source.status_code == 200
        assert source.json()["source_url"] == build.REPOSITORY + "/tree/" + "a" * 40
        monkeypatch.setenv("GIT_SHA", "b" * 40)
        assert client.get("/health/version").json()["git_sha"] == "a" * 40
        path.write_text("../../not-a-revision")
        assert client.get("/source").status_code == 503
