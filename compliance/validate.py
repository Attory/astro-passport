"""Fast offline coverage/preservation gate for the committed compliance records."""

import hashlib
import json
import re
import tomllib
from pathlib import Path

from compliance.bundle import checked


def validate(root: Path) -> None:
    folder = root / "compliance"
    lock = json.loads((folder / "source-lock.json").read_bytes())
    report = json.loads((folder / "correspondence.json").read_bytes())
    base = json.loads((folder / "base-image.json").read_bytes())
    seed = json.loads((folder / "discovery-inputs.json").read_bytes())
    notices = json.loads((folder / "native-notices.json").read_bytes())["notices"]
    if not notices:
        raise ValueError("native notices absent")
    for notice in notices:
        if (
            not notice["origins"]
            or hashlib.sha256(notice["text"].encode()).hexdigest() != notice["sha256"]
        ):
            raise ValueError("native licence notice corrupted")
    if lock["failures"] or lock["schema"] != "apt-runtime-source-lock.v1":
        raise ValueError("unresolved source acquisition")
    entries = lock["artifacts"]
    if (
        report["source_lock_sha256"]
        != hashlib.sha256(
            json.dumps(lock, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    ):
        raise ValueError("correspondence report is stale")
    names = [e["name"] for e in entries]
    if len(names) != len(set(names)) or report["artifact_count"] != len(entries):
        raise ValueError("source coverage mismatch")
    for entry in entries:
        checked(entry)
    for entry in seed["artifacts"]:
        if entry["name"] not in names:
            raise ValueError("seed artifact absent")
        selected = next(e for e in entries if e["name"] == entry["name"])
        if selected["url"] != entry["url"] or (
            "sha256" in entry and selected["sha256"] != entry["sha256"]
        ):
            raise ValueError("seed identity mismatch")
    sources = {(e["source_package"], e["source_version"]) for e in entries if "source_package" in e}
    installed = {(p["source_package"], p["source_version"]) for p in base["packages"]}
    proved = {(p["package"], p["version"]) for p in report["debian_sources"]}
    if sources != installed or proved != sources:
        raise ValueError("OS/source correspondence incomplete")
    if base["image"] != seed["base_image"] or base["architecture"] != "amd64":
        raise ValueError("base image changed")
    if base["python_distributions"] != [["pip", "25.0.1"]]:
        raise ValueError("unaccounted base Python distribution")
    for path, notice in base["copyrights"].items():
        if (
            not path.startswith("/usr/share/doc/")
            or hashlib.sha256(notice["text"].encode()).hexdigest() != notice["sha256"]
        ):
            raise ValueError("notice content mismatch")
    for package in base["packages"]:
        if (
            "/usr/share/doc/" + package["package"].split(":")[0] + "/copyright"
            not in base["copyrights"]
        ):
            raise ValueError("missing base package notice")
    docker = (root / "Dockerfile").read_text()
    if docker.count(seed["base_image"]) != 2:
        raise ValueError("Docker base identity changed")
    packages = tomllib.loads((root / "uv.lock").read_text())["package"]
    runtime = {p["name"] for p in packages if p["name"] == "astro-passport"}
    # Follow only the runtime dependencies, never mistake test tools for image contents.
    pending = list(runtime)
    while pending:
        name = pending.pop()
        package = next(p for p in packages if p["name"] == name)
        for dep in package.get("dependencies", []):
            if dep["name"] not in runtime:
                runtime.add(dep["name"])
                pending.append(dep["name"])
    for package in packages:
        if package["name"] in runtime and package["name"] != "astro-passport":
            component = package["name"] + "=" + package["version"]
            rows = [e for e in entries if e["component"] == component]
            if not any(e["name"].endswith(".whl") for e in rows) or not any(
                e["name"].endswith(".tar.gz") for e in rows
            ):
                raise ValueError("runtime wheel/source missing")
            for entry in rows:
                if entry["name"].endswith(".whl") and "sha256:" + entry["sha256"] not in {
                    w["hash"] for w in package["wheels"]
                }:
                    raise ValueError("runtime wheel differs from uv lock")
    for crate in report["rust_crates"]:
        if not crate["notices"] or not crate["license"]:
            raise ValueError("missing Rust notice")
    if len(report["rust_crates"]) != 103 or len(report["swiss_source_equal"]) != 27:
        raise ValueError("native source inventory changed")
    for line in report["native_lineage"].values():
        if not re.fullmatch(r"[a-f0-9]{64}", line["wheel_sha256"]):
            raise ValueError("native image identity missing")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parent.parent)
    print(
        "Compliance metadata/coverage verified; distribution still requires exact release evidence"
    )
