"""Bounded original synthetic calculation/codec measurements at a clean revision.

Writes only synthetic exchange fixtures and aggregate timing evidence. No member
inputs or signing private keys are retained. This is an explicit maintainer command,
not an APT service persistence feature or a production performance claim.
"""

import argparse
import asyncio
import base64
import json
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app import build
from app.science.pipeline import PassportScience
from app.western import WesternRequest
from passport_codec import PROFILE, build_payload, input_digest, sign, verify


def summarize(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


async def run(artifacts: Path, count: int, revision: str) -> tuple[dict, dict]:
    startup = time.perf_counter()
    science = await asyncio.to_thread(PassportScience, artifacts)
    startup_ms = (time.perf_counter() - startup) * 1000
    key = Ed25519PrivateKey.generate()
    kid = b"synthetic-benchmark-only"
    trusted = {kid: key.public_key().public_bytes_raw()}
    samples, calc, signing, verification, sizes = [], [], [], [], []
    cases = [
        ("1900-01-01", "08:30", -33.87, 151.21),
        ("2000-01-15", "12:00", -33.87, 151.21),
        ("2000-07-15", "12:00", 59.91, 10.75),
        ("2100-12-31", "12:00", 78.22, 15.65),
    ]
    for repeat in range(count):
        for day, clock, latitude, longitude in cases:
            request = {
                "schema_version": "AstroPassportRequest.v1",
                "contract_version": "1.0.0",
                "profile": PROFILE,
                "civil": {"date": day, "time": clock, "fold": None},
                "selected_place": {
                    "schema_version": "SelectedPlaceInput.v1",
                    "provider": "synthetic",
                    "source_id": "synthetic-benchmark",
                    "display_name": "Synthetic benchmark only",
                    "latitude": latitude,
                    "longitude": longitude,
                    "attribution": None,
                    "query": "synthetic benchmark",
                    "requested_limit": 1,
                    "result_count": 1,
                    "selected_index": 0,
                },
            }
            start = time.perf_counter()
            legacy, motion = await science.calculate_portable(
                WesternRequest.model_validate_json(json.dumps(request))
            )
            calc.append((time.perf_counter() - start) * 1000)
            payload = build_payload(request, legacy.model_dump(mode="json"), motion)
            start = time.perf_counter()
            token = sign(payload, kid, key)
            signing.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            receipt = verify(token, trusted, input_digest(request))
            verification.append((time.perf_counter() - start) * 1000)
            sizes.append(float(len(token)))
            if repeat == 0:
                samples.append(
                    {"request": request, "token": token, "profile_id": receipt.profile_id}
                )
    exchange = {
        "warning": "Synthetic benchmark inputs/results and public verification key ONLY; not operational trust or member data",
        "producer_revision": revision,
        "verification_keys": {kid.decode(): base64.b64encode(trusted[kid]).decode()},
        "samples": samples,
    }
    report = {
        "source_revision": revision,
        "conditions": "local clean-source measurement; no hosted performance claim",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "synthetic_cases": len(cases),
        "repeats": count,
        "startup_ms": startup_ms,
        "calculation_ms": summarize(calc),
        "sign_ms": summarize(signing),
        "decode_verify_ms": summarize(verification),
        "encoded_ascii_bytes": summarize(sizes),
        "apt_calculations": len(calc),
        "compression": False,
    }
    return report, exchange


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic-exchange", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error("Bounded repeats1..10 required")
    if subprocess.check_output(["git", "status", "--porcelain"]):
        parser.error("Clean committed benchmark source required")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="apt-synthetic-benchmark-") as directory:
        marker = Path(directory) / "revision"
        marker.write_text(revision + "\n")
        build.REVISION_FILE = marker
        report, exchange = asyncio.run(run(args.artifacts, args.repeats, revision))
    for path, data in ((args.output, report), (args.synthetic_exchange, exchange)):
        with path.open("x") as out:
            out.write(json.dumps(data, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
