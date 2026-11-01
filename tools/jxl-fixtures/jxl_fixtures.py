#!/usr/bin/env python3
"""Writes `jxl/` with libjxl's `cjxl` (an independent encoder), from procedural images that
PhotoCraft's `crates/codecs/tests/jxl.rs` regenerates, so lossless files are compared sample for
sample and lossy ones by PSNR:

    rgb8-lossless.jxl        12x9 RGB 8-bit, bare codestream, Modular lossless
    rgba8-lossless.jxl       RGBA 8-bit, straight alpha with fully transparent and opaque pixels
    gray8-lossless.jxl       Gray 8-bit
    graya16-lossless.jxl     Gray 16-bit + alpha (stored 8-bit by cjxl 0.7: alpha values are multiples of 257)
    rgb16-lossless.jxl       RGB 16-bit
    rgb10-lossless.jxl       RGB 10-bit samples (decodes to 16-bit)
    rgb-f32-lossless.jxl     RGB 32-bit float with values above 1 (from PFM)
    rgb8-lossy.jxl           RGB 8-bit VarDCT, distance 1 (XYB)
    rgb8-p3.jxl              RGB 8-bit lossless tagged Display P3 (enum colour encoding, no ICC)
    exif-xmp-orient6.jxl     JPEG input with EXIF Orientation 6: the codestream carries orientation 6,
                             re-encoded losslessly, wrapped by this script in a container with the EXIF
                             (Orientation 6, ImageDescription) and XMP boxes a camera file would have
    jpeg-recon.jxl           the same JPEG transcoded losslessly (JPEG reconstruction data)
    animated.jxl             3-frame GIF animation

Everything is drawn from scratch here (procedural samples, a synthetic Exif block and XMP packet
whose only text is "PhotoCraft JPEG XL fixture", a three-frame procedural GIF); nothing is read
from disk. The source JPEG of the two JPEG-derived files is kept next to them.

Run with:  python3 tools/jxl-fixtures/jxl_fixtures.py     (needs cjxl 0.7+ on PATH and Pillow)
The pixel formulas are mirrored by `pattern()` in PhotoCraft's crates/codecs/tests/jxl.rs; change both.
"""

import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

from PIL import Image

# The repository root is two levels up from this file.
OUT = Path(__file__).resolve().parent.parent.parent / "jxl"
W, H = 12, 9


def pattern(x, y, c, maxval):
    """Integer sample: varied values, every channel different (mirrored in jxl.rs)."""
    return (x * 31 + y * 17 + c * 101 + 7) * 13 % (maxval + 1)


def alpha(x, y, maxval):
    """Alpha gradient from fully transparent (top-left) to fully opaque (bottom-right)."""
    return min(maxval, (x + y) * maxval // (W + H - 4))


def smooth(x, y, c):
    """Smooth 8-bit content for the lossy fixture (mirrored in jxl.rs)."""
    return [x * 255 // (W - 1), y * 255 // (H - 1), 128][c]


def float_sample(x, y, c):
    """Exact binary fractions, some above 1.0 (mirrored in jxl.rs)."""
    return (x * 3 + y * 5 + c * 7) / 64.0


def png(path, w, h, channels, bits, sample, extra_chunks=()):
    """A minimal PNG writer: `sample(x, y, c)` gives each integer sample."""
    color_type = {1: 0, 2: 4, 3: 2, 4: 6}[channels]
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            for c in range(channels):
                v = sample(x, y, c)
                raw += struct.pack(">H", v) if bits == 16 else bytes([v])

    def chunk(ty, data):
        return struct.pack(">I", len(data)) + ty + data + struct.pack(">I", zlib.crc32(ty + data) & 0xFFFFFFFF)

    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bits, color_type, 0, 0, 0))
    for ty, data in extra_chunks:
        out += chunk(ty, data)
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    path.write_bytes(out)


def pfm(path, w, h):
    rows = []
    for y in range(h - 1, -1, -1):  # PFM is bottom-up
        for x in range(w):
            for c in range(3):
                rows.append(float_sample(x, y, c))
    path.write_bytes(f"PF\n{w} {h}\n-1.0\n".encode() + struct.pack(f"<{len(rows)}f", *rows))


def exif_tiff(orientation):
    """A TIFF-structured EXIF block: Orientation and ImageDescription."""
    desc = b"PhotoCraft JPEG XL fixture\0"
    entries = [
        struct.pack(">HHII", 0x010E, 2, len(desc), 8 + 2 + 12 * 2 + 4),
        struct.pack(">HHIHH", 0x0112, 3, 1, orientation, 0),
    ]
    return b"MM\0*" + struct.pack(">I", 8) + struct.pack(">H", len(entries)) + b"".join(entries) + struct.pack(">I", 0) + desc


XMP = (
    '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?><x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:tiff="http://ns.adobe.com/tiff/1.0/" tiff:Orientation="6">'
    "<dc:title><rdf:Alt><rdf:li xml:lang=\"x-default\">PhotoCraft JPEG XL fixture</rdf:li></rdf:Alt></dc:title>"
    '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
)


def jpeg_with_metadata(path):
    """A smooth JPEG with an EXIF APP1 (Orientation 6) and an XMP APP1 segment."""
    img = Image.new("RGB", (W, H))
    img.putdata([tuple(smooth(x, y, c) for c in range(3)) for y in range(H) for x in range(W)])
    # Saved to its final path, then rewritten with XMP below: a NamedTemporaryFile cannot be
    # reopened by name on Windows while it is still open.
    img.save(path, "JPEG", quality=95, exif=b"Exif\0\0" + exif_tiff(6))
    data = Path(path).read_bytes()
    xmp = b"http://ns.adobe.com/xap/1.0/\0" + XMP.encode("utf-8")
    app1 = b"\xff\xe1" + struct.pack(">H", len(xmp) + 2) + xmp
    # Right after SOI; Pillow's JFIF and EXIF segments follow.
    assert data[:2] == b"\xff\xd8"
    path.write_bytes(data[:2] + app1 + data[2:])


def codestream_of(data):
    """The bare codestream: `data` itself, or the jxlc / jxlp payloads of a container (cjxl 0.7
    writes a container for JPEG input whatever --container says)."""
    if data[:2] == b"\xff\x0a":
        return data
    assert data[:12] == b"\0\0\0\x0cJXL \r\n\x87\n", "not a JPEG XL file"
    out = b""
    pos = 0
    while pos < len(data):
        size, ty = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + size] if size else data[pos + 8:]
        if ty == b"jxlc":
            out += body
        elif ty == b"jxlp":
            out += body[4:]  # after the partial-codestream index
        pos += size or len(data)
    assert out[:2] == b"\xff\x0a"
    return out


def container(path, codestream, exif, xmp):
    """Wraps a bare codestream in the ISO/IEC 18181-2 container with Exif and XML boxes
    (cjxl 0.7 drops the JPEG's metadata when it re-encodes pixels, so the boxes are written here)."""

    def box(ty, data):
        return struct.pack(">I", 8 + len(data)) + ty + data

    out = box(b"JXL ", b"\r\n\x87\n") + box(b"ftyp", b"jxl \0\0\0\0jxl ")
    out += box(b"Exif", struct.pack(">I", 0) + exif) + box(b"xml ", xmp) + box(b"jxlc", codestream)
    path.write_bytes(out)


def gif_animation(path):
    frames = []
    for i in range(3):
        img = Image.new("RGB", (W, H))
        img.putdata([((x * 20 + i * 80) % 256, (y * 25) % 256, i * 100) for y in range(H) for x in range(W)])
        frames.append(img)
    frames[0].save(path, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)


def cjxl(src, dst, *args):
    subprocess.run(["cjxl", str(src), str(dst), "--quiet", *args], check=True)
    print(f"{dst.name}: {dst.stat().st_size} bytes")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        png(d / "rgb8.png", W, H, 3, 8, lambda x, y, c: pattern(x, y, c, 255))
        cjxl(d / "rgb8.png", OUT / "rgb8-lossless.jxl", "-d", "0", "-e", "3")
        png(d / "rgba8.png", W, H, 4, 8, lambda x, y, c: alpha(x, y, 255) if c == 3 else pattern(x, y, c, 255))
        cjxl(d / "rgba8.png", OUT / "rgba8-lossless.jxl", "-d", "0", "-e", "3")
        png(d / "gray8.png", W, H, 1, 8, lambda x, y, c: pattern(x, y, c, 255))
        cjxl(d / "gray8.png", OUT / "gray8-lossless.jxl", "-d", "0", "-e", "3")
        png(d / "graya16.png", W, H, 2, 16, lambda x, y, c: alpha(x, y, 255) * 257 if c == 1 else pattern(x, y, c, 65535))
        cjxl(d / "graya16.png", OUT / "graya16-lossless.jxl", "-d", "0", "-e", "3")
        png(d / "rgb16.png", W, H, 3, 16, lambda x, y, c: pattern(x, y, c, 65535))
        cjxl(d / "rgb16.png", OUT / "rgb16-lossless.jxl", "-d", "0", "-e", "3")
        # 10-bit samples: cjxl reads the 16-bit PNG as fractions of 65535 and requantizes them to
        # 10 bits, so the PNG holds each 10-bit value scaled up (the exact inverse of that step).
        png(d / "rgb10.png", W, H, 3, 16, lambda x, y, c: round(pattern(x, y, c, 1023) * 65535 / 1023))
        cjxl(d / "rgb10.png", OUT / "rgb10-lossless.jxl", "-d", "0", "-e", "3", "--override_bitdepth=10")
        pfm(d / "rgb.pfm", W, H)
        cjxl(d / "rgb.pfm", OUT / "rgb-f32-lossless.jxl", "-d", "0", "-e", "3")
        png(d / "smooth.png", W, H, 3, 8, smooth)
        cjxl(d / "smooth.png", OUT / "rgb8-lossy.jxl", "-d", "1", "-e", "3")
        cjxl(d / "rgb8.png", OUT / "rgb8-p3.jxl", "-d", "0", "-e", "3", "-x", "color_space=RGB_D65_DCI_Rel_SRG")
        jpeg_with_metadata(d / "meta.jpg")
        cjxl(d / "meta.jpg", d / "orient6.jxl", "-d", "0", "-e", "3", "-j", "0", "--container=0")
        container(OUT / "exif-xmp-orient6.jxl", codestream_of((d / "orient6.jxl").read_bytes()), exif_tiff(6), XMP.encode("utf-8"))
        cjxl(d / "meta.jpg", OUT / "jpeg-recon.jxl", "-j", "1")
        gif_animation(d / "anim.gif")
        cjxl(d / "anim.gif", OUT / "animated.jxl", "-d", "0", "-e", "3")
        (d / "meta.jpg").replace(OUT / "exif-xmp-orient6.src.jpg")
        print("source JPEG kept next to the fixtures for the reconstruction test")


if __name__ == "__main__":
    sys.exit(main())
