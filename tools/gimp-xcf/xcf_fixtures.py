#!/usr/bin/env python3
"""Writes `gimp/` with GIMP itself (an independent XCF writer): small procedural images saved as
XCF, each next to GIMP's own merged rendering of the visible layers as a PNG, so PhotoCraft's
`crates/io/tests/xcf.rs` checks both the layer data it reads and the composite it renders against
GIMP:

    layers-8bit.xcf     three RGB layers: offsets (one off-canvas), opacity, Multiply and Screen
                        modes, a hidden layer, lock alpha, a colour tag, resolution and guides
    groups.xcf          a group with two children and a nested group, one group pass-through,
                        group opacity
    mask.xcf            a layer mask painted with a gradient, one applied and one disabled
    gray16.xcf          a 16-bit grayscale image with two layers
    float-linear.xcf    a 32-bit float linear-light RGB image (precision 600)
    indexed.xcf         a 16-colour indexed image with transparency
    text.xcf            a text layer (opens as pixels)
    channel.xcf         an extra channel and a saved selection
    legacy-modes.xcf    Addition, Subtract, Divide, Dodge, Burn, Grain Merge, HSV Hue/Value and
                        LCH Color modes
    precision-*.xcf    integer/half/float/double boundary samples, including finite HDR and
                        double-to-float rounding/underflow inputs; PNGs are clipped previews

Each file with blend modes or transparency also comes as `<name>-perceptual.xcf`, with every
layer set to blend and composite in gamma-encoded RGB (GIMP's default is linear light for most
modes), which is the space PhotoCraft composes in; the tests compare our composite tightly to
GIMP's PNG for those and measure the known gap on the defaults.

Everything is drawn from scratch here (procedural samples, paths, selections and text whose
fonts are referenced by name only). Only our own newly generated files are read back for
verification or linking. GIMP adds its own Exif (dimensions, resolution, a thumbnail in PNGs).
The assigned-profile cases embed original ICC data generated here; no bundled profile is used.

Run `tools/gimp-xcf/generate.sh` (GIMP 3.2 headless), or from the repository root:

    flatpak run --command=gimp org.gimp.GIMP -i -n --batch-interpreter=python-fu-eval \
        -b "exec(open('tools/gimp-xcf/xcf_fixtures.py').read())" -b 'quit()'

The patterns are mirrored by `pattern()` in PhotoCraft's crates/io/tests/xcf.rs; change both.
Set PHOTOCRAFT_XCF_CASES=precision_variants to generate only the small precision batch.
"""

import os
import struct
import bz2
import gzip
import lzma

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gegl, Gimp, Gio  # noqa: E402

# The repository root: two levels up from this file, or the working directory when the script is
# exec'd inside GIMP (generate.sh runs it from the root).
HERE = (os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(globals().get("__file__", "")) == "xcf_fixtures.py" else None)
ROOT = os.path.normpath(os.path.join(HERE, "..", "..")) if HERE else os.getcwd()
OUT = os.path.join(ROOT, "gimp")
os.makedirs(OUT, exist_ok=True)
W, H = 40, 30


def pattern(x, y, c, maxval):
    """Integer sample, every channel different (mirrored in xcf.rs)."""
    return (x * 31 + y * 17 + c * 101 + 7) * 13 % (maxval + 1)


def alpha(x, y, w, h, maxval):
    return min(maxval, (x + y) * maxval // max(1, w + h - 4))


def fill(drawable, w, h, channels, bits, sample, fmt=None):
    """Writes procedural samples into a drawable's buffer."""
    data = bytearray()
    for y in range(h):
        for x in range(w):
            for c in range(channels):
                v = sample(x, y, c)
                if bits == 8:
                    data.append(v)
                elif bits == 16:
                    data += struct.pack("<H", v)
                else:
                    data += struct.pack("<f", v)
    buf = drawable.get_buffer()
    if fmt is None:
        fmt = {(1, 8): "Y' u8", (2, 8): "Y'A u8", (3, 8): "R'G'B' u8", (4, 8): "R'G'B'A u8", (1, 16): "Y' u16", (2, 16): "Y'A u16", (4, 16): "R'G'B'A u16", (4, 32): "RGBA float", (3, 32): "RGB float"}[(channels, bits)]
    buf.set(Gegl.Rectangle.new(0, 0, w, h), fmt, bytes(data))
    buf.flush()
    drawable.update(0, 0, w, h)


def all_layers(parent):
    """Every layer of an image or group, depth first."""
    out = []
    for layer in parent.get_layers() if isinstance(parent, Gimp.Image) else parent.get_children():
        out.append(layer)
        if isinstance(layer, Gimp.GroupLayer):
            out += all_layers(layer)
    return out


def save(img, name, perceptual_variant=True):
    """Writes `name.xcf` as GIMP composes it by default (linear light for most modes), and
    `name-perceptual.xcf` with every layer blending and compositing in gamma-encoded RGB, which
    is how Photoshop and PhotoCraft compose; each with GIMP's merged rendering as a PNG."""
    save_one(img, name)
    if perceptual_variant:
        for layer in all_layers(img):
            layer.set_blend_space(Gimp.LayerColorSpace.RGB_PERCEPTUAL)
            layer.set_composite_space(Gimp.LayerColorSpace.RGB_PERCEPTUAL)
        save_one(img, name + "-perceptual")


def save_one(img, name):
    path = os.path.join(OUT, name)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(path + ".xcf"), None)
    # GIMP's own rendering of the visible layers, as the oracle for our composite.
    merged = img.duplicate()
    merged.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, merged, Gio.File.new_for_path(path + ".png"), None)
    merged.delete()
    print("wrote", name, os.path.getsize(path + ".xcf"), "bytes")


def rgba_layer(img, name, w, h, seed, mode=Gimp.LayerMode.NORMAL, opacity=100.0):
    layer = Gimp.Layer.new(img, name, w, h, Gimp.ImageType.RGBA_IMAGE, opacity, mode)
    img.insert_layer(layer, None, 0)
    fill(layer, w, h, 4, 8, lambda x, y, c: alpha(x, y, w, h, 255) if c == 3 else pattern(x + seed, y, c, 255))
    return layer


def layers_8bit():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    img.set_resolution(300.0, 300.0)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W, H, 3, 8, lambda x, y, c: pattern(x, y, c, 255))
    a = rgba_layer(img, "Multiply 60%", 20, 16, 3, Gimp.LayerMode.MULTIPLY, 60.0)
    a.set_offsets(5, 4)
    a.set_lock_alpha(True)
    a.set_color_tag(Gimp.ColorTag.GREEN)
    b = rgba_layer(img, "Screen off-canvas", 24, 12, 7, Gimp.LayerMode.SCREEN, 100.0)
    b.set_offsets(-8, 20)
    hidden = rgba_layer(img, "Hidden", 10, 10, 11)
    hidden.set_offsets(28, 2)
    hidden.set_visible(False)
    img.add_hguide(10)
    img.add_vguide(25)
    save(img, "layers-8bit")


def groups():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    bg = rgba_layer(img, "Background", W, H, 0)
    group = Gimp.GroupLayer.new(img, "Group")
    img.insert_layer(group, None, 0)
    group.set_opacity(70.0)
    c1 = rgba_layer(img, "Child Multiply", 20, 20, 2, Gimp.LayerMode.MULTIPLY)
    img.reorder_item(c1, group, 0)
    c1.set_offsets(3, 3)
    nested = Gimp.GroupLayer.new(img, "Nested pass-through")
    img.insert_layer(nested, group, 0)
    nested.set_mode(Gimp.LayerMode.PASS_THROUGH)
    c2 = rgba_layer(img, "Nested child Screen", 16, 12, 5, Gimp.LayerMode.SCREEN)
    img.reorder_item(c2, nested, 0)
    c2.set_offsets(18, 10)
    top = rgba_layer(img, "Top", 12, 8, 9)
    top.set_offsets(26, 20)
    save(img, "groups")


def mask():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W, H, 3, 8, lambda x, y, c: [200, 200, 200][c])
    masked = rgba_layer(img, "Masked", 30, 20, 4)
    masked.set_offsets(5, 5)
    m = masked.create_mask(Gimp.AddMaskType.WHITE)
    masked.add_mask(m)
    fill(m, 30, 20, 1, 8, lambda x, y, c: x * 255 // 29)
    disabled = rgba_layer(img, "Mask disabled", 20, 10, 6)
    disabled.set_offsets(15, 18)
    m2 = disabled.create_mask(Gimp.AddMaskType.BLACK)
    disabled.add_mask(m2)
    disabled.set_apply_mask(False)
    save(img, "mask")


def gray16():
    img = Gimp.Image.new_with_precision(W, H, Gimp.ImageBaseType.GRAY, Gimp.Precision.U16_NON_LINEAR)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.GRAY_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W, H, 1, 16, lambda x, y, c: pattern(x, y, c, 65535))
    top = Gimp.Layer.new(img, "Gray alpha", 20, 15, Gimp.ImageType.GRAYA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(top, None, 0)
    fill(top, 20, 15, 2, 16, lambda x, y, c: alpha(x, y, 20, 15, 65535) if c == 1 else pattern(x + 9, y, 0, 65535))
    top.set_offsets(10, 8)
    save(img, "gray16", perceptual_variant=False)


def float_linear():
    img = Gimp.Image.new_with_precision(W, H, Gimp.ImageBaseType.RGB, Gimp.Precision.FLOAT_LINEAR)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W, H, 3, 32, lambda x, y, c: (x * 3 + y * 5 + c * 7) / 64.0)
    top = Gimp.Layer.new(img, "Float alpha", 16, 16, Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(top, None, 0)
    fill(top, 16, 16, 4, 32, lambda x, y, c: (x + y) / 30.0 if c == 3 else (x * 2 + y * 3 + c * 5) / 64.0)
    top.set_offsets(12, 7)
    save(img, "float-linear", perceptual_variant=False)


def indexed():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    bg = rgba_layer(img, "Background", W, H, 0)
    top = rgba_layer(img, "Top", 20, 20, 5)
    top.set_offsets(10, 5)
    img.convert_indexed(Gimp.ConvertDitherType.NONE, Gimp.ConvertPaletteType.GENERATE, 16, False, False, "")
    save(img, "indexed", perceptual_variant=False)


def text():
    img = Gimp.Image.new(W * 4, H * 2, Gimp.ImageBaseType.RGB)
    bg = Gimp.Layer.new(img, "Background", W * 4, H * 2, Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W * 4, H * 2, 3, 8, lambda x, y, c: 255)
    font = Gimp.context_get_font()
    tl = Gimp.TextLayer.new(img, "XCF", font, 24.0, Gimp.Unit.pixel())
    img.insert_layer(tl, None, 0)
    tl.set_offsets(10, 10)
    save(img, "text")


def channel():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    bg = rgba_layer(img, "Background", W, H, 0)
    color = Gegl.Color.new("red")
    ch = Gimp.Channel.new(img, "Alpha 1", W, H, 50.0, color)
    img.insert_channel(ch, None, 0)
    fill(ch, W, H, 1, 8, lambda x, y, c: y * 255 // (H - 1))
    img.select_rectangle(Gimp.ChannelOps.REPLACE, 4, 6, 20, 12)
    save(img, "channel", perceptual_variant=False)


def legacy_modes():
    img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)
    bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    img.insert_layer(bg, None, 0)
    fill(bg, W, H, 3, 8, lambda x, y, c: pattern(x, y, c, 255))
    modes = [
        ("Addition", Gimp.LayerMode.ADDITION),
        ("Subtract", Gimp.LayerMode.SUBTRACT),
        ("Divide", Gimp.LayerMode.DIVIDE),
        ("Dodge", Gimp.LayerMode.DODGE),
        ("Burn", Gimp.LayerMode.BURN),
        ("Grain merge", Gimp.LayerMode.GRAIN_MERGE),
        ("HSV Hue", Gimp.LayerMode.HSV_HUE),
        ("HSV Value", Gimp.LayerMode.HSV_VALUE),
        ("LCH Color", Gimp.LayerMode.LCH_COLOR),
        ("Hard light", Gimp.LayerMode.HARDLIGHT),
        ("Exclusion", Gimp.LayerMode.EXCLUSION),
        ("Linear light", Gimp.LayerMode.LINEAR_LIGHT),
    ]
    for i, (name, mode) in enumerate(modes):
        layer = rgba_layer(img, name, 8, 8, i * 3, mode)
        layer.set_offsets((i % 5) * 8, (i // 5) * 10)
    save(img, "legacy-modes")


def precision_variants():
    """Original source samples; no profile/preset files or image inputs are read.

    The unsigned integers are normalized samples. Half/float/double colors may be outside
    [0, 1], while alpha stays in [0, 1]. Double midpoint ties are around 1 with f32 ULP 2^-23;
    2^-150 is halfway between zero and the smallest f32 subnormal. Preview PNGs deliberately
    cannot serve as HDR or native-compositing oracles.
    """
    cases = [
        ("precision-u32-nonlinear", Gimp.Precision.U32_NON_LINEAR, Gimp.ImageBaseType.RGB,
         17, 5, "R'G'B'A u32", "I", [0, 1, 2, (1 << 24) - 1, (1 << 24) + 1,
                                   (1 << 31) - 1, 1 << 31, (1 << 32) - 2, (1 << 32) - 1]),
        ("precision-half-hdr", Gimp.Precision.HALF_NON_LINEAR, Gimp.ImageBaseType.RGB,
         9, 7, "R'G'B'A half", "e", [0.0, -0.0, 2.0 ** -24, 2.0 ** -14, -0.25, 0.5, 1.0, 1.5, 65504.0]),
        ("precision-float-hdr", Gimp.Precision.FLOAT_NON_LINEAR, Gimp.ImageBaseType.RGB,
         11, 3, "R'G'B'A float", "f", [0.0, -0.0, 2.0 ** -149, 2.0 ** -126, -0.125, 0.25, 1.0, 2.0, 4.0]),
        ("precision-double-gray-boundaries", Gimp.Precision.DOUBLE_NON_LINEAR, Gimp.ImageBaseType.GRAY,
         13, 5, "Y'A double", "d", [0.0, -0.0, 2.0 ** -1074, 2.0 ** -150, 2.0 ** -149,
                                   1.0 + 2.0 ** -24, 1.0 + 3.0 * 2.0 ** -24, 1.5, -0.25, 2.0]),
    ]
    for name, precision, mode, w, h, fmt, code, colors in cases:
        img = Gimp.Image.new_with_precision(w + 4, h + 3, mode, precision)
        try:
            img.set_resolution(96.0, 96.0)
            channels = 2 if mode == Gimp.ImageBaseType.GRAY else 4
            layer_type = Gimp.ImageType.GRAYA_IMAGE if channels == 2 else Gimp.ImageType.RGBA_IMAGE
            layer = Gimp.Layer.new(img, "Stored precision samples", w, h, layer_type, 100.0, Gimp.LayerMode.NORMAL)
            img.insert_layer(layer, None, 0)
            layer.set_offsets(-2, 1)
            alphas = [0, 1 << 30, 1 << 31, (1 << 32) - 1] if code == "I" else [0.0, 0.25, 0.5, 1.0]
            values = []
            for y in range(h):
                for x in range(w):
                    values.extend(colors[(x + y * 3 + c) % len(colors)] for c in range(channels - 1))
                    values.append(alphas[(x + y) % len(alphas)])
            data = struct.pack("=" + code * len(values), *values)
            rect = Gegl.Rectangle.new(0, 0, w, h)
            buf = layer.get_buffer()
            buf.set(rect, fmt, data)
            buf.flush()
            if bytes(buf.get(rect, 1.0, fmt, Gegl.AbyssPolicy.NONE)) != data:
                raise RuntimeError(name + ": GIMP buffer did not retain the requested source bits")
            layer.update(0, 0, w, h)
            save(img, name, perceptual_variant=False)
            reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(os.path.join(OUT, name + ".xcf")))
            try:
                if reopened.get_precision() != precision:
                    raise RuntimeError(name + ": saved precision changed")
                stored = reopened.get_layers()[0].get_buffer().get(rect, 1.0, fmt, Gegl.AbyssPolicy.NONE)
                if bytes(stored) != data:
                    raise RuntimeError(name + ": saved/reopened source samples changed")
                metadata = reopened.get_metadata()
                if metadata:
                    tags = list(metadata.get_exif_tags() or []) + list(metadata.get_xmp_tags() or []) + list(metadata.get_iptc_tags() or [])
                    for tag in tags:
                        value = metadata.try_get_tag_string(tag) or ""
                        if tag.lower() in {"exif.image.artist", "xmp.dc.creator", "iptc.application2.byline"} and value:
                            raise RuntimeError(name + ": unexpected creator metadata")
                        if any(marker in value.lower() for marker in ("c:/users/", "c:\\users\\", "/users/", "/home/")):
                            raise RuntimeError(name + ": unexpected source path metadata")
            finally:
                reopened.delete()
        finally:
            img.delete()
    # Independent standard-library encoders wrap the unchanged GIMP-authored integer source.
    # No original filename or timestamp is put in the gzip header. The XZ dictionary is 8 MiB.
    path = os.path.join(OUT, "precision-u32-nonlinear.xcf")
    with open(path, "rb") as source:
        raw = source.read()
    for suffix, data in [("gz", gzip.compress(raw, mtime=0)), ("bz2", bz2.compress(raw)),
                         ("xz", lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6))]:
        with open(path + "." + suffix, "wb") as output:
            output.write(data)
        print("wrote", "precision-u32-nonlinear.xcf." + suffix, len(data), "bytes")


def native_text_paths():
    """Original text and cubic geometry; fonts are references, never copied files."""
    img = Gimp.Image.new(160, 100, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(img, "Procedural background", 160, 100, 0)
        layer = Gimp.TextLayer.new(img, "héλlo\n漢字", Gimp.context_get_font(), 24.0, Gimp.Unit.pixel())
        img.insert_layer(layer, None, 0)
        layer.set_color(Gegl.Color.new("rgb(0.2,0.4,0.8)"))
        layer.resize(120.0, 60.0)
        layer.set_markup('<markup>hé<span foreground="#c04020" size="18432" weight="bold">λlo</span>\n漢字</markup>')
        layer.set_offsets(-3, 7)
        save(img, "text-unicode-fixed-markup", perceptual_variant=False)
        if not layer.edit_fill(Gimp.FillType.WHITE):
            raise RuntimeError("could not apply destructive text edit")
        fill(layer, layer.get_width(), layer.get_height(), 4, 8,
             lambda x, y, c: 255 if c == 3 else (x * 17 + y * 5 + c * 61) % 256)
        save(img, "text-unicode-modified-cache", perceptual_variant=False)
    finally:
        img.delete()
    img = Gimp.Image.new(64, 48, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(img, "Procedural background", 64, 48, 1)
        for name, closed in [("Open fractional cubic", False), ("Closed fractional cubic", True)]:
            path = Gimp.Path.new(img, name)
            img.insert_path(path, None, 0)
            points = [-8.5, 2.25, -4.5, 4.25, 2.5, 8.25,
                      18.125, -6.5, 24.125, 10.5, 32.125, 18.5,
                      72.5, 36.25, 68.5, 52.25, 64.5, 58.25]
            path.stroke_new_from_points(Gimp.PathStrokeType.BEZIER, points, closed)
        save(img, "paths-fractional-open-closed", perceptual_variant=False)
        vector = Gimp.VectorLayer.new(img, path)
        img.insert_layer(vector, None, 0)
        vector.set_fill_color(Gegl.Color.new("rgb(0.2,0.6,0.3)"))
        vector.set_enable_stroke(True)
        vector.set_stroke_color(Gegl.Color.new("rgb(0.8,0.2,0.4)"))
        vector.set_stroke_width(3.5)
        vector.set_stroke_width_unit(Gimp.Unit.pixel())
        vector.set_stroke_dash_pattern([2.0, 1.0, 4.0, 1.0])
        vector.set_stroke_dash_offset(1.25)
        vector.set_stroke_cap_style(Gimp.CapStyle.ROUND)
        vector.set_stroke_join_style(Gimp.JoinStyle.BEVEL)
        save(img, "vector-solid-dashed-stroke", perceptual_variant=False)
        if not vector.edit_fill(Gimp.FillType.WHITE):
            raise RuntimeError("could not apply destructive vector edit")
        fill(vector, vector.get_width(), vector.get_height(), 4, 8,
             lambda x, y, c: 255 if c == 3 else (x * 7 + y * 19 + c * 53) % 256)
        save(img, "vector-modified-cache", perceptual_variant=False)
    finally:
        img.delete()


def floating_relationships():
    """Floating content uses original pixels and an actual stock attachment pointer."""
    # GIMP 3.2.6 cannot reopen its own mask-attached floating selection reliably;
    # keep valid independently reopenable sources in this batch.
    for target_kind in ["rgb", "channel"]:
        img = Gimp.Image.new(32, 24, Gimp.ImageBaseType.RGB)
        try:
            base = rgba_layer(img, "Attachment layer", 32, 24, 2)
            if target_kind == "channel":
                target = Gimp.Channel.new(img, "Attachment channel", 32, 24, 40.0, Gegl.Color.new("blue"))
                img.insert_channel(target, None, 0)
                fill(target, 32, 24, 1, 8, lambda x, y, c: (x * 13 + y * 7) % 256)
            else:
                target = base
            floating = Gimp.Layer.new(img, "Floating original pixels", 9, 7,
                                      Gimp.ImageType.RGBA_IMAGE if target_kind == "rgb" else Gimp.ImageType.GRAYA_IMAGE,
                                      75.0, Gimp.LayerMode.NORMAL)
            if not Gimp.floating_sel_attach(floating, target):
                raise RuntimeError("could not attach floating selection")
            channels = 4 if target_kind == "rgb" else 2
            fill(floating, 9, 7, channels, 8,
                 lambda x, y, c: 192 if c == channels - 1 else (x * 19 + y * 23 + c * 37) % 256)
            floating.set_offsets(-2, 3)
            save(img, "floating-" + target_kind + "-negative-offset", perceptual_variant=False)
            reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(
                os.path.join(OUT, "floating-" + target_kind + "-negative-offset.xcf")))
            try:
                attachment = reopened.floating_sel_attached_to()
                if reopened.get_floating_sel() is None or attachment is None or attachment.get_name() != target.get_name():
                    raise RuntimeError("saved floating attachment did not survive stock reopen")
            finally:
                reopened.delete()
        finally:
            img.delete()


def linked_resource():
    """Link an original generated PNG using GIMP's relative XCF resource locator."""
    source = Gimp.Image.new(12, 9, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(source, "Original linked pixels", 12, 9, 3)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, source,
                       Gio.File.new_for_path(os.path.join(OUT, "link-source.png")), None)
    finally:
        source.delete()
    img = Gimp.Image.new(32, 24, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(img, "Unaffected sibling", 32, 24, 5)
        linked = Gimp.LinkLayer.new(img, Gio.File.new_for_path(os.path.join(OUT, "link-source.png")))
        img.insert_layer(linked, None, 0)
        linked.set_name("Relative original resource")
        linked.set_offsets(-2, 3)
        save(img, "link-relative-stored-pixels", perceptual_variant=False)
        with open(os.path.join(OUT, "link-relative-stored-pixels.xcf"), "rb") as saved:
            data = saved.read()
        if b"link-source.png" not in data or any(marker in data.lower() for marker in
                [b"c:/users/", b"c:\\users\\", b"/users/", b"/home/"]):
            raise RuntimeError("linked XCF did not store a privacy-safe relative resource locator")
    finally:
        img.delete()


def metadata_view():
    """Public, nonpersonal metadata and channel/view markers in stock serialization."""
    img = Gimp.Image.new(48, 36, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(img, "Metadata pixels", 48, 36, 4)
        img.set_resolution(144.0, 96.0)
        img.set_unit(Gimp.Unit.mm())
        img.attach_parasite(Gimp.Parasite.new("gimp-comment", 1, b"Original procedural metadata fixture\x00"))
        metadata = Gimp.Metadata.new()
        metadata.set_tag_string("Exif.Image.ImageDescription", "Original procedural XCF")
        metadata.set_tag_string("Xmp.dc.description", "Nonpersonal fixture description")
        img.set_metadata(metadata)
        channel = Gimp.Channel.new(img, "Overlay channel", 48, 36, 37.5, Gegl.Color.new("rgb(0.2,0.4,0.8)"))
        img.insert_channel(channel, None, 0)
        channel.set_show_masked(False)
        fill(channel, 48, 36, 1, 8, lambda x, y, c: (x * 5 + y * 11) % 256)
        img.set_selected_channels([channel])
        img.add_hguide(7)
        img.add_vguide(19)
        for n in range(12):
            img.add_sample_point(2 + n * 3, 2 + n * 2)
        save(img, "metadata-channel-view", perceptual_variant=False)
    finally:
        img.delete()


def tone_effects():
    """Small independent envelopes; unaffected sibling proves effect owner scope."""
    cases = [
        ("brightness-contrast", "gimp:brightness-contrast", {"brightness": 0.25, "contrast": -0.3}),
        ("levels", "gimp:levels", {"low-input": 0.1, "high-input": 0.9, "gamma": 1.4,
                                    "low-output": 0.05, "high-output": 0.95,
                                    "clamp-input": True, "clamp-output": False}),
        ("exposure", "gegl:exposure", {"black-level": 0.03, "exposure": 0.75}),
        ("gaussian-anisotropic", "gegl:gaussian-blur", {"std-dev-x": 2.0, "std-dev-y": 0.75}),
    ]
    for name, operation, parameters in cases:
        img = Gimp.Image.new(48, 32, Gimp.ImageBaseType.RGB)
        try:
            rgba_layer(img, "Unaffected sibling", 48, 32, 8)
            owner = rgba_layer(img, "Effect owner", 19, 13, 2)
            owner.set_offsets(7, 5)
            # Public DrawableFilter creation snapshots the live selection.
            img.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0, 48, 32)
            effect = Gimp.DrawableFilter.new(owner, operation, "Original " + name)
            config = effect.get_config()
            for key, value in parameters.items():
                config.set_property(key, value)
            effect.set_opacity(0.65)
            effect.set_blend_mode(Gimp.LayerMode.NORMAL)
            effect.update()
            owner.append_filter(effect)
            Gimp.Selection.none(img)
            save(img, "effect-" + name + "-owner", perceptual_variant=False)
        finally:
            img.delete()


def per_channel_curve_effect():
    """Original public-API curves on one offset owner; no development operations."""
    img = Gimp.Image.new(48, 32, Gimp.ImageBaseType.RGB)
    try:
        rgba_layer(img, "Unaffected sibling", 48, 32, 8)
        owner = rgba_layer(img, "Curve effect owner", 19, 13, 2)
        owner.set_offsets(7, 5)
        # The filter snapshots selection as its image-global coverage mask.
        # Select all explicitly so this fixture exercises visible curve output.
        img.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0, 48, 32)
        effect = Gimp.DrawableFilter.new(owner, "gimp:curves", "Original per-channel curves")
        config = effect.get_config()
        channels = [
            (Gimp.HistogramChannel.VALUE, [(0.0, 0.0), (0.35, 0.5), (1.0, 1.0)]),
            (Gimp.HistogramChannel.RED, [(0.0, 0.05), (0.5, 0.35), (1.0, 0.95)]),
            (Gimp.HistogramChannel.BLUE, [(0.0, 0.0), (0.65, 0.85), (1.0, 1.0)]),
            (Gimp.HistogramChannel.ALPHA, [(0.0, 0.0), (0.5, 0.65), (1.0, 1.0)]),
        ]
        for channel, anchors in channels:
            config.set_property("channel", channel)
            curve = config.get_property("curve")
            curve.clear_points()
            for x, y in anchors:
                curve.add_point(x, y)
            config.set_property("curve", curve)
            effect.update()
        effect.set_opacity(0.65)
        effect.set_blend_mode(Gimp.LayerMode.NORMAL)
        effect.update()
        owner.append_filter(effect)
        Gimp.Selection.none(img)
        save(img, "effect-curves-per-channel-owner", perceptual_variant=False)
    finally:
        img.delete()


def original_profile(gray=False):
    """Original ICC v2 matrix/gamma data assembled from public ICC field layouts.

    This intentionally synthetic RGB gamut differs from sRGB. The three XYZ columns
    sum to D50 (.9642, 1, .8249); gamma is 1.8. No bundled or downloaded profile is used.
    """
    def fixed(value):
        return struct.pack(">i", round(value * 65536))
    def xyz(values):
        return b"XYZ \0\0\0\0" + b"".join(fixed(v) for v in values)
    def desc(value):
        text = value.encode("ascii") + b"\0"
        return b"desc\0\0\0\0" + struct.pack(">I", len(text)) + text + bytes(8 + 2 + 1 + 67)
    curve = b"curv\0\0\0\0" + struct.pack(">IH", 1, round(1.8 * 256))
    tags = [(b"desc", desc("Original procedural Gray gamma 1.8" if gray else "Original procedural RGB gamma 1.8")),
            (b"cprt", b"text\0\0\0\0Original procedural fixture; MIT OR Apache-2.0\0"),
            (b"wtpt", xyz([.9642, 1.0, .8249]))]
    if gray:
        tags.append((b"kTRC", curve))
    else:
        for signature, values in [(b"rXYZ", [.6, .2, .01]), (b"gXYZ", [.25, .7, .1]),
                                  (b"bXYZ", [.1142, .1, .7149])]:
            tags.append((signature, xyz(values)))
        tags += [(signature, curve) for signature in [b"rTRC", b"gTRC", b"bTRC"]]
    header = bytearray(128)
    header[8:12] = bytes([2, 0x10, 0, 0])
    header[12:24] = b"mntr" + (b"GRAY" if gray else b"RGB ") + b"XYZ "
    header[24:36] = struct.pack(">6H", 2026, 1, 1, 0, 0, 0)
    header[36:40] = b"acsp"
    header[68:80] = b"".join(fixed(v) for v in [.9642, 1.0, .8249])
    table = bytearray(struct.pack(">I", len(tags)))
    data = bytearray()
    for signature, payload in tags:
        table += signature + struct.pack(">II", 128 + 4 + 12 * len(tags) + len(data), len(payload))
        data += payload
        data += bytes((-len(data)) % 4)
    result = header + table + data
    result[0:4] = struct.pack(">I", len(result))
    return Gimp.ColorProfile.new_from_icc_profile(bytes(result))


def effect_stack_masks():
    for distinct in [False, True]:
        img = Gimp.Image.new(48, 32, Gimp.ImageBaseType.RGB)
        try:
            rgba_layer(img, "Unaffected sibling", 48, 32, 8)
            owner = rgba_layer(img, "Effect stack owner", 19, 13, 2)
            owner.set_offsets(7, 5)
            for index, operation in enumerate(["gimp:brightness-contrast", "gegl:exposure"]):
                x, y = (12, 8) if distinct and index == 1 else (7, 5)
                img.select_rectangle(Gimp.ChannelOps.REPLACE, x, y, 8, 6)
                effect = Gimp.DrawableFilter.new(owner, operation, "Stack stage " + str(index + 1))
                config = effect.get_config()
                config.set_property("brightness" if index == 0 else "exposure", 0.25 if index == 0 else 0.75)
                effect.set_opacity(0.5 if index == 0 else 0.8)
                effect.update()
                owner.append_filter(effect)
                if distinct and index == 1:
                    effect.set_visible(False)
            Gimp.Selection.none(img)
            save(img, "effect-stack-" + ("distinct-masks-disabled" if distinct else "common-mask"), perceptual_variant=False)
        finally:
            img.delete()


def assigned_color_profiles():
    for gray in [False, True]:
        for encoding, precision in [("linear", Gimp.Precision.FLOAT_LINEAR),
                                    ("perceptual", Gimp.Precision.FLOAT_PERCEPTUAL)]:
            name = "profile-original-" + ("gray" if gray else "rgb") + "-" + encoding
            img = Gimp.Image.new_with_precision(16, 12, Gimp.ImageBaseType.GRAY if gray else Gimp.ImageBaseType.RGB, precision)
            try:
                channels = 2 if gray else 4
                layer = Gimp.Layer.new(img, "Literal assigned-profile samples", 9, 5,
                                      Gimp.ImageType.GRAYA_IMAGE if gray else Gimp.ImageType.RGBA_IMAGE,
                                      100.0, Gimp.LayerMode.NORMAL)
                img.insert_layer(layer, None, 0)
                layer.set_offsets(2, -1)
                prefix = "Y" if gray else "RGB"
                fmt = ("Y~A" if gray else "R~G~B~A") + " float" if encoding == "perceptual" else prefix + "A float"
                values = [(.125, .25, .5, .75)[(x + y + c) % 4] if c != channels - 1 else 1.0
                          for y in range(5) for x in range(9) for c in range(channels)]
                data = struct.pack("=" + "f" * len(values), *values)
                rect = Gegl.Rectangle.new(0, 0, 9, 5)
                buffer = layer.get_buffer()
                buffer.set(rect, fmt, data)
                buffer.flush()
                layer.update(0, 0, 9, 5)
                # Assigning the profile changes interpretation, never the stored samples.
                # A NULL get format returns native bytes, avoiding a conversion to sRGB.
                img.set_color_profile(original_profile(gray))
                buffer = layer.get_buffer()
                if bytes(buffer.get(rect, 1.0, None, Gegl.AbyssPolicy.NONE)) != data:
                    raise RuntimeError(name + ": source samples changed before save")
                save(img, name, perceptual_variant=False)
                reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(os.path.join(OUT, name + ".xcf")))
                try:
                    if reopened.get_precision() != precision or reopened.get_color_profile() is None:
                        raise RuntimeError(name + ": assigned precision/profile changed")
                    stored = reopened.get_layers()[0].get_buffer().get(rect, 1.0, None, Gegl.AbyssPolicy.NONE)
                    if bytes(stored) != data:
                        raise RuntimeError(name + ": source samples changed after reopen")
                finally:
                    reopened.delete()
            finally:
                img.delete()


makers = [layers_8bit, groups, mask, gray16, float_linear, indexed, text, channel, legacy_modes, precision_variants,
          native_text_paths, floating_relationships, linked_resource, metadata_view, tone_effects,
          assigned_color_profiles, effect_stack_masks, per_channel_curve_effect]
selected = {name.strip() for name in os.environ.get("PHOTOCRAFT_XCF_CASES", "").split(",") if name.strip()}
unknown = selected - {make.__name__ for make in makers}
if unknown:
    raise ValueError("unknown XCF case selector: " + ", ".join(sorted(unknown)))
failed = []
for make in makers:
    if selected and make.__name__ not in selected:
        continue
    try:
        make()
    except Exception as e:  # noqa: BLE001
        failed.append(make.__name__)
        print("FAILED", make.__name__, repr(e))
if failed:
    raise RuntimeError("XCF generation failed: " + ", ".join(failed))
print("done")
