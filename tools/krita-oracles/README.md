# Krita oracles

`generate.py` builds the files in [`krita/`](../../krita) from scratch in Krita (procedural
pixels only; no images, brushes, fonts or profiles from anywhere else). Each case is saved as a
native `.kra` and exported as OpenRaster (`.ora`); both carry Krita's own rendering of the layer
stack in `mergedimage.png`, which PhotoCraft compares its import against.

Krita embeds Elle Stone's ICC profiles (CC BY-SA 3.0) in every `.kra`. The corpus carries no
third-party profiles, so the generator removes `*/annotations/icc` from each `.kra` after saving
and builds every document with the sRGB tone curve, so the files mean the same without the
profile (Krita opens them as sRGB and renders them as before).

## Running (Linux, headless)

Needs Krita 5.2 (`kritarunner` ships with it) and PyQt5 for its Python (`python3-pyqt5` on
Debian/Ubuntu). From the repository root:

```sh
env -u DISPLAY QT_QPA_PLATFORM=offscreen PYTHONPATH=tools/krita-oracles \
    kritarunner -s generate -f main
```

Every line of `krita/generate.log` must read `ok`. Delete the log before committing, then
regenerate `SHA256SUMS` (see the top-level README).
