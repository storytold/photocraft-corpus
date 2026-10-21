"""Krita oracle generator for photocraft-corpus.

Builds small documents from scratch in Krita (procedural pixels only, no external images),
then saves each one as a native .kra and exports it as OpenRaster (.ora). Both files carry
Krita's own rendering of the layer stack (mergedimage.png), which PhotoCraft's tests compare
against.

Run headless (see README.md next to this file):
    env -u DISPLAY QT_QPA_PLATFORM=offscreen PYTHONPATH=tools/krita-oracles \
        kritarunner -s generate -f main
Output goes to krita/ in the repository root; set KRITA_ORACLES_OUT to override.
A log of every case (ok or skip) is written to krita/generate.log.
"""

import os
import struct
import zipfile

from krita import InfoObject, Krita

SIZE = 96
OUT = os.environ.get(
    "KRITA_ORACLES_OUT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "krita"),
)
LOG = []

# Krita blending-mode ids exercised by the blend cases (each file name carries the id).
MODES = [
    "normal", "multiply", "screen", "overlay", "darken", "lighten", "dodge", "burn",
    "hard_light", "soft_light", "diff", "exclusion", "linear_burn", "linear_dodge", "add",
    "subtract", "divide", "vivid_light", "linear light", "pin_light", "hard_mix_photoshop",
    "darker color", "lighter color", "hue", "saturation", "color", "luminize",
]


def clamp(v):
    return max(0, min(255, int(v)))


def pixels_u8(w, h, f):
    """BGRA8 bytes from f(x, y) -> (r, g, b, a) in 0..255."""
    out = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = f(x, y)
            out += bytes((clamp(b), clamp(g), clamp(r), clamp(a)))
    return bytes(out)


def pixels_u16(w, h, f):
    """BGRA16 little-endian bytes from f(x, y) -> (r, g, b, a) in 0..65535."""
    out = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = f(x, y)
            out += struct.pack("<4H", *(max(0, min(65535, int(v))) for v in (b, g, r, a)))
    return bytes(out)


def gray_u8(w, h, f):
    """GrayA8 bytes from f(x, y) -> (v, a)."""
    out = bytearray()
    for y in range(h):
        for x in range(w):
            v, a = f(x, y)
            out += bytes((clamp(v), clamp(a)))
    return bytes(out)


def backdrop(x, y):
    # Horizontal hue-ish ramp over a vertical value ramp: every blend mode has something to do.
    t = x / (SIZE - 1)
    u = y / (SIZE - 1)
    return (255 * t, 255 * (1 - t) * u + 40, 255 * (1 - u), 255)


def disc(cx, cy, r, color):
    def f(x, y):
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        a = 255 * max(0.0, min(1.0, r - d))
        return (*color, a)
    return f


def stripes(x, y):
    on = (x // 6 + y // 6) % 2 == 0
    return (230, 200, 60, 255) if on else (40, 90, 200, 180)


def new_doc(name, model="RGBA", depth="U8"):
    # Every document uses the sRGB tone curve (Krita's 16-bit default is linear light), so the
    # files still mean the same after strip_profile() removes the embedded profile.
    profile = "sRGB-elle-V2-srgbtrc.icc" if model == "RGBA" else ""
    d = Krita.instance().createDocument(SIZE, SIZE, name, model, depth, profile, 72.0)
    # createDocument adds an empty "Background" paint layer; drop it so each case is explicit.
    for n in list(d.rootNode().childNodes()):
        d.rootNode().removeChildNode(n)
    return d


def paint(d, parent, name, data, x=0, y=0, w=SIZE, h=SIZE, mode="normal", opacity=255, visible=True):
    n = d.createNode(name, "paintlayer")
    parent.addChildNode(n, None)
    n.setPixelData(data, x, y, w, h)
    n.setBlendingMode(mode)
    n.setOpacity(opacity)
    n.setVisible(visible)
    return n


def strip_profile(path):
    """Removes the embedded ICC profile from a saved .kra.

    Krita embeds Elle Stone's CC BY-SA profiles, and the corpus carries no third-party ICC
    profiles. Without one, Krita and PhotoCraft both read the pixels as sRGB (gray: sGray).
    The archive is otherwise rewritten entry for entry: mimetype first and stored, the rest
    with their original compression.
    """
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w") as dst:
        for info in src.infolist():
            if info.filename.endswith("/annotations/icc"):
                continue
            dst.writestr(info, src.read(info.filename), compress_type=info.compress_type)
    os.replace(tmp, path)
    backup = path + "~"
    if os.path.exists(backup):
        os.remove(backup)


def save(d, stem):
    d.refreshProjection()
    d.waitForDone()
    kra = os.path.join(OUT, stem + ".kra")
    ora = os.path.join(OUT, stem + ".ora")
    ok_kra = d.saveAs(kra)
    ok_ora = d.exportImage(ora, InfoObject())
    d.close()
    if ok_kra:
        strip_profile(kra)
    LOG.append(f"{'ok' if ok_kra else 'skip'} {stem}.kra")
    LOG.append(f"{'ok' if ok_ora else 'skip'} {stem}.ora")


def case_blend(mode):
    d = new_doc("blend")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    paint(d, root, "Blend " + mode, pixels_u8(SIZE, SIZE, stripes), mode=mode)
    save(d, "blend-" + mode.replace(" ", "_"))


def case_opacity_visibility():
    d = new_doc("opacity")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    paint(d, root, "Half", pixels_u8(SIZE, SIZE, disc(30, 40, 22, (250, 30, 30))), opacity=128)
    paint(d, root, "Hidden", pixels_u8(SIZE, SIZE, disc(60, 50, 25, (20, 250, 20))), visible=False)
    paint(d, root, "Quarter", pixels_u8(SIZE, SIZE, disc(64, 30, 20, (20, 20, 250))), opacity=64)
    save(d, "layers-opacity-visibility")


def case_offsets():
    # Layer content partly outside the canvas, at negative and positive offsets.
    d = new_doc("offsets")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    paint(d, root, "Left out", pixels_u8(40, 30, stripes), x=-15, y=10, w=40, h=30)
    paint(d, root, "Bottom out", pixels_u8(50, 40, lambda x, y: (240, 120, 30, 200)), x=60, y=70, w=50, h=40)
    paint(d, root, "Across tiles", pixels_u8(80, 20, lambda x, y: (x * 3, 40, 200, 255)), x=10, y=60, w=80, h=20)
    save(d, "layers-offsets")


def case_moved():
    # Layers moved after painting: Krita keeps the paint device's offset in the layer's x/y.
    d = new_doc("moved")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    a = paint(d, root, "Moved right", pixels_u8(30, 30, stripes), x=0, y=0, w=30, h=30)
    a.move(50, 20)
    b = paint(d, root, "Moved up-left", pixels_u8(40, 20, lambda x, y: (250, 80, 20, 220)), x=40, y=60, w=40, h=20)
    b.move(-10, -5)
    g = d.createGroupLayer("Moved group")
    root.addChildNode(g, None)
    paint(d, g, "In moved group", pixels_u8(20, 20, lambda x, y: (20, 200, 90, 255)), x=10, y=10, w=20, h=20)
    g.move(30, 40)
    save(d, "layers-moved")


def case_groups():
    d = new_doc("groups")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    g = d.createGroupLayer("Isolated multiply")
    root.addChildNode(g, None)
    paint(d, g, "Inner A", pixels_u8(SIZE, SIZE, disc(35, 35, 25, (250, 220, 40))))
    paint(d, g, "Inner B screen", pixels_u8(SIZE, SIZE, disc(55, 50, 25, (40, 80, 250))), mode="screen")
    g.setBlendingMode("multiply")
    g.setOpacity(200)
    p = d.createGroupLayer("Pass-through")
    root.addChildNode(p, None)
    p.setPassThroughMode(True)
    paint(d, p, "Through overlay", pixels_u8(SIZE, SIZE, stripes), mode="overlay", opacity=180)
    n = d.createGroupLayer("Nested outer")
    root.addChildNode(n, None)
    inner = d.createGroupLayer("Nested inner")
    n.addChildNode(inner, None)
    paint(d, inner, "Deep", pixels_u8(SIZE, SIZE, disc(70, 70, 18, (240, 240, 240))))
    h = d.createGroupLayer("Hidden group")
    root.addChildNode(h, None)
    paint(d, h, "Under hidden", pixels_u8(SIZE, SIZE, disc(20, 75, 15, (0, 0, 0))))
    h.setVisible(False)
    save(d, "groups-isolated-passthrough-nested")


def case_transparency_mask():
    d = new_doc("mask")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    top = paint(d, root, "Masked", pixels_u8(SIZE, SIZE, stripes))
    m = d.createTransparencyMask("Radial mask")
    top.addChildNode(m, None)
    # Alpha8 mask: one byte per pixel, a soft radial falloff.
    data = bytearray()
    for y in range(SIZE):
        for x in range(SIZE):
            dist = ((x - 48) ** 2 + (y - 48) ** 2) ** 0.5
            data.append(clamp(255 * (1 - dist / 48)))
    m.setPixelData(bytes(data), 0, 0, SIZE, SIZE)
    save(d, "mask-transparency")


def case_u16():
    d = new_doc("u16", "RGBA", "U16")
    root = d.rootNode()
    paint(d, root, "Ramp16", pixels_u16(SIZE, SIZE, lambda x, y: (x * 680, y * 680, 30000, 65535)))
    paint(d, root, "Disc16", pixels_u16(SIZE, SIZE, lambda x, y: (65535, 1000, 1000, 65535 if (x - 48) ** 2 + (y - 48) ** 2 < 900 else 0)), mode="multiply")
    save(d, "depth-rgba-u16")


def case_gray():
    d = new_doc("gray", "GRAYA", "U8")
    root = d.rootNode()
    paint(d, root, "Gray ramp", gray_u8(SIZE, SIZE, lambda x, y: (x * 2.6, 255)))
    paint(d, root, "Gray disc", gray_u8(SIZE, SIZE, lambda x, y: (220, 255 if (x - 48) ** 2 + (y - 48) ** 2 < 600 else 0)), opacity=160)
    save(d, "colour-graya-u8")


def case_unsupported_nodes():
    # Node kinds PhotoCraft does not model yet: vector, filter and fill layers. The importer
    # must report them, and the merged image tells the tests what Krita drew.
    d = new_doc("unsupported")
    root = d.rootNode()
    paint(d, root, "Backdrop", pixels_u8(SIZE, SIZE, backdrop))
    v = d.createVectorLayer("Vector")
    root.addChildNode(v, None)
    v.addShapesFromSvg(
        '<svg xmlns="http://www.w3.org/2000/svg" width="96pt" height="96pt" viewBox="0 0 96 96">'
        '<rect x="20" y="20" width="40" height="30" fill="#ff8800"/></svg>'
    )
    f = Krita.instance().filter("invert")
    if f is not None:
        sel = None
        fl = d.createFilterLayer("Invert filter", f, sel) if sel is not None else None
        if fl is not None:
            root.addChildNode(fl, None)
    save(d, "nodes-vector-unsupported")


def main(*_args):
    Krita.instance().setBatchmode(True)
    os.makedirs(OUT, exist_ok=True)
    for mode in MODES:
        case_blend(mode)
    case_opacity_visibility()
    case_offsets()
    case_moved()
    case_groups()
    case_transparency_mask()
    case_u16()
    case_gray()
    case_unsupported_nodes()
    with open(os.path.join(OUT, "generate.log"), "w") as log:
        log.write("\n".join(LOG) + "\n")
