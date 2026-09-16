"""Read-only RPM/ELF lineage evidence; never loads a shared library or extracts paths."""

from __future__ import annotations

import gzip
import io
import lzma
import struct

LIMIT = 1024 * 1024 * 1024


def rpm(raw: bytes) -> tuple[dict[int, str], dict[str, bytes]]:
    if len(raw) < 112 or raw[:4] != b"\xed\xab\xee\xdb":
        raise ValueError("not RPM")

    def header(offset: int) -> tuple[int, dict[int, str]]:
        if offset + 16 > len(raw) or raw[offset : offset + 3] != b"\x8e\xad\xe8":
            raise ValueError("invalid RPM header")
        count, size = struct.unpack_from(">II", raw, offset + 8)
        if count > 10000 or size > LIMIT:
            raise ValueError("oversized RPM header")
        begin = offset + 16 + 16 * count
        end = begin + size
        if end > len(raw):
            raise ValueError("truncated RPM")
        values = {}
        for i in range(count):
            tag, kind, relative, _ = struct.unpack_from(">IIII", raw, offset + 16 + i * 16)
            if relative >= size:
                raise ValueError("invalid RPM value offset")
            if kind == 6:
                values[tag] = raw[begin + relative : end].split(b"\0", 1)[0].decode()
        return end, values

    end, _ = header(96)
    end, values = header((end + 7) & ~7)
    compression = values.get(1125)
    if compression == "xz":
        decoder = lzma.LZMADecompressor()
        data = decoder.decompress(raw[end:], max_length=LIMIT + 1)
        if not decoder.eof:
            raise ValueError("oversized or incomplete RPM payload")
    elif compression == "gzip":
        with gzip.GzipFile(fileobj=io.BytesIO(raw[end:])) as stream:
            data = stream.read(LIMIT + 1)
    else:
        raise ValueError("unsupported RPM compression")
    if len(data) > LIMIT:
        raise ValueError("oversized RPM payload")
    members = {}
    cursor = 0
    while cursor + 110 <= len(data):
        if data[cursor : cursor + 6] not in (b"070701", b"070702"):
            raise ValueError("invalid cpio member")
        size = int(data[cursor + 54 : cursor + 62], 16)
        namesize = int(data[cursor + 94 : cursor + 102], 16)
        if not 0 < namesize < 4096:
            raise ValueError("invalid cpio name")
        start = cursor + 110
        name = data[start : start + namesize - 1].decode()
        start = (start + namesize + 3) & ~3
        if start + size > len(data):
            raise ValueError("truncated cpio member")
        if name == "TRAILER!!!":
            return values, members
        if name in members:
            raise ValueError("duplicate cpio member")
        members[name] = data[start : start + size]
        cursor = (start + size + 3) & ~3
    raise ValueError("missing cpio trailer")


def elf_sections(raw: bytes) -> dict[str, bytes]:
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01":
        raise ValueError("expected ELF64 little-endian")
    offset = struct.unpack_from("<Q", raw, 40)[0]
    stride, count, names_index = struct.unpack_from("<HHH", raw, 58)
    if stride != 64 or count == 0 or names_index >= count or offset + stride * count > len(raw):
        raise ValueError("invalid ELF section table")
    headers = [struct.unpack_from("<IIQQQQIIQQ", raw, offset + stride * i) for i in range(count)]
    names = headers[names_index]
    if names[4] + names[5] > len(raw):
        raise ValueError("truncated ELF string table")
    strings = raw[names[4] : names[4] + names[5]]
    result = {}
    for item in headers:
        if item[1] == 8:  # SHT_NOBITS has no stored payload.
            continue
        if item[0] >= len(strings):
            raise ValueError("invalid ELF section name")
        name = strings[item[0] :].split(b"\0", 1)[0].decode()
        if item[4] + item[5] > len(raw):
            raise ValueError("truncated ELF section")
        if name in result:
            raise ValueError("duplicate ELF section name")
        result[name] = raw[item[4] : item[4] + item[5]]
    return result
