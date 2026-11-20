#!/usr/bin/env python3
"""Author graph fixtures from scratch through stock GIMP's public Python API.

Run inside GIMP 3.2.6, from the corpus root, with an isolated GIMP3_DIRECTORY:
GIMP_ALLOW_GEGL_GRAPH_LAYER_EFFECT=1 gimp-console --new-instance --no-interface \
    --batch-interpreter=python-fu-eval \
    --batch="exec(open('tools/gimp-xcf/graph_filters.py').read())" --quit

GIMP itself requests this experimental opt-in when creating a graph layer effect.
No XCF seed, wire writer, implementation declaration or internal setter is used.
Set PHOTOCRAFT_GRAPH_MODE=verify for an independent reopen without regeneration.
PHOTOCRAFT_GRAPH_OUTPUT may select a separate output directory for reproduction.
"""

import hashlib
import json
import os
from pathlib import Path
import sys

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import Gegl, Gimp, Gio  # noqa: E402

ROOT = Path.cwd()
OUT = Path(os.environ.get("PHOTOCRAFT_GRAPH_OUTPUT", str(ROOT / "gimp")))
FACTS = Path(os.environ.get("PHOTOCRAFT_GRAPH_FACTS", str(
    ROOT / "tools" / "gimp-xcf" / "graph_filters.source-facts.json")))
sys.path.insert(0, str(ROOT / "tools" / "gimp-xcf"))
from historical_png_metadata import sanitize  # noqa: E402

CASES = (
    ("invert-linear", "invert-linear"),
    ("original-over-inverted", "id=original over aux=[ ref=original invert-linear ]"),
)
RECT = Gegl.Rectangle.new(0, 0, 8, 6)
FORMAT = "R'G'B'A u8"


def original_pixels():
    return bytes(value for y in range(6) for x in range(8) for value in (
        (x * 23 + 17) % 256, (y * 37 + 13) % 256,
        (x * 11 + y * 19 + 29) % 256, 64 + ((x + y) % 4) * 48))


def pixels(layer):
    return bytes(layer.get_buffer().get(RECT, 1.0, FORMAT, Gegl.AbyssPolicy.NONE))


def author(path, graph):
    image = Gimp.Image.new_with_precision(8, 6, Gimp.ImageBaseType.RGB,
                                         Gimp.Precision.U8_NON_LINEAR)
    try:
        image.set_resolution(96.0, 96.0)
        owner = Gimp.Layer.new(image, "Original procedural graph owner", 8, 6,
                               Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
        image.insert_layer(owner, None, 0)
        buffer = owner.get_buffer()
        buffer.set(RECT, FORMAT, original_pixels())
        buffer.flush()
        owner.update(0, 0, 8, 6)
        image.select_rectangle(Gimp.ChannelOps.REPLACE, 0, 0, 8, 6)
        effect = Gimp.DrawableFilter.new(owner, "gegl:gegl", "Original procedural graph")
        config = effect.get_config()
        config.set_property("string", graph)
        effect.set_opacity(1.0)
        effect.set_blend_mode(Gimp.LayerMode.NORMAL)
        effect.update()
        owner.append_filter(effect)
        Gimp.Selection.none(image)
        assert pixels(owner) == original_pixels()
        assert Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
                              Gio.File.new_for_path(str(path)), None)
    finally:
        image.delete()


def reopen(path, graph, export):
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(str(path)))
    try:
        assert (image.get_width(), image.get_height()) == (8, 6)
        assert image.get_precision() == Gimp.Precision.U8_NON_LINEAR
        layers = image.get_layers()
        assert len(layers) == 1
        owner = layers[0]
        source = pixels(owner)
        assert source == original_pixels()
        filters = owner.get_filters()
        assert len(filters) == 1
        effect = filters[0]
        assert effect.get_operation_name() == "gegl:gegl"
        assert effect.get_config().get_property("string") == graph
        assert effect.get_opacity() == 1.0 and effect.get_visible()
        assert effect.get_blend_mode() == Gimp.LayerMode.NORMAL
        # Materialize only a duplicate of the reopened document for GIMP's preview.
        preview = image.duplicate()
        try:
            rendered = preview.get_layers()[0]
            assert rendered.merge_filters()
            result = pixels(rendered)
            assert len(result) == 8 * 6 * 4 and result != source
            png = path.with_suffix(".png")
            if export:
                assert Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, preview,
                                      Gio.File.new_for_path(str(png)), None)
                sanitize(png)
            # Reopening the exported PNG also checks that it contains this rendering.
            oracle = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                                    Gio.File.new_for_path(str(png)))
            try:
                assert pixels(oracle.get_layers()[0]) == result
            finally:
                oracle.delete()
        finally:
            preview.delete()
        return {"name": path.stem, "graph": graph, "canvas": [8, 6],
                "sourceRgba8Hex": source.hex(), "previewRgba8Hex": result.hex(),
                "xcfSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "pngSha256": hashlib.sha256(png.read_bytes()).hexdigest()}
    finally:
        image.delete()


if Gimp.version() != "3.2.6":
    raise RuntimeError("This batch is qualified with stock GIMP 3.2.6")
if not os.environ.get("GIMP_ALLOW_GEGL_GRAPH_LAYER_EFFECT"):
    raise RuntimeError("GIMP requires GIMP_ALLOW_GEGL_GRAPH_LAYER_EFFECT=1 for graph effects")
mode = os.environ.get("PHOTOCRAFT_GRAPH_MODE", "generate")
if mode not in ("generate", "verify"):
    raise ValueError("PHOTOCRAFT_GRAPH_MODE must be generate or verify")
OUT.mkdir(parents=True, exist_ok=True)
results = []
for suffix, graph in CASES:
    path = OUT / ("graph-" + suffix + ".xcf")
    if mode == "generate":
        author(path, graph)
    results.append(reopen(path, graph, mode == "generate"))
facts = {"producer": Gimp.version(), "method": "public API author/save/delete/reopen",
         "experimentalGraphOptIn": True, "bootstrapUsed": False,
         "results": results}
if mode == "generate":
    FACTS.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf8")
print("GRAPH_FIXTURES_VERIFIED " + json.dumps(facts), flush=True)
