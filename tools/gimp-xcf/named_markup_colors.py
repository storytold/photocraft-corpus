#!/usr/bin/env python3
"""Original named-color markup witness, stock GIMP 3.2.6 / Pango 1.58.2.

From this repository root run GIMP headless with the python-fu-eval interpreter:
  gimp --new-instance --no-interface --batch-interpreter=python-fu-eval \
    --batch="exec(open('tools/gimp-xcf/named_markup_colors.py', encoding='utf-8').read())" --quit
Only constructs original text and refers to a font by name; no font asset ships.
The generator saves, deletes, reopens, queries actual markup, and exports a PNG.
Run historical_png_metadata.sanitize on the PNG to remove ancillary export metadata.
Public Pango.Color parse observations are source facts, not a copied implementation.
"""
import os, json, hashlib
from pathlib import Path
import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gimp, Gio, Pango

out = Path(os.environ.get('PHOTOCRAFT_NAMED_COLOR_OUT', Path.cwd() / 'gimp')); out.mkdir(parents=True, exist_ok=True)
names = ['green', 'gray', 'grey', 'maroon', 'purple', 'red', 'LightGoldenrodYellow', 'light goldenrod yellow',
         'LiGhTgOlDeNrOdYeLlOw', ' lightgoldenrodyellow ', 'light\tgoldenrod\tyellow', 'light-goldenrod-yellow',
         'light_goldenrod_yellow', 'gray42', 'grey42', 'steelblue4', 'RebeccaPurple', 'transparent', 'rgb(0,128,0)', 'unknown-color-name']
rows = []
for name in names:
    color = Pango.Color()
    parsed = color.parse(name)
    row = {'name': name, 'colorParse': bool(parsed), 'rgb16': [color.red, color.green, color.blue] if parsed else None}
    alpha_color = Pango.Color()
    alpha_result = alpha_color.parse_with_alpha(name)
    row['parseWithAlpha'] = list(alpha_result)
    row['rgba16'] = [alpha_color.red, alpha_color.green, alpha_color.blue, alpha_result[1]] if alpha_result[0] else None
    markup = '<markup><span foreground="' + name + '">X</span></markup>'
    try:
        result = Pango.parse_markup(markup, -1, '\0')
        row['markupAccepted'] = bool(result[0]); row['markupText'] = result[2]
    except Exception as error:
        row['markupAccepted'] = False; row['markupError'] = str(error)
    rows.append(row)

markup = '<markup><span foreground="green">Green </span><span color="gray">Gray </span><span fgcolor="LightGoldenrodYellow" alpha="32768">Gold </span><span foreground="gray42">42 </span><span foreground="steelblue4">Steel</span>\n<span foreground="grey">Y </span><span foreground="maroon">M </span><span foreground="purple">P </span><span foreground="red">R </span><span foreground="light goldenrod yellow">L </span><span foreground="LiGhTgOlDeNrOdYeLlOw">C </span><span foreground="RebeccaPurple">B</span></markup>'
accepted = Pango.parse_markup(markup, -1, '\0')
if not accepted[0]: raise RuntimeError('original named markup rejected')
image = Gimp.Image.new(300, 70, Gimp.ImageBaseType.RGB)
layer = Gimp.TextLayer.new(image, 'Named colors', Gimp.context_get_font(), 16., Gimp.Unit.pixel())
image.insert_layer(layer, None, 0)
result = layer.set_markup(markup)
layer.set_name('Original named markup')
layer.set_offsets(3, 4)
path = out / 'text-named-markup-colors.xcf'
if not Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(str(path)), None): raise RuntimeError('save failed')
image.delete()
reopened = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(str(path)))
loaded = reopened.get_layers()[0]
facts = {'gimpVersion': Gimp.version(), 'pangoVersion': Pango.version_string(), 'colors': rows,
         'fixture': {'file': path.name, 'canvas': [reopened.get_width(), reopened.get_height()], 'sourceMarkup': markup,
                     'setMarkupResult': result, 'storedReopenedMarkup': loaded.get_markup(), 'offsets': list(loaded.get_offsets()),
                     'textSizePixels': loaded.get_font_size()[0], 'fontName': loaded.get_font().get_name(),
                     'isText': isinstance(loaded, Gimp.TextLayer), 'sourcePrecision': int(reopened.get_precision())}}
second = out / 'text-named-markup-colors-reopened.xcf'
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, reopened, Gio.File.new_for_path(str(second)), None)
merged = reopened.duplicate(); merged.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, merged, Gio.File.new_for_path(str(out/'text-named-markup-colors.png')), None)
merged.delete(); reopened.delete()
invalid_image = Gimp.Image.new(8, 8, Gimp.ImageBaseType.RGB)
invalid_layer = Gimp.TextLayer.new(invalid_image, 'Original', Gimp.context_get_font(), 12., Gimp.Unit.pixel())
invalid_image.insert_layer(invalid_layer, None, 0)
invalid_layer.set_markup('<markup><span color="green">Original</span></markup>')
try:
    rejected = invalid_layer.set_markup('<markup><span color="unknown-color-name">Rejected</span></markup>')
    facts['unknownGimpMarkup'] = {'setMarkupResult': rejected, 'readbackMarkup': invalid_layer.get_markup()}
except Exception as error:
    facts['unknownGimpMarkup'] = {'exception': str(error), 'readbackMarkup': invalid_layer.get_markup()}
invalid_image.delete()
facts['fixture']['xcfSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
(out/'text-named-markup-colors.source-facts.json').write_text(json.dumps(facts, indent=2), encoding='utf-8')
print('SOL7_NAMED_COLORS_OK ' + json.dumps(facts), flush=True)
