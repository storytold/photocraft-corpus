# `jxl/`: JPEG XL oracles

12 JPEG XL files of 12×9 pixels encoded by **libjxl's `cjxl` 0.7.0** from procedural source
images, plus the source JPEG two of them were made from. PhotoCraft's JPEG XL decoder
(`photocraft-codecs`, cargo feature `jxl`) checks the lossless files sample for sample against
the formulas the generator drew with, the lossy one by PSNR, and the metadata, orientation,
JPEG-reconstruction and animation files against what was encoded.

Every file is written from scratch by [`tools/jxl-fixtures/jxl_fixtures.py`](../tools/jxl-fixtures/jxl_fixtures.py),
which draws the source images itself (a minimal PNG writer, a PFM, a Pillow JPEG and GIF) and runs
`cjxl` on them. Nothing is read from disk, no third-party image, profile or asset is used, and the
only text in any metadata is "PhotoCraft JPEG XL fixture" (plus Exif Orientation 6). The files are
licensed like the rest of this repository, MIT OR Apache-2.0; `cjxl` is the authoring tool only
and none of its code is included.

## What each file covers

| File | Lossless | Lossy | Alpha | 16-bit | Float | Animation | Colour / metadata | Container |
|---|:-:|:-:|:-:|:-:|:-:|:-:|---|:-:|
| `rgb8-lossless.jxl` | ✓ | | | | | | sRGB | bare |
| `rgba8-lossless.jxl` | ✓ | | ✓ straight, 0→255 gradient | | | | sRGB | bare |
| `gray8-lossless.jxl` | ✓ | | | | | | gray | bare |
| `graya16-lossless.jxl` | ✓ | | ✓ (stored 8-bit by cjxl 0.7: multiples of 257) | ✓ | | | gray | bare |
| `rgb16-lossless.jxl` | ✓ | | | ✓ | | | sRGB | bare |
| `rgb10-lossless.jxl` | ✓ | | | 10-bit samples, decode to 16 | | | sRGB | bare |
| `rgb-f32-lossless.jxl` | ✓ | | | | ✓ values above 1.0 | | sRGB (as cjxl tags a PFM) | bare |
| `rgb8-lossy.jxl` | | ✓ VarDCT, distance 1 (XYB) | | | | | sRGB | bare |
| `rgb8-p3.jxl` | ✓ | | | | | | Display P3 as an **enum colour encoding**, no ICC | bare |
| `exif-xmp-orient6.jxl` | ✓ (pixels re-encoded) | | | | | | Exif box (Orientation 6, ImageDescription) + XMP box; codestream orientation 6 | ✓ |
| `jpeg-recon.jxl` | ✓ (JPEG transcoded) | | | | | | JPEG reconstruction data | ✓ |
| `animated.jxl` | ✓ | | ✓ opaque (GIF input) | | | ✓ 3 frames, 100 ms each, looping | sRGB | bare |
| `exif-xmp-orient6.src.jpg` | source JPEG of the two files above (Pillow, quality 95, Exif APP1 + XMP APP1) | | | | | | | |

Not covered by this set: an embedded **ICC profile** (the colour-managed case is the enum
encoding of `rgb8-p3`), **progressive** decoding, CMYK, spot channels and layers. Add a case to
the generator when the decoder gains a test for one of them.

## How each file was made

All files are 12×9. `cjxl` is invoked as `cjxl <source> <output> --quiet <flags>` with the
flags below; `-d 0` is Modular lossless, `-e 3` is the effort, and the rest is per file.

| File | Source (drawn by the script) | `cjxl` flags |
|---|---|---|
| `rgb8-lossless.jxl` | 8-bit RGB PNG, `pattern()` | `-d 0 -e 3` |
| `rgba8-lossless.jxl` | 8-bit RGBA PNG, `pattern()` + `alpha()` | `-d 0 -e 3` |
| `gray8-lossless.jxl` | 8-bit gray PNG | `-d 0 -e 3` |
| `graya16-lossless.jxl` | 16-bit gray+alpha PNG | `-d 0 -e 3` |
| `rgb16-lossless.jxl` | 16-bit RGB PNG | `-d 0 -e 3` |
| `rgb10-lossless.jxl` | 16-bit RGB PNG holding 10-bit values scaled by 65535/1023 | `-d 0 -e 3 --override_bitdepth=10` |
| `rgb-f32-lossless.jxl` | 32-bit float PFM, `float_sample()` | `-d 0 -e 3` |
| `rgb8-lossy.jxl` | 8-bit RGB PNG, `smooth()` | `-d 1 -e 3` |
| `rgb8-p3.jxl` | the `rgb8-lossless` PNG | `-d 0 -e 3 -x color_space=RGB_D65_DCI_Rel_SRG` |
| `exif-xmp-orient6.jxl` | the source JPEG | `-d 0 -e 3 -j 0 --container=0`, then the script wraps the bare codestream in an ISO/IEC 18181-2 container with its own `Exif` and `xml ` boxes (cjxl 0.7 drops the JPEG's metadata when it re-encodes pixels) |
| `jpeg-recon.jxl` | the source JPEG | `-j 1` |
| `animated.jxl` | 3-frame GIF, Pillow | `-d 0 -e 3` |
| `exif-xmp-orient6.src.jpg` | Pillow JPEG, quality 95, with an Exif APP1 (Orientation 6, ImageDescription) and an XMP APP1 written by the script | not encoded by cjxl |

Regenerate the whole set with `python3 tools/jxl-fixtures/jxl_fixtures.py` (needs `cjxl` 0.7 or
newer on `PATH` and Pillow). cjxl's output is deterministic for a given version; another libjxl
may change bytes, so regenerate only when the set itself changes, then follow the
[pinning workflow](../README.md#pinning-workflow). The pixel formulas are mirrored by
`pattern()` in PhotoCraft's `crates/codecs/tests/jxl.rs`; change both together.

## Sizes and checksums

7275 bytes in all. The same hashes are in the repository's [`SHA256SUMS`](../SHA256SUMS)
and in PhotoCraft's `xtask/jxl-corpus.sha256`.

| File | Bytes | SHA-256 |
|---|--:|---|
| `rgb8-lossless.jxl` | 391 | `201467b584e3db669c724b942507936b82a8efb8b72953d0323942e30713174b` |
| `rgba8-lossless.jxl` | 453 | `ab5638f2e45d6c78fc6542bc6b70472bf959630f84d6985f89a1d43c59c7d81b` |
| `gray8-lossless.jxl` | 151 | `b4fd5502866c31ed09a6914ea2c4ffb329bb5596f03428f974e4c3edebcf9466` |
| `graya16-lossless.jxl` | 214 | `8177b04e9d071d3402fe2467772e45dcf73d5f3bbafc1dd2379a0f325260a1db` |
| `rgb16-lossless.jxl` | 196 | `d89cb267a9775ce6ef4cacc9b2b6354f0a0054fe84703d6f18e88f7e9b599950` |
| `rgb10-lossless.jxl` | 489 | `2d95e32b15768d170c90ab7e4f81e4b4c92c88776705cb4ea48e0af17c23d398` |
| `rgb-f32-lossless.jxl` | 911 | `6ea7666e8d3d0a142655c612213ae02173fa312e9c84983865301c76ffd59037` |
| `rgb8-lossy.jxl` | 146 | `ca289851a1c4adb76be2340ddf03f1ff166df5cb441c3599a6097a72605e3fb3` |
| `rgb8-p3.jxl` | 391 | `0bf9cc59503b265caa1e386eef2a76a29a9f27739180f0c2c82acaf0e12fbb8b` |
| `exif-xmp-orient6.jxl` | 803 | `c773ece848d968910aaeaa30da6340a7beaa73a296f6c1095d58f493629b4bf1` |
| `jpeg-recon.jxl` | 1166 | `e74c2a2b3c9b243c1ec95de6b6cc17eeee116e5368e50e4709baf68e2d6a7714` |
| `animated.jxl` | 697 | `05a1b5a6144deb5d90bd2ab211eec19a9e1176a50cb08c2a44f3f5e9b9a2bbfd` |
| `exif-xmp-orient6.src.jpg` | 1267 | `e594e80b6ea3034d273f5403ae3fd42b9949d0c5c34b3055e55ea94a994efdee` |
