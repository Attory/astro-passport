"""Build an exact committed PUBLIC scaffold revision and record image/source correspondence.

This does not push an image, publish a release, deploy, install scientific dependencies, or
assert that a future scientific service has satisfied its release gates.
"""

import argparse
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path

REPOSITORY = "https://github.com/Attory/astro-passport"


def build(output: Path) -> None:
    if subprocess.check_output(["git", "status", "--porcelain"]):
        raise ValueError("build requires clean tracked and untracked state")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid revision")
    # Anonymous availability check: no environment token, credential helper or auth header.
    with urllib.request.urlopen(
        "https://api.github.com/repos/Attory/astro-passport/commits/" + revision, timeout=30
    ) as response:
        if json.load(response)["sha"] != revision:
            raise ValueError("exact source is not publicly available")
    lock = Path("compliance/source-lock.json").read_bytes()
    tag = "apt-source-checked:" + revision
    # Use git archive, not the working directory; ignored files/secrets cannot enter context.
    archive = subprocess.Popen(["git", "archive", "--format=tar", revision], stdout=subprocess.PIPE)
    try:
        subprocess.run(
            [
                "docker",
                "build",
                "--platform",
                "linux/amd64",
                "--build-arg",
                "GIT_SHA=" + revision,
                "--tag",
                tag,
                "-",
            ],
            stdin=archive.stdout,
            check=True,
        )
    finally:
        if archive.stdout is not None:
            archive.stdout.close()
        if archive.wait() != 0:
            raise ValueError("source archive failed")
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", tag]))[0]
    labels = image["Config"]["Labels"]
    if (
        image["Architecture"] != "amd64"
        or labels["org.opencontainers.image.revision"] != revision
        or labels["org.opencontainers.image.source"] != REPOSITORY
    ):
        raise ValueError("image/source identity mismatch")
    evidence = {
        "schema": "apt-image-source-correspondence.v1",
        "source_revision": revision,
        "source_repository": REPOSITORY,
        "source_archive": REPOSITORY + "/archive/" + revision + ".tar.gz",
        "source_lock_sha256": hashlib.sha256(lock).hexdigest(),
        "image_id": image["Id"],
        "platform": "linux/amd64",
        "scope": "scaffold only; not science/extraction clearance",
        "distribution": "not published",
        "deployment": "not performed",
    }
    with output.open("x") as stream:
        json.dump(evidence, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
