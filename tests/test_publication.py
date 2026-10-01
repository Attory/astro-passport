"""The public source offer and neutral grants must be independently usable."""

import json
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app import build
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_neutral_publication_is_narrow_and_pinned() -> None:
    codec = ROOT / "passport_codec"
    metadata = tomllib.loads((codec / "pyproject.toml").read_text())
    assert metadata["project"]["name"] == "astropassport-codec"
    assert metadata["project"]["version"] == "1.0.0"
    assert metadata["project"]["license"] == "Apache-2.0"
    assert (codec / "LICENSE").read_text().count("Apache License") >= 1
    assert (codec / "NOTICE").is_file()
    assert (ROOT / "contracts" / "LICENSE").is_file()
    assert (ROOT / "contracts" / "NOTICE").is_file()
    assert (ROOT / "LICENSE").read_text().startswith("                    GNU AFFERO")
    accepted = (ROOT / "contracts" / "accepted" / "schema.json").read_bytes()
    public = (ROOT / "contracts" / "astropassport" / "v1" / "schema.json").read_bytes()
    assert accepted == public
    assert json.loads(public)["$id"] == (
        "https://raw.githubusercontent.com/Attory/astro-passport/"
        "astropassport-schema-v1.0.0/contracts/astropassport/v1/schema.json"
    )


def test_v2_source_offer_is_public_and_exact(tmp_path: Path, monkeypatch: object) -> None:
    revision = "a" * 40
    path = tmp_path / "revision"
    path.write_text(revision + "\n")
    monkeypatch.setattr(build, "REVISION_FILE", path)  # type: ignore[attr-defined]
    with TestClient(create_app()) as client:
        response = client.get("/v2/source")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        data = response.json()
        assert data["git_sha"] == revision
        assert data["release_tag"] == "apt-v0.2.0"
        assert data["build_identity"] == f"git:{revision}"
        assert data["codec_license"] == data["schema_license"] == "Apache-2.0"
        assert data["codec_version"] == data["schema_version"] == "1.0.0"
        assert data["source_url"].endswith("/tree/" + revision)
        assert data["schema_source_url"].endswith(
            "/astropassport-schema-v1.0.0/contracts/astropassport/v1/schema.json"
        )
        assert data["supported_passport_profile"] == "western-synastry-core.v1-mvp"
        assert client.get("/v2/health/version").json() == data
