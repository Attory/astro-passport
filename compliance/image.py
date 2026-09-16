"""Read-only inventory of the pinned public base image; no service or science execution."""

import argparse
import json
import subprocess
from pathlib import Path

INSPECT = r"""
import hashlib, importlib.metadata, json, pathlib, subprocess, sys
raw = subprocess.check_output(['dpkg-query', '-W', '-f', '${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n'], text=True)
packages = [dict(zip(('package','version','source_package','source_version'), line.split('\t'))) for line in raw.splitlines()]
notices = {}
for p in sorted(pathlib.Path('/usr/share/doc').glob('*/copyright')):
    if p.is_file():
        content = p.read_bytes()
        notices[str(p)] = {'sha256': hashlib.sha256(content).hexdigest(), 'text': content.decode('utf-8')}
python_license = pathlib.Path('/usr/local/lib/python3.12/LICENSE.txt').read_text()
distributions = sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())
print(json.dumps({'packages': packages, 'copyrights': notices, 'python_license': python_license,
                  'python_version': sys.version, 'python_distributions': distributions}, sort_keys=True))
"""


def inventory(image: str) -> dict:
    if "@sha256:" not in image or not image.startswith("python:3.12.14-slim-bookworm@"):
        raise ValueError("only the explicitly approved public base image is in scope")
    raw = subprocess.check_output(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--read-only",
            "--user",
            "65534:65534",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--entrypoint",
            "python",
            image,
            "-c",
            INSPECT,
        ]
    )
    result = json.loads(raw)
    details = json.loads(subprocess.check_output(["docker", "image", "inspect", image]))[0]
    result["image"] = image
    result["image_id"] = details["Id"]
    result["architecture"] = details["Architecture"]
    result["history"] = [
        json.loads(line)
        for line in subprocess.check_output(
            [
                "docker",
                "history",
                "--no-trunc",
                "--format",
                "{{json .}}",
                image,
            ],
            text=True,
        ).splitlines()
    ]
    # Relative ages vary. Build-control strings and hashes do not.
    for row in result["history"]:
        row.pop("CreatedSince", None)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(json.loads(args.seed.read_bytes())["base_image"])
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Inventoried", len(result["packages"]), "base-image packages")
