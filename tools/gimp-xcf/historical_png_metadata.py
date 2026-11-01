#!/usr/bin/env python3
"""Remove ancillary metadata/profile chunks from this original historical batch.

PNG critical chunks and their CRCs/pixel payloads are retained byte-for-byte.
GIMP's default PNG export attaches its built-in ICC and textual Exif; neither is
needed by this source storage/structure fixture, and no third-party asset ships.
"""
import argparse
from pathlib import Path
import struct
import zlib


def sanitize(path):
    original = path.read_bytes()
    if len(original) > 1_048_576 or original[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a small PNG: {path.name}")
    result = bytearray(original[:8])
    offset = 8
    critical = []
    while offset < len(original):
        if len(original) - offset < 12:
            raise ValueError("truncated chunk")
        length = struct.unpack_from(">I", original, offset)[0]
        end = offset + length + 12
        if end > len(original):
            raise ValueError("truncated payload")
        kind = original[offset + 4:offset + 8]
        payload = original[offset + 8:end - 4]
        crc = struct.unpack_from(">I", original, end - 4)[0]
        if zlib.crc32(kind + payload) != crc:
            raise ValueError("invalid CRC")
        # Critical chunks, plus transparency when present, define the pixels.
        if not (kind[0] & 32) or kind == b"tRNS":
            chunk = original[offset:end]
            result.extend(chunk)
            critical.append((kind.decode("ascii"), length))
        offset = end
    if not critical or critical[-1][0] != "IEND":
        raise ValueError("missing IEND")
    path.write_bytes(result)
    print(path.name, critical)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gimp_directory", type=Path)
    args = parser.parse_args()
    for suffix in ("u8", "float"):
        sanitize(args.gimp_directory / f"historical-2-99-18-text-path-{suffix}.png")
