"""Hash-locked public source acquisition, verification and deterministic packaging.

No project imports, native execution, private corpus or repository access. Archives stay
opaque: never unpack untrusted source packages as a side effect of acquisition.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX_BYTES = 1024 * 1024 * 1024


def checked(entry: dict[str, object]) -> tuple[str, str, int]:
    digest, url, size = entry["sha256"], entry["url"], entry["bytes"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid content identity")
    if not isinstance(url, str):
        raise ValueError("invalid source URL")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source must be public credential-free HTTPS")
    if parsed.query or parsed.fragment or type(size) is not int or not 0 < size <= MAX_BYTES:
        raise ValueError("invalid source size or URL")
    return digest, url, size


def verify(path: Path, digest: str, size: int) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError("missing or wrong-size content")
    state = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            state.update(block)
    if state.hexdigest() != digest:
        raise ValueError("content digest mismatch")


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise ValueError("insecure source redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def acquire(entry: dict[str, object], cache: Path, offline: bool) -> Path:
    digest, url, size = checked(entry)
    path = cache / digest
    if path.exists() or path.is_symlink():
        verify(path, digest, size)
        return path
    if offline:
        raise ValueError("source absent from offline cache")
    cache.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: no replacement of existing files or symlink following.
    temporary = cache / (digest + ".part")
    opener = urllib.request.build_opener(HTTPSRedirect())
    output = temporary.open("xb")
    try:
        with output, opener.open(url, timeout=60) as response:
            count = 0
            while block := response.read(1024 * 1024):
                count += len(block)
                if count > size:
                    raise ValueError("source larger than lock")
                output.write(block)
        verify(temporary, digest, size)
        # A hard link publishes without overwriting a concurrent writer's content.
        try:
            path.hardlink_to(temporary)
        except FileExistsError:
            verify(path, digest, size)
    finally:
        # Open succeeded before try: this invocation owns precisely this partial file.
        temporary.unlink()
    return path


def pack(lock: Path, cache: Path, output: Path) -> None:
    lock_bytes = lock.read_bytes()
    data = json.loads(lock_bytes)
    if data.get("failures"):
        raise ValueError("unresolved source acquisition")
    members: dict[str, Path] = {}
    for entry in data["artifacts"]:
        digest, _, _ = checked(entry)
        members[digest] = acquire(entry, cache, offline=True)
    # Exclusive output, sorted entries, fixed metadata. No gzip timestamp variability.
    with output.open("xb") as target, tarfile.open(fileobj=target, mode="w") as archive:
        raw = lock_bytes
        info = tarfile.TarInfo("source-lock.json")
        info.size, info.mode, info.mtime = len(raw), 0o644, 0
        archive.addfile(info, io.BytesIO(raw))
        for digest, path in sorted(members.items()):
            info = tarfile.TarInfo("sha256/" + digest)
            info.size, info.mode, info.mtime = path.stat().st_size, 0o644, 0
            with path.open("rb") as source:

                class HashingReader:
                    def __init__(self):
                        self.state = hashlib.sha256()

                    def read(self, size):
                        block = source.read(size)
                        self.state.update(block)
                        return block

                reader = HashingReader()
                archive.addfile(info, reader)
                if reader.state.hexdigest() != digest:
                    raise ValueError("source changed during packaging; discard incomplete output")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "verify", "pack"])
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.lock.read_bytes())
    if data.get("failures"):
        raise ValueError("unresolved source acquisition")
    if args.action == "pack":
        if args.output is None:
            parser.error("pack requires --output")
        pack(args.lock, args.cache, args.output)
    else:
        for entry in data["artifacts"]:
            acquire(entry, args.cache, offline=args.action == "verify")
    print(f"Verified {len(data['artifacts'])} locked public source artifacts")


if __name__ == "__main__":
    main()
