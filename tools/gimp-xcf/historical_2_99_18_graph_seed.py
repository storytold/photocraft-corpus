#!/usr/bin/env python3
"""Original documented-wire bootstrap inputs, NOT GIMP/UI-authored XCFs.

These are intermediate seeds only. Run the accompanying ordinary stock2.99.18
ScriptFu resave/reopen generator to produce qualified final corpus files.
Wire declarations: GIMP_2_99_18 app/xcf/xcf-{save,load}.c and xcf-private.h.
No GIMP image-processing algorithms, graph interpreter or font/profile assets.
"""
import argparse
from pathlib import Path
import struct


class Wire:
    def __init__(self): self.data = bytearray()
    def word(self, x): self.data.extend(struct.pack('>I', x))
    def pointer(self, x): self.data.extend(struct.pack('>Q', x))
    def slot(self):
        at = len(self.data); self.pointer(0); return at
    def patch(self, at): struct.pack_into('>Q', self.data, at, len(self.data))
    def text(self, value):
        data = value.encode(); self.word(len(data) + 1); self.data.extend(data + b'\0')
    def prop(self, kind, data):
        self.word(kind); self.word(len(data)); self.data.extend(data)
    def end(self): self.word(0); self.word(0)
    def hierarchy(self, channels, data):
        for value in (8, 6, channels): self.word(value)
        level = self.slot(); self.pointer(0); self.patch(level)
        self.word(8); self.word(6)
        tile = self.slot(); self.pointer(0); self.patch(tile)
        self.data.extend(data)


def seed(graph):
    pixels = bytes(value for y in range(6) for x in range(8) for value in (
        (x * 23 + 17) % 256, (y * 37 + 13) % 256,
        (x * 11 + y * 19 + 29) % 256, 64 + ((x + y) % 4) * 48))
    w = Wire(); w.data.extend(b'gimp xcf v020\0')
    for value in (8, 6, 0, 150): w.word(value)
    w.prop(17, b'\0'); w.end()
    owner = w.slot(); w.pointer(0); w.pointer(0); w.pointer(0)
    w.patch(owner)
    for value in (8, 6, 1): w.word(value)
    w.text('Original procedural owner')
    w.prop(15, struct.pack('>ii', 0, 0)); w.prop(8, struct.pack('>I', 1))
    w.prop(33, struct.pack('>f', 1)); w.prop(7, struct.pack('>I', 28)); w.end()
    hierarchy = w.slot(); w.pointer(0); effect = w.slot(); w.pointer(0)
    w.patch(hierarchy); w.hierarchy(4, pixels)
    w.patch(effect)
    w.text('Disclosed graph bootstrap'); w.text(''); w.text('gegl:gegl')
    for kind, value in ((8, 1), (7, 28), (37, 0), (36, 0), (35, 0), (44, 1)):
        w.prop(kind, struct.pack('>I', value))
    w.prop(33, struct.pack('>f', 1))
    arg = Wire(); arg.text('string'); arg.word(4); arg.text(graph)
    w.prop(45, arg.data); w.end()
    mask = w.slot(); w.patch(mask)
    w.word(8); w.word(6); w.text('Original full coverage')
    w.prop(33, struct.pack('>f', 1)); w.prop(8, struct.pack('>I', 1)); w.end()
    hierarchy = w.slot(); w.pointer(0); w.patch(hierarchy)
    w.hierarchy(1, bytes([255]) * 48)
    return w.data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('work_directory', type=Path)
    args = parser.parse_args()
    args.work_directory.mkdir(parents=True, exist_ok=True)
    for name, graph in (
        ('invert-linear', 'invert-linear'),
        ('original-over-inverted', 'id=foo over aux=[ ref=foo invert-linear ]')):
        path = args.work_directory / (name + '-seed.xcf')
        path.write_bytes(seed(graph))
        print('bootstrap seed, not corpus witness:', path.name)
