// PhotoCraft Photoshop oracle corpus generator (ExtendScript, run inside Adobe Photoshop).
//
// Authors every file of photoshop/ (storytold/photocraft-corpus) from scratch: generated gradients, shapes and text
// (no third-party images, no Adobe presets, patterns, contours or profiles). Each file is saved
// with Maximize Compatibility on, so its merged composite is Photoshop's own rendering of the
// layer stack: the oracle PhotoCraft's corpus tests compare its flatten with.
//
// Run:  tools/photoshop-oracles/generate.sh [filter-regex]
// (or:  tools/photoshop-oracles/run-jsx.sh tools/photoshop-oracles/generate.jsx <out-dir> [filter-regex])
//
// Clean-room: this script only drives Photoshop's public scripting API and keeps its output.
// Contours and gradients below are our own point lists, not Photoshop presets.

#target photoshop

var OUT = (typeof arguments !== "undefined" && arguments.length > 0) ? arguments[0] : "~/Desktop/photoshop-oracles";
var FILTER = (typeof arguments !== "undefined" && arguments.length > 1 && arguments[1]) ? new RegExp(arguments[1]) : null;

function cTID(s) { return charIDToTypeID(s); }
function sTID(s) { return stringIDToTypeID(s); }
function tid(s) { return s.length === 4 ? cTID(s) : sTID(s); }

// ---------------------------------------------------------------------------------------------
// Basic helpers
// ---------------------------------------------------------------------------------------------

function rgbDesc(c) {
    var d = new ActionDescriptor();
    d.putDouble(cTID("Rd  "), c[0]);
    d.putDouble(cTID("Grn "), c[1]);
    d.putDouble(cTID("Bl  "), c[2]);
    return d;
}

function solid(c) {
    var s = new SolidColor();
    s.rgb.red = c[0];
    s.rgb.green = c[1];
    s.rgb.blue = c[2];
    return s;
}

function px(v) { return new UnitValue(v, "px"); }

var MODES = { rgb: NewDocumentMode.RGB, gray: NewDocumentMode.GRAYSCALE, cmyk: NewDocumentMode.CMYK, lab: NewDocumentMode.LAB };
var BITS = { 8: BitsPerChannelType.EIGHT, 16: BitsPerChannelType.SIXTEEN, 32: BitsPerChannelType.THIRTYTWO };

/// New RGB 8-bit document at 72 ppi (so 1 pt = 1 px), transparent or white.
function newDoc(name, w, h, fill) {
    return app.documents.add(px(w), px(h), 72, name, NewDocumentMode.RGB, fill || DocumentFill.WHITE, 1, BitsPerChannelType.EIGHT);
}

/// Rectangle / ellipse selections (pixel coordinates).
function selectRect(l, t, r, b) {
    app.activeDocument.selection.select([[l, t], [r, t], [r, b], [l, b]]);
}

function selectEllipse(l, t, r, b) {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putProperty(cTID("Chnl"), cTID("fsel"));
    d.putReference(cTID("null"), ref);
    var e = new ActionDescriptor();
    e.putUnitDouble(cTID("Top "), cTID("#Pxl"), t);
    e.putUnitDouble(cTID("Left"), cTID("#Pxl"), l);
    e.putUnitDouble(cTID("Btom"), cTID("#Pxl"), b);
    e.putUnitDouble(cTID("Rght"), cTID("#Pxl"), r);
    d.putObject(cTID("T   "), cTID("Elps"), e);
    d.putBoolean(cTID("AntA"), true);
    executeAction(cTID("setd"), d, DialogModes.NO);
}

function fillSel(c) {
    app.activeDocument.selection.fill(solid(c));
    app.activeDocument.selection.deselect();
}

function fillRect(l, t, r, b, c) { selectRect(l, t, r, b); fillSel(c); }
function fillEllipse(l, t, r, b, c) { selectEllipse(l, t, r, b); fillSel(c); }

/// Gradient descriptor from our own colour stops: [[position 0..1, [r,g,b]], ...].
function gradDesc(stops, name) {
    var g = new ActionDescriptor();
    g.putString(cTID("Nm  "), name || "oracle");
    g.putEnumerated(cTID("GrdF"), cTID("GrdF"), cTID("CstS"));
    g.putDouble(cTID("Intr"), 4096);
    var cl = new ActionList();
    for (var i = 0; i < stops.length; i++) {
        var s = new ActionDescriptor();
        s.putObject(cTID("Clr "), cTID("RGBC"), rgbDesc(stops[i][1]));
        s.putEnumerated(cTID("Type"), cTID("Clry"), cTID("UsrS"));
        s.putInteger(cTID("Lctn"), Math.round(stops[i][0] * 4096));
        s.putInteger(cTID("Mdpn"), 50);
        cl.putObject(cTID("Clrt"), s);
    }
    g.putList(cTID("Clrs"), cl);
    var tl = new ActionList();
    for (var j = 0; j < 2; j++) {
        var t = new ActionDescriptor();
        t.putUnitDouble(cTID("Opct"), cTID("#Prc"), 100);
        t.putInteger(cTID("Lctn"), j * 4096);
        t.putInteger(cTID("Mdpn"), 50);
        tl.putObject(cTID("TrnS"), t);
    }
    g.putList(cTID("Trns"), tl);
    return g;
}

/// Draw a gradient (in the selection, or the whole layer) with the gradient tool, no dither.
function gradient(x0, y0, x1, y1, stops, type) {
    var d = new ActionDescriptor();
    var f = new ActionDescriptor();
    f.putUnitDouble(cTID("Hrzn"), cTID("#Pxl"), x0);
    f.putUnitDouble(cTID("Vrtc"), cTID("#Pxl"), y0);
    d.putObject(cTID("From"), cTID("Pnt "), f);
    var t = new ActionDescriptor();
    t.putUnitDouble(cTID("Hrzn"), cTID("#Pxl"), x1);
    t.putUnitDouble(cTID("Vrtc"), cTID("#Pxl"), y1);
    d.putObject(cTID("T   "), cTID("Pnt "), t);
    d.putEnumerated(cTID("Type"), cTID("GrdT"), cTID(type || "Lnr "));
    d.putBoolean(cTID("Dthr"), false);
    d.putBoolean(cTID("UsMs"), true);
    d.putObject(cTID("Grad"), cTID("Grdn"), gradDesc(stops));
    executeAction(cTID("Grdn"), d, DialogModes.NO);
}

var SPECTRUM = [[0, [255, 0, 0]], [1 / 6, [255, 255, 0]], [2 / 6, [0, 255, 0]], [3 / 6, [0, 255, 255]], [4 / 6, [0, 0, 255]], [5 / 6, [255, 0, 255]], [1, [255, 0, 0]]];

function newLayer(name) {
    var l = app.activeDocument.artLayers.add();
    l.name = name;
    return l;
}

/// A colourful test motif on the active (pixel) layer: spectrum band, ramps and hard-edged shapes.
function motif(w, h) {
    selectRect(0, 0, w, Math.round(h * 0.4));
    gradient(0, 0, w, 0, SPECTRUM);
    app.activeDocument.selection.deselect();
    selectRect(0, Math.round(h * 0.4), w, Math.round(h * 0.55));
    gradient(0, 0, w, 0, [[0, [0, 0, 0]], [1, [255, 255, 255]]]);
    app.activeDocument.selection.deselect();
    fillRect(Math.round(w * 0.08), Math.round(h * 0.62), Math.round(w * 0.42), Math.round(h * 0.92), [20, 90, 200]);
    fillEllipse(Math.round(w * 0.5), Math.round(h * 0.6), Math.round(w * 0.92), Math.round(h * 0.95), [240, 160, 30]);
    fillRect(Math.round(w * 0.22), Math.round(h * 0.7), Math.round(w * 0.3), Math.round(h * 0.98), [250, 250, 250]);
}

/// Shapes on a transparent layer (for layer styles: hard alpha edges, a hole and a thin bar).
function styleShapes(w, h, c) {
    fillRect(Math.round(w * 0.12), Math.round(h * 0.15), Math.round(w * 0.55), Math.round(h * 0.55), c);
    fillEllipse(Math.round(w * 0.45), Math.round(h * 0.4), Math.round(w * 0.9), Math.round(h * 0.88), c);
    selectEllipse(Math.round(w * 0.6), Math.round(h * 0.55), Math.round(w * 0.75), Math.round(h * 0.72));
    app.activeDocument.selection.clear();
    app.activeDocument.selection.deselect();
    fillRect(Math.round(w * 0.1), Math.round(h * 0.75), Math.round(w * 0.4), Math.round(h * 0.79), c);
}

function convertToSmartObject() {
    executeAction(sTID("newPlacedLayer"), undefined, DialogModes.NO);
}

/// Run a filter by event id with a descriptor-building callback (smart filter on a smart object).
function filter(event, build) {
    var d = new ActionDescriptor();
    if (build) build(d);
    executeAction(tid(event), d, DialogModes.NO);
}

function unit(d, key, u, v) { d.putUnitDouble(tid(key), tid(u), v); }

function gaussian(r) { filter("GsnB", function (d) { unit(d, "Rds ", "#Pxl", r); }); }

// ---------------------------------------------------------------------------------------------
// Saving
// ---------------------------------------------------------------------------------------------

var RESULTS = [];

function save(doc, rel) {
    var f = new File(OUT + "/" + rel);
    if (!f.parent.exists) f.parent.create();
    var o = new PhotoshopSaveOptions();
    o.alphaChannels = true;
    o.annotations = true;
    o.layers = true;
    o.spotColors = true;
    // No ICC profiles in the files: we never redistribute vendor profiles; untagged data is
    // interpreted with the same defaults on both sides of the comparison.
    o.embedColorProfile = false;
    doc.saveAs(f, o, true, Extension.LOWERCASE);
}

/// Run one case: `fn(doc?)` builds and returns the document; it is saved as `rel` and closed.
function run(rel, fn) {
    if (FILTER && !FILTER.test(rel)) return;
    var doc = null;
    try {
        doc = fn();
        save(doc, rel);
        RESULTS.push("ok    " + rel);
    } catch (e) {
        if (/^SKIP/.test(e.message)) RESULTS.push("skip  " + rel + ": " + e.message);
        else RESULTS.push("FAIL  " + rel + ": " + e + (e.line ? " (line " + e.line + ")" : ""));
    }
    try {
        if (doc) doc.close(SaveOptions.DONOTSAVECHANGES);
    } catch (e2) {}
    // Close anything a failed case left open (smart object edits etc.).
    while (app.documents.length > OPEN_AT_START) {
        try { app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); } catch (e3) { break; }
    }
}

var OPEN_AT_START = app.documents.length;

// ---------------------------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------------------------

/// A smart object holding the motif on a white background layer, ready for smart filters.
var SF = 128; // smart-filter documents are SF x SF (embedded smart objects double the file size)

function smartBase(name) {
    var doc = newDoc(name, SF, SF, DocumentFill.WHITE);
    var l = newLayer("motif");
    motif(SF, SF);
    l.opacity = 100;
    convertToSmartObject();
    return doc;
}

/// Levels/Curves "composite" channel: Lab has none, its first channel is Lightness.
function compositeChannel() {
    return app.documents.length && app.activeDocument.mode === DocumentMode.LAB ? "Lght" : "Cmps";
}

function levelsDesc(d, lo, hi, gamma, olo, ohi) {
    var l = new ActionList();
    var a = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(cTID("Chnl"), cTID("Chnl"), cTID(compositeChannel()));
    a.putReference(cTID("Chnl"), ref);
    var inp = new ActionList();
    inp.putInteger(lo);
    inp.putInteger(hi);
    a.putList(cTID("Inpt"), inp);
    a.putDouble(cTID("Gmm "), gamma);
    if (olo !== undefined) {
        var out = new ActionList();
        out.putInteger(olo);
        out.putInteger(ohi);
        a.putList(cTID("Otpt"), out);
    }
    l.putObject(cTID("LvlA"), a);
    d.putList(cTID("Adjs"), l);
}

/// Curves on the composite channel (and optionally per channel): points [[in, out], ...].
function curvesDesc(d, pts, perChannel) {
    var l = new ActionList();
    function one(ch, p) {
        var a = new ActionDescriptor();
        var ref = new ActionReference();
        ref.putEnumerated(cTID("Chnl"), cTID("Chnl"), cTID(ch));
        a.putReference(cTID("Chnl"), ref);
        var cl = new ActionList();
        for (var i = 0; i < p.length; i++) {
            var pt = new ActionDescriptor();
            pt.putDouble(cTID("Hrzn"), p[i][0]);
            pt.putDouble(cTID("Vrtc"), p[i][1]);
            cl.putObject(cTID("Pnt "), pt);
        }
        a.putList(cTID("Crv "), cl);
        l.putObject(cTID("CrvA"), a);
    }
    one(compositeChannel(), pts);
    if (perChannel) for (var k in perChannel) one(k, perChannel[k]);
    d.putList(cTID("Adjs"), l);
}

function selectFilterMask() {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(cTID("Chnl"), cTID("Chnl"), sTID("filterMask"));
    d.putReference(cTID("null"), ref);
    d.putBoolean(cTID("MkVs"), false);
    executeAction(cTID("slct"), d, DialogModes.NO);
}

function selectComposite() {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putEnumerated(cTID("Chnl"), cTID("Chnl"), cTID("RGB "));
    d.putReference(cTID("null"), ref);
    executeAction(cTID("slct"), d, DialogModes.NO);
}

/// Blend mode / opacity of smart filter `index` (1-based, bottom-up as in the Layers panel).
function setFilterBlend(index, mode, opacity) {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putIndex(sTID("filterFX"), index);
    ref.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"));
    d.putReference(cTID("null"), ref);
    var fx = new ActionDescriptor();
    var bo = new ActionDescriptor();
    bo.putUnitDouble(cTID("Opct"), cTID("#Prc"), opacity);
    bo.putEnumerated(cTID("Md  "), cTID("BlnM"), tid(mode));
    fx.putObject(sTID("blendOptions"), sTID("blendOptions"), bo);
    d.putObject(sTID("filterFX"), sTID("filterFX"), fx);
    executeAction(cTID("setd"), d, DialogModes.NO);
}

function smartFilterCases() {
    var S = "smart-filters/";
    function sf(name, apply) {
        run(S + name + ".psd", function () { var d = smartBase(name); apply(d); return d; });
    }
    sf("sf-none-plain", function () {});
    sf("sf-none-transformed", function (d) { d.activeLayer.resize(70, 70, AnchorPosition.MIDDLECENTER); d.activeLayer.rotate(15, AnchorPosition.MIDDLECENTER); });
    sf("sf-gaussian-blur-r4", function () { gaussian(4); });
    sf("sf-gaussian-blur-r1.5", function () { gaussian(1.5); });
    sf("sf-gaussian-blur-r20", function () { gaussian(20); });
    sf("sf-unsharp-mask-150-r2-t0", function () { filter("UnsM", function (d) { unit(d, "Amnt", "#Prc", 150); unit(d, "Rds ", "#Pxl", 2); d.putInteger(cTID("Thsh"), 0); }); });
    sf("sf-unsharp-mask-300-r5-t8", function () { filter("UnsM", function (d) { unit(d, "Amnt", "#Prc", 300); unit(d, "Rds ", "#Pxl", 5); d.putInteger(cTID("Thsh"), 8); }); });
    // Add Noise is seeded (FlRs): the smart filter re-renders identically from the stored seed.
    sf("sf-add-noise-uniform-12-seed", function () {
        filter("AdNs", function (d) { d.putEnumerated(cTID("Dstr"), cTID("Dstr"), cTID("Unfr")); unit(d, "Nose", "#Prc", 12); d.putBoolean(cTID("Mnch"), false); d.putInteger(cTID("FlRs"), 1234); });
    });
    sf("sf-add-noise-gaussian-mono-20-seed", function () {
        filter("AdNs", function (d) { d.putEnumerated(cTID("Dstr"), cTID("Dstr"), cTID("Gsn ")); unit(d, "Nose", "#Prc", 20); d.putBoolean(cTID("Mnch"), true); d.putInteger(cTID("FlRs"), 99); });
    });
    sf("sf-motion-blur-a30-d12", function () { filter("MtnB", function (d) { d.putInteger(cTID("Angl"), 30); unit(d, "Dstn", "#Pxl", 12); }); });
    sf("sf-motion-blur-a0-d25", function () { filter("MtnB", function (d) { d.putInteger(cTID("Angl"), 0); unit(d, "Dstn", "#Pxl", 25); }); });
    sf("sf-high-pass-r3", function () { filter("HghP", function (d) { unit(d, "Rds ", "#Pxl", 3); }); });
    sf("sf-median-r3", function () { filter("Mdn ", function (d) { unit(d, "Rds ", "#Pxl", 3); }); });
    sf("sf-minimum-r2", function () { filter("Mnm ", function (d) { unit(d, "Rds ", "#Pxl", 2); }); });
    sf("sf-maximum-r2", function () { filter("Mxm ", function (d) { unit(d, "Rds ", "#Pxl", 2); }); });
    sf("sf-box-blur-r5", function () { filter("boxblur", function (d) { unit(d, "Rds ", "#Pxl", 5); }); });
    sf("sf-emboss-135-3-100", function () { filter("Embs", function (d) { d.putInteger(cTID("Angl"), 135); d.putInteger(cTID("Hght"), 3); d.putInteger(cTID("Amnt"), 100); }); });
    sf("sf-mosaic-8", function () { filter("Msc ", function (d) { unit(d, "ClSz", "#Pxl", 8); }); });
    sf("sf-levels", function () { filter("Lvls", function (d) { levelsDesc(d, 20, 220, 1.4); }); });
    sf("sf-curves", function () { filter("Crvs", function (d) { curvesDesc(d, [[0, 0], [64, 40], [192, 220], [255, 255]]); }); });
    sf("sf-shadows-highlights", function () { filter("adaptCorrect", null); });
    sf("sf-filter-mask-gradient", function () {
        gaussian(6);
        selectFilterMask();
        gradient(0, 0, SF, 0, [[0, [0, 0, 0]], [1, [255, 255, 255]]]);
        selectComposite();
    });
    sf("sf-filter-mask-hard", function () {
        gaussian(6);
        selectFilterMask();
        fillRect(0, 0, SF / 2, SF, [0, 0, 0]);
        selectComposite();
    });
    sf("sf-blend-multiply-60", function () { gaussian(5); setFilterBlend(1, "Mltp", 60); });
    sf("sf-blend-screen-100", function () { filter("MtnB", function (d) { d.putInteger(cTID("Angl"), 90); unit(d, "Dstn", "#Pxl", 20); }); setFilterBlend(1, "Scrn", 100); });
    sf("sf-blend-difference-50", function () { filter("Embs", function (d) { d.putInteger(cTID("Angl"), 45); d.putInteger(cTID("Hght"), 2); d.putInteger(cTID("Amnt"), 150); }); setFilterBlend(1, "Dfrn", 50); });
    sf("sf-stack-blur-unsharp-motion", function () {
        gaussian(3);
        filter("UnsM", function (d) { unit(d, "Amnt", "#Prc", 200); unit(d, "Rds ", "#Pxl", 3); d.putInteger(cTID("Thsh"), 0); });
        filter("MtnB", function (d) { d.putInteger(cTID("Angl"), -20); unit(d, "Dstn", "#Pxl", 10); });
    });
    sf("sf-stack-blend-and-mask", function () {
        filter("Mxm ", function (d) { unit(d, "Rds ", "#Pxl", 3); });
        gaussian(4);
        setFilterBlend(2, "Ovrl", 75);
        selectFilterMask();
        selectEllipse(SF * 0.15, SF * 0.15, SF * 0.85, SF * 0.85);
        fillSel([0, 0, 0]);
        selectComposite();
    });
    sf("sf-transformed-gaussian", function (d) { gaussian(5); d.activeLayer.resize(80, 60, AnchorPosition.MIDDLECENTER); d.activeLayer.rotate(-25, AnchorPosition.MIDDLECENTER); });
    sf("sf-layer-opacity-blend", function (d) { gaussian(3); d.activeLayer.opacity = 70; d.activeLayer.blendMode = BlendMode.MULTIPLY; });
}

// ---------------------------------------------------------------------------------------------
// Layer styles: bevel & emboss, satin, glows, contours
// ---------------------------------------------------------------------------------------------

/// Our own contour curves (input/output 0..255). `smooth` marks points as smooth (not corner).
var CONTOURS = {
    linear: [[0, 0], [255, 255]],
    ramp_peak: [[0, 0], [128, 255], [255, 0]],
    double_ring: [[0, 0], [64, 255], [128, 40], [192, 255], [255, 0]],
    soft_s: [[0, 0], [70, 30], [185, 225], [255, 255]],
    step_down: [[0, 255], [100, 255], [160, 30], [255, 0]]
};

function contourDesc(name, smooth) {
    var pts = CONTOURS[name];
    var d = new ActionDescriptor();
    d.putString(cTID("Nm  "), "oracle " + name);
    var l = new ActionList();
    for (var i = 0; i < pts.length; i++) {
        var p = new ActionDescriptor();
        p.putDouble(cTID("Hrzn"), pts[i][0]);
        p.putDouble(cTID("Vrtc"), pts[i][1]);
        if (smooth === false) p.putBoolean(cTID("Cnty"), false);
        l.putObject(cTID("CrPt"), p);
    }
    d.putList(cTID("Crv "), l);
    return d;
}

/// Apply a layer-style descriptor set: {key: ActionDescriptor} (ebbl, ChFX, OrGl, IrGl, FrFX, DrSh...).
function setStyles(effects) {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putProperty(cTID("Prpr"), cTID("Lefx"));
    ref.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"));
    d.putReference(cTID("null"), ref);
    var fx = new ActionDescriptor();
    fx.putUnitDouble(cTID("Scl "), cTID("#Prc"), 100);
    for (var k in effects) fx.putObject(tid(k), tid(k), effects[k]);
    d.putObject(cTID("T   "), cTID("Lefx"), fx);
    executeAction(cTID("setd"), d, DialogModes.NO);
}

function bevel(o) {
    var d = new ActionDescriptor();
    d.putBoolean(cTID("enab"), true);
    d.putEnumerated(cTID("hglM"), cTID("BlnM"), tid(o.hiMode || "Scrn"));
    d.putObject(cTID("hglC"), cTID("RGBC"), rgbDesc(o.hiColor || [255, 255, 255]));
    unit(d, "hglO", "#Prc", o.hiOpacity === undefined ? 75 : o.hiOpacity);
    d.putEnumerated(cTID("sdwM"), cTID("BlnM"), tid(o.shMode || "Mltp"));
    d.putObject(cTID("sdwC"), cTID("RGBC"), rgbDesc(o.shColor || [0, 0, 0]));
    unit(d, "sdwO", "#Prc", o.shOpacity === undefined ? 75 : o.shOpacity);
    d.putEnumerated(cTID("bvlT"), cTID("bvlT"), tid(o.technique || "SfBL"));
    d.putEnumerated(cTID("bvlS"), cTID("BESl"), tid(o.style || "InrB"));
    d.putBoolean(cTID("uglg"), false);
    unit(d, "lagl", "#Ang", o.angle === undefined ? 120 : o.angle);
    unit(d, "Lald", "#Ang", o.altitude === undefined ? 30 : o.altitude);
    unit(d, "srgR", "#Prc", o.depth || 100);
    unit(d, "blur", "#Pxl", o.size || 8);
    d.putEnumerated(cTID("bvlD"), cTID("BESs"), tid(o.down ? "Out " : "In  "));
    d.putObject(cTID("TrnS"), cTID("ShpC"), contourDesc(o.gloss || "linear"));
    d.putBoolean(sTID("antialiasGloss"), !!o.glossAA);
    unit(d, "Sftn", "#Pxl", o.soften || 0);
    if (o.contour) {
        d.putBoolean(sTID("useShape"), true);
        d.putObject(cTID("MpgS"), cTID("ShpC"), contourDesc(o.contour));
        d.putBoolean(cTID("AntA"), !!o.contourAA);
        unit(d, "Inpr", "#Prc", o.range || 50);
    } else {
        d.putBoolean(sTID("useShape"), false);
    }
    d.putBoolean(sTID("useTexture"), false);
    return d;
}

function strokeFx(size, pos, c) {
    var d = new ActionDescriptor();
    d.putBoolean(cTID("enab"), true);
    d.putEnumerated(cTID("Styl"), cTID("FStl"), tid(pos || "OutF"));
    d.putEnumerated(cTID("PntT"), cTID("FrFl"), cTID("SClr"));
    d.putEnumerated(cTID("Md  "), cTID("BlnM"), cTID("Nrml"));
    unit(d, "Opct", "#Prc", 100);
    unit(d, "Sz  ", "#Pxl", size);
    d.putObject(cTID("Clr "), cTID("RGBC"), rgbDesc(c || [200, 60, 40]));
    return d;
}

function satin(o) {
    var d = new ActionDescriptor();
    d.putBoolean(cTID("enab"), true);
    d.putEnumerated(cTID("Md  "), cTID("BlnM"), tid(o.mode || "Mltp"));
    d.putObject(cTID("Clr "), cTID("RGBC"), rgbDesc(o.color || [20, 20, 60]));
    d.putBoolean(cTID("AntA"), !!o.aa);
    d.putBoolean(cTID("Invr"), !!o.invert);
    unit(d, "Opct", "#Prc", o.opacity || 50);
    unit(d, "lagl", "#Ang", o.angle === undefined ? 19 : o.angle);
    unit(d, "Dstn", "#Pxl", o.distance || 11);
    unit(d, "blur", "#Pxl", o.size || 14);
    d.putObject(cTID("MpgS"), cTID("ShpC"), contourDesc(o.contour || "soft_s"));
    return d;
}

function glow(o) {
    var d = new ActionDescriptor();
    d.putBoolean(cTID("enab"), true);
    d.putEnumerated(cTID("Md  "), cTID("BlnM"), tid(o.mode || "Scrn"));
    if (o.gradient) d.putObject(cTID("Grad"), cTID("Grdn"), gradDesc(o.gradient));
    else d.putObject(cTID("Clr "), cTID("RGBC"), rgbDesc(o.color || [255, 230, 120]));
    unit(d, "Opct", "#Prc", o.opacity || 85);
    d.putEnumerated(cTID("GlwT"), cTID("BETE"), tid(o.technique || "SfBL"));
    unit(d, "Ckmt", "#Prc", o.spread || 0);
    unit(d, "blur", "#Pxl", o.size || 12);
    unit(d, "Nose", "#Prc", 0);
    unit(d, "ShdN", "#Prc", 0);
    d.putBoolean(cTID("AntA"), !!o.aa);
    d.putObject(cTID("TrnS"), cTID("ShpC"), contourDesc(o.contour || "linear"));
    unit(d, "Inpr", "#Prc", o.range || 50);
    if (o.source) d.putEnumerated(cTID("glwS"), cTID("IGSr"), tid(o.source));
    return d;
}

var FX = 192;

/// White background + a transparent shape layer (blue-grey) for layer styles.
function fxBase(name, bg) {
    var doc = newDoc(name, FX, FX, DocumentFill.WHITE);
    if (bg) {
        doc.activeLayer = doc.layers[0];
        selectRect(0, 0, FX, FX);
        gradient(0, 0, FX, FX, [[0, [40, 40, 50]], [1, [200, 200, 210]]]);
        doc.selection.deselect();
    }
    newLayer("shape");
    styleShapes(FX, FX, [90, 120, 170]);
    return doc;
}

function effectCases() {
    var E = "effects/";
    function fx(name, effects, bg) {
        run(E + name + ".psd", function () { var d = fxBase(name, bg); setStyles(effects()); return d; });
    }
    var styles = { outer: "OtrB", inner: "InrB", emboss: "Embs", pillow: "PlEb", stroke: "strokeEmboss" };
    var techs = { smooth: "SfBL", "chisel-hard": "PrBL", "chisel-soft": "Slmt" };
    for (var sn in styles) {
        for (var tn in techs) {
            (function (sn, tn) {
                fx("bevel-" + sn + "-" + tn, function () {
                    var e = { ebbl: bevel({ style: styles[sn], technique: techs[tn], size: 10 }) };
                    if (sn === "stroke") e.FrFX = strokeFx(6, "OutF");
                    return e;
                });
            })(sn, tn);
        }
    }
    fx("bevel-inner-smooth-down-soften4", function () { return { ebbl: bevel({ down: true, soften: 4, size: 12 }) }; });
    fx("bevel-inner-smooth-a45-alt65-depth300", function () { return { ebbl: bevel({ angle: 45, altitude: 65, depth: 300, size: 6 }) }; });
    fx("bevel-emboss-smooth-colored-normal", function () { return { ebbl: bevel({ style: "Embs", hiMode: "Nrml", hiColor: [255, 220, 120], hiOpacity: 60, shMode: "Clr ", shColor: [60, 0, 120], shOpacity: 90, size: 9 }) }; });
    fx("bevel-inner-contour-ramp-peak", function () { return { ebbl: bevel({ size: 14, contour: "ramp_peak", range: 50 }) }; });
    fx("bevel-inner-contour-double-ring-aa-r70", function () { return { ebbl: bevel({ size: 14, contour: "double_ring", contourAA: true, range: 70 }) }; });
    fx("bevel-inner-gloss-ramp-peak", function () { return { ebbl: bevel({ size: 12, gloss: "ramp_peak" }) }; });
    fx("bevel-inner-gloss-double-ring-aa", function () { return { ebbl: bevel({ size: 12, gloss: "double_ring", glossAA: true }) }; });
    fx("bevel-pillow-chisel-hard-gloss-and-contour", function () { return { ebbl: bevel({ style: "PlEb", technique: "PrBL", size: 10, gloss: "soft_s", contour: "step_down", range: 40 }) }; });
    fx("bevel-stroke-emboss-inside-stroke", function () { return { ebbl: bevel({ style: "strokeEmboss", size: 6 }), FrFX: strokeFx(8, "InsF", [240, 200, 40]) }; });
    fx("bevel-stroke-emboss-center-stroke-chisel-soft", function () { return { ebbl: bevel({ style: "strokeEmboss", technique: "Slmt", size: 8 }), FrFX: strokeFx(10, "CtrF", [40, 180, 120]) }; });
    fx("bevel-outer-on-gradient-bg", function () { return { ebbl: bevel({ style: "OtrB", size: 10 }) }; }, true);

    fx("satin-default", function () { return { ChFX: satin({}) }; });
    fx("satin-inverted-ramp-peak-aa", function () { return { ChFX: satin({ invert: true, contour: "ramp_peak", aa: true, angle: 60, distance: 20, size: 8, opacity: 80, color: [200, 30, 30], mode: "Nrml" }) }; });
    fx("satin-linear-screen", function () { return { ChFX: satin({ contour: "linear", mode: "Scrn", color: [255, 255, 255], distance: 6, size: 20, opacity: 70 }) }; });

    fx("outer-glow-soft", function () { return { OrGl: glow({}) }; }, true);
    fx("outer-glow-precise-spread40", function () { return { OrGl: glow({ technique: "PrBL", spread: 40, size: 16 }) }; }, true);
    fx("outer-glow-contour-double-ring-r60", function () { return { OrGl: glow({ contour: "double_ring", range: 60, size: 24, aa: true }) }; }, true);
    fx("outer-glow-gradient", function () { return { OrGl: glow({ gradient: [[0, [255, 0, 0]], [0.5, [255, 255, 0]], [1, [0, 0, 255]]], size: 20, mode: "Nrml", opacity: 100 }) }; }, true);
    fx("inner-glow-edge-soft", function () { return { IrGl: glow({ source: "SrcE", color: [255, 255, 180], size: 14 }) }; });
    fx("inner-glow-center-precise-choke30", function () { return { IrGl: glow({ source: "SrcC", technique: "PrBL", spread: 30, size: 18, color: [255, 120, 0], mode: "Nrml" }) }; });
    fx("inner-glow-edge-contour-ramp-peak", function () { return { IrGl: glow({ source: "SrcE", contour: "ramp_peak", range: 50, size: 20, color: [0, 255, 200] }) }; });
    fx("combo-bevel-satin-glows-stroke", function () {
        return {
            ebbl: bevel({ size: 8, contour: "soft_s" }),
            ChFX: satin({ opacity: 40 }),
            OrGl: glow({ size: 10 }),
            IrGl: glow({ source: "SrcE", size: 8, color: [255, 255, 255], opacity: 50 }),
            FrFX: strokeFx(3, "OutF", [20, 20, 20])
        };
    }, true);
}

// ---------------------------------------------------------------------------------------------
// Type: point, paragraph, vertical, warped and path text with style runs (Action Manager)
// ---------------------------------------------------------------------------------------------

/// Fonts used (PostScript names). Arial / Times New Roman / Georgia / Courier New ship with macOS
/// and Windows (metric-compatible Liberation / Croscore fonts exist elsewhere); Source Serif is
/// OFL (Adobe's open-source family, bundled with Photoshop as a variable font) and carries the
/// OpenType features (liga, dlig, frac, onum, smcp, ordn); Hiragino Sans ships with macOS (CJK).
var FONTS = {
    arial: "ArialMT",
    arialBold: "Arial-BoldMT",
    arialItalic: "Arial-ItalicMT",
    times: "TimesNewRomanPSMT",
    georgia: "Georgia",
    georgiaItalic: "Georgia-Italic",
    courier: "CourierNewPSMT",
    sourceSerif: "SourceSerifRoman-Regular",
    hiragino: "HiraginoSans-W3"
};

var UNIT_KEYS = { size: 1, baselineShift: 1, leading: 1, firstLineIndent: 1, startIndent: 1, endIndent: 1, spaceBefore: 1, spaceAfter: 1 };
var INT_KEYS = { tracking: 1, hyphenateWordSize: 1, hyphenatePreLength: 1, hyphenatePostLength: 1, hyphenateLimit: 1, kerning: 1 };
var DOUBLE_KEYS = { horizontalScale: 1, verticalScale: 1, characterRotation: 1 };
var ENUM_KEYS = {
    autoKern: "autoKern", fontCaps: "fontCaps", baseline: "baseline", underline: "underline", strikethrough: "strikethrough",
    align: "alignmentType", baselineDirection: "baselineDirection", figureStyle: "figureStyle"
};

function putTyped(d, k, v) {
    var key = sTID(k);
    if (k === "color") {
        var c = new ActionDescriptor();
        c.putDouble(sTID("red"), v[0]);
        c.putDouble(sTID("grain"), v[1]);
        c.putDouble(sTID("blue"), v[2]);
        d.putObject(key, sTID("RGBColor"), c);
    } else if (UNIT_KEYS[k]) d.putUnitDouble(key, sTID("pixelsUnit"), v);
    else if (INT_KEYS[k]) d.putInteger(key, v);
    else if (DOUBLE_KEYS[k]) d.putDouble(key, v);
    else if (ENUM_KEYS[k]) d.putEnumerated(key, sTID(ENUM_KEYS[k]), sTID(v));
    else if (typeof v === "boolean") d.putBoolean(key, v);
    else if (typeof v === "string") d.putString(key, v);
    else if (typeof v === "number") d.putDouble(key, v);
}

function styleDesc(cls, o) {
    var d = new ActionDescriptor();
    for (var k in o) if (k !== "from" && k !== "to") putTyped(d, k, o[k]);
    return d;
}

function pathPoint(x, y) {
    var p = new ActionDescriptor();
    p.putUnitDouble(sTID("horizontal"), sTID("pixelsUnit"), x);
    p.putUnitDouble(sTID("vertical"), sTID("pixelsUnit"), y);
    return p;
}

/// A path descriptor from Bézier anchors [[x, y, outDx, outDy], ...] (in-handle mirrored).
function bezierPath(anchors, closed) {
    var pl = new ActionList();
    for (var i = 0; i < anchors.length; i++) {
        var a = anchors[i];
        var p = new ActionDescriptor();
        p.putObject(sTID("anchor"), sTID("paint"), pathPoint(a[0], a[1]));
        p.putObject(sTID("forward"), sTID("paint"), pathPoint(a[0] + a[2], a[1] + a[3]));
        p.putObject(sTID("backward"), sTID("paint"), pathPoint(a[0] - a[2], a[1] - a[3]));
        p.putBoolean(sTID("smooth"), true);
        pl.putObject(sTID("pathPoint"), p);
    }
    var sp = new ActionDescriptor();
    sp.putBoolean(sTID("closedSubpath"), closed);
    sp.putList(sTID("points"), pl);
    var spl = new ActionList();
    spl.putObject(sTID("subpathsList"), sp);
    var comp = new ActionDescriptor();
    comp.putEnumerated(sTID("shapeOperation"), sTID("shapeOperation"), sTID("xor"));
    comp.putList(sTID("subpathListKey"), spl);
    var cl = new ActionList();
    cl.putObject(sTID("pathComponent"), comp);
    var pc = new ActionDescriptor();
    pc.putList(sTID("pathComponents"), cl);
    return pc;
}

function circleAnchors(cx, cy, r) {
    var k = 0.5522847498 * r;
    return [[cx - r, cy, 0, -k], [cx, cy - r, k, 0], [cx + r, cy, 0, k], [cx, cy + r, -k, 0]];
}

/// Create a text layer.
///   text: string ("\r" separates paragraphs)
///   at: [x, y] origin (point text: baseline start; box/path: shapes are relative to it)
///   box: [w, h] paragraph text box; path: [anchors, closed] text on a path; vertical: bool
///   style: base character style; runs: [{from, to, ...style}] overrides on top of `style`
///   para: base paragraph style; paras: [{from, to, ...}] overrides
///   warp: {style, value, h, v, vertical}; aa: antiAlias type; name: layer name
function makeText(o) {
    var doc = app.activeDocument;
    var W = doc.width.as("px"), H = doc.height.as("px");
    var md = new ActionDescriptor();
    var r = new ActionReference();
    r.putClass(sTID("textLayer"));
    md.putReference(cTID("null"), r);
    var tk = new ActionDescriptor();
    tk.putString(sTID("textKey"), o.text);
    var cp = new ActionDescriptor();
    cp.putUnitDouble(sTID("horizontal"), sTID("percentUnit"), 100 * o.at[0] / W);
    cp.putUnitDouble(sTID("vertical"), sTID("percentUnit"), 100 * o.at[1] / H);
    tk.putObject(sTID("textClickPoint"), sTID("paint"), cp);
    tk.putEnumerated(sTID("antiAlias"), sTID("antiAliasType"), sTID(o.aa || "antiAliasSharp"));
    var orient = o.vertical ? "vertical" : "horizontal";
    tk.putEnumerated(sTID("orientation"), sTID("orientation"), sTID(orient));
    if (o.warp) {
        var w = new ActionDescriptor();
        w.putEnumerated(sTID("warpStyle"), sTID("warpStyle"), sTID(o.warp.style));
        w.putDouble(sTID("warpValue"), o.warp.value);
        w.putDouble(sTID("warpPerspective"), o.warp.h || 0);
        w.putDouble(sTID("warpPerspectiveOther"), o.warp.v || 0);
        w.putEnumerated(sTID("warpRotate"), sTID("orientation"), sTID(o.warp.vertical ? "vertical" : "horizontal"));
        tk.putObject(sTID("warp"), sTID("warp"), w);
    }
    var sh = new ActionDescriptor();
    sh.putEnumerated(sTID("char"), sTID("char"), sTID(o.box ? "box" : o.path ? "onACurve" : "paint"));
    sh.putEnumerated(sTID("orientation"), sTID("orientation"), sTID(orient));
    var tr = new ActionDescriptor();
    var m = { xx: 1, xy: 0, yx: 0, yy: 1, tx: 0, ty: 0 };
    for (var mk in m) tr.putDouble(sTID(mk), m[mk]);
    sh.putObject(sTID("transform"), sTID("transform"), tr);
    sh.putInteger(sTID("rowCount"), 1);
    sh.putInteger(sTID("columnCount"), 1);
    sh.putBoolean(sTID("rowMajorOrder"), true);
    sh.putUnitDouble(sTID("rowGutter"), sTID("pixelsUnit"), 0);
    sh.putUnitDouble(sTID("columnGutter"), sTID("pixelsUnit"), 0);
    sh.putUnitDouble(sTID("spacing"), sTID("pixelsUnit"), 0);
    sh.putEnumerated(sTID("frameBaselineAlignment"), sTID("frameBaselineAlignment"), sTID("alignByAscent"));
    sh.putUnitDouble(sTID("firstBaselineMinimum"), sTID("pixelsUnit"), 0);
    if (o.box) {
        var b = new ActionDescriptor();
        b.putUnitDouble(cTID("Top "), cTID("#Pnt"), 0);
        b.putUnitDouble(cTID("Left"), cTID("#Pnt"), 0);
        b.putUnitDouble(cTID("Btom"), cTID("#Pnt"), o.box[1]);
        b.putUnitDouble(cTID("Rght"), cTID("#Pnt"), o.box[0]);
        sh.putObject(sTID("bounds"), cTID("Rctn"), b);
    } else {
        var base = new ActionDescriptor();
        base.putDouble(sTID("horizontal"), 0);
        base.putDouble(sTID("vertical"), 0);
        sh.putObject(sTID("base"), sTID("paint"), base);
    }
    if (o.path) sh.putObject(sTID("path"), sTID("pathClass"), bezierPath(o.path[0], o.path[1]));
    var sl = new ActionList();
    sl.putObject(sTID("textShape"), sh);
    tk.putList(sTID("textShape"), sl);

    var n = o.text.length;
    function ranges(listKey, itemKey, styleKey, base, overrides) {
        // Split [0, n) at every override boundary; later overrides win.
        var cuts = [0, n];
        var ov = overrides || [];
        for (var i = 0; i < ov.length; i++) { cuts.push(ov[i].from); cuts.push(ov[i].to); }
        cuts.sort(function (a, b) { return a - b; });
        var l = new ActionList();
        for (var j = 0; j + 1 < cuts.length; j++) {
            var a = cuts[j], z = cuts[j + 1];
            if (a === z) continue;
            var s = {};
            for (var k in base) s[k] = base[k];
            for (var q = 0; q < ov.length; q++) if (ov[q].from <= a && z <= ov[q].to) for (var k2 in ov[q]) s[k2] = ov[q][k2];
            var rd = new ActionDescriptor();
            rd.putInteger(sTID("from"), a);
            rd.putInteger(sTID("to"), z);
            rd.putObject(sTID(styleKey), sTID(styleKey), styleDesc(styleKey, s));
            l.putObject(sTID(itemKey), rd);
        }
        tk.putList(sTID(listKey), l);
    }
    var cs = { fontPostScriptName: FONTS.arial, size: 24, color: [0, 0, 0] };
    for (var sk in o.style || {}) cs[sk] = o.style[sk];
    ranges("textStyleRange", "textStyleRange", "textStyle", cs, o.runs);
    ranges("paragraphStyleRange", "paragraphStyleRange", "paragraphStyle", o.para || { align: "left" }, o.paras);
    if (o.box) {
        // `make` turns a box shape into path text, so paragraph text is created through the DOM
        // and then restyled with the style ranges built above.
        var layer = doc.artLayers.add();
        layer.kind = LayerKind.TEXT;
        var ti = layer.textItem;
        ti.kind = TextType.PARAGRAPHTEXT;
        if (o.vertical) ti.direction = Direction.VERTICAL;
        ti.contents = o.text;
        ti.position = [o.at[0], o.at[1]];
        ti.width = px(o.box[0]);
        ti.height = px(o.box[1]);
        var lr = new ActionReference();
        lr.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"));
        var cur = executeActionGet(lr).getObjectValue(cTID("Txt "));
        cur.putList(sTID("textStyleRange"), tk.getList(sTID("textStyleRange")));
        cur.putList(sTID("paragraphStyleRange"), tk.getList(sTID("paragraphStyleRange")));
        cur.putEnumerated(sTID("antiAlias"), sTID("antiAliasType"), sTID(o.aa || "antiAliasSharp"));
        var sd = new ActionDescriptor();
        var tr2 = new ActionReference();
        tr2.putEnumerated(cTID("TxLr"), cTID("Ordn"), cTID("Trgt"));
        sd.putReference(cTID("null"), tr2);
        sd.putObject(cTID("T   "), cTID("TxLr"), cur);
        executeAction(cTID("setd"), sd, DialogModes.NO);
    } else {
        md.putObject(cTID("Usng"), sTID("textLayer"), tk);
        executeAction(cTID("Mk  "), md, DialogModes.NO);
    }
    if (o.name) doc.activeLayer.name = o.name;
    return doc.activeLayer;
}

function textDoc(name, w, h) { return newDoc(name, w || 256, h || 128, DocumentFill.WHITE); }

function textCases() {
    var T = "text/";
    function tx(name, w, h, build) {
        run(T + name + ".psd", function () { var d = textDoc(name, w, h); build(d); return d; });
    }
    var PANGRAM = "Sphinx of black quartz, judge my vow.";
    var PARA = "Typography is the craft of arranging type to make written language legible, readable and appealing when displayed. Justification, hyphenation and leading shape the texture of a paragraph.";

    tx("point-arial-24", 256, 64, function () { makeText({ text: "Hello, PhotoCraft!", at: [8, 40] }); });
    tx("point-sizes-colors-runs", 320, 96, function () {
        makeText({ text: "Small Medium Large", at: [8, 64], style: { size: 14 }, runs: [{ from: 6, to: 12, size: 26, color: [200, 30, 30] }, { from: 13, to: 18, size: 44, color: [20, 90, 200] }] });
    });
    tx("point-fonts-mixed-runs", 384, 64, function () {
        makeText({ text: "Arial Times Georgia Courier", at: [8, 40], style: { size: 26 },
            runs: [{ from: 6, to: 12, fontPostScriptName: FONTS.times }, { from: 12, to: 20, fontPostScriptName: FONTS.georgia }, { from: 20, to: 27, fontPostScriptName: FONTS.courier }] });
    });
    tx("point-multiline-fonts", 320, 160, function () {
        makeText({ text: "Georgia 22 regular\rGeorgia Italic 22\rTimes New Roman 28\rCourier New 18", at: [8, 30], style: { fontPostScriptName: FONTS.georgia, size: 22 },
            runs: [{ from: 19, to: 37, fontPostScriptName: FONTS.georgiaItalic }, { from: 37, to: 56, fontPostScriptName: FONTS.times, size: 28 }, { from: 56, to: 70, fontPostScriptName: FONTS.courier, size: 18 }] });
    });
    tx("tracking-plus200", 320, 64, function () { makeText({ text: "TRACKING", at: [8, 40], style: { tracking: 200 } }); });
    tx("tracking-minus60-runs", 320, 64, function () { makeText({ text: "tight normal loose", at: [8, 40], style: { tracking: -60 }, runs: [{ from: 6, to: 12, tracking: 0 }, { from: 13, to: 18, tracking: 120 }] }); });
    var KERN = "AVATAR Wavy To. LT";
    tx("kerning-metrics", 320, 64, function () { makeText({ text: KERN, at: [8, 42], style: { size: 32, autoKern: "metricsKern" } }); });
    tx("kerning-optical", 320, 64, function () { makeText({ text: KERN, at: [8, 42], style: { size: 32, autoKern: "opticalKern" } }); });
    tx("kerning-off", 320, 64, function () { makeText({ text: KERN, at: [8, 42], style: { size: 32, autoKern: "manual" } }); });
    // Kerning "0" on part of the line, the rest Metrics. (Photoshop 2026 stores this range's
    // manual mode on characters 1..3: an Action Manager autoKern range is shifted one character
    // back in the saved Txt2. Manual kerning *values* can't be set by script at all: the
    // `kerning` key is ignored, so no case here has them.) And Optical at 24 pt (size dependent).
    tx("kerning-off-partial", 320, 64, function () { makeText({ text: KERN, at: [8, 42], style: { size: 32 }, runs: [{ from: 2, to: 5, autoKern: "manual" }] }); });
    tx("kerning-optical-24pt", 320, 48, function () { makeText({ text: KERN, at: [8, 32], style: { size: 24, autoKern: "opticalKern" } }); });
    tx("leading-manual-30-paragraph", 256, 192, function () { makeText({ text: PARA, at: [8, 8], box: [240, 176], style: { size: 14, autoLeading: false, leading: 30 } }); });
    tx("leading-mixed-runs-point", 256, 160, function () {
        makeText({ text: "auto leading line\rleading 40 line\rleading 12 line", at: [8, 30], style: { size: 18 }, runs: [{ from: 18, to: 33, autoLeading: false, leading: 40 }, { from: 34, to: 49, autoLeading: false, leading: 12 }] });
    });
    tx("baseline-shift-runs", 320, 96, function () { makeText({ text: "base up down base", at: [8, 56], style: { size: 26 }, runs: [{ from: 5, to: 7, baselineShift: 10 }, { from: 8, to: 12, baselineShift: -8, color: [0, 120, 60] }] }); });
    tx("faux-bold-italic-runs", 320, 64, function () {
        makeText({ text: "regular faux-bold faux-italic both", at: [6, 40], style: { size: 20 },
            runs: [{ from: 8, to: 17, syntheticBold: true }, { from: 18, to: 29, syntheticItalic: true }, { from: 30, to: 34, syntheticBold: true, syntheticItalic: true }] });
    });
    tx("caps-all-caps", 320, 64, function () { makeText({ text: "All Caps Applied", at: [8, 40], style: { fontCaps: "allCaps" } }); });
    tx("caps-small-caps-faux-arial", 320, 64, function () { makeText({ text: "Small Caps Arial", at: [8, 40], style: { fontCaps: "smallCaps" } }); });
    tx("caps-small-caps-opentype-source-serif", 320, 64, function () { makeText({ text: "Small Caps Serif", at: [8, 40], style: { fontPostScriptName: FONTS.sourceSerif, fontCaps: "smallCaps" } }); });
    tx("super-subscript-runs", 320, 64, function () {
        makeText({ text: "E=mc2 H2O x1 TM", at: [8, 40], style: { size: 28 }, runs: [{ from: 4, to: 5, baseline: "superScript" }, { from: 7, to: 8, baseline: "subScript" }, { from: 11, to: 12, baseline: "subScript" }, { from: 13, to: 15, baseline: "superScript" }] });
    });
    tx("align-point-left-center-right", 256, 128, function () {
        makeText({ text: "left aligned", at: [128, 30], style: { size: 18 }, para: { align: "left" }, name: "left" });
        makeText({ text: "center aligned", at: [128, 70], style: { size: 18 }, para: { align: "center" }, name: "center" });
        makeText({ text: "right aligned", at: [128, 110], style: { size: 18 }, para: { align: "right" }, name: "right" });
    });
    var aligns = { "box-left": "left", "box-center": "center", "box-right": "right", "justify-left": "justifyLeft", "justify-center": "justifyCenter", "justify-right": "justifyRight", "justify-all": "justifyAll" };
    for (var an in aligns) {
        (function (an, av) {
            tx("paragraph-" + an, 256, 192, function () { makeText({ text: PARA, at: [8, 8], box: [240, 176], style: { size: 14 }, para: { align: av } }); });
        })(an, aligns[an]);
    }
    tx("paragraph-hyphenation-narrow", 160, 256, function () {
        makeText({ text: "Extraordinarily incomprehensible internationalization characteristically misunderstood telecommunications infrastructure.", at: [8, 8], box: [140, 240], style: { size: 14 },
            para: { align: "justifyLeft", hyphenate: true, hyphenateWordSize: 6, hyphenatePreLength: 2, hyphenatePostLength: 2, hyphenateLimit: 0 } });
    });
    tx("paragraph-no-hyphenation-narrow", 160, 256, function () {
        makeText({ text: "Extraordinarily incomprehensible internationalization characteristically misunderstood telecommunications infrastructure.", at: [8, 8], box: [140, 240], style: { size: 14 }, para: { align: "justifyLeft", hyphenate: false } });
    });
    tx("paragraph-indents-space-before-after", 256, 256, function () {
        makeText({ text: "First paragraph with a first-line indent of twenty pixels.\rSecond paragraph indented left and right by sixteen, with space before.\rThird paragraph: hanging indent and space after.", at: [8, 8], box: [240, 240], style: { size: 13 },
            para: { align: "left" },
            paras: [{ from: 0, to: 59, firstLineIndent: 20 }, { from: 59, to: 132, startIndent: 16, endIndent: 16, spaceBefore: 14 }, { from: 132, to: 182, startIndent: 24, firstLineIndent: -24, spaceAfter: 12, spaceBefore: 6 }] });
    });
    tx("paragraph-multi-style-runs", 256, 192, function () {
        makeText({ text: PARA, at: [8, 8], box: [240, 176], style: { size: 14, fontPostScriptName: FONTS.georgia }, para: { align: "justifyLeft" },
            runs: [{ from: 0, to: 10, size: 22, color: [180, 20, 20] }, { from: 26, to: 40, fontPostScriptName: FONTS.georgiaItalic }, { from: 60, to: 80, syntheticBold: true, color: [20, 80, 180] }, { from: 120, to: 133, fontPostScriptName: FONTS.courier }] });
    });
    tx("vertical-latin-arial", 96, 320, function () { makeText({ text: "Vertical text", at: [48, 8], vertical: true, style: { size: 24, baselineDirection: "rotated" } }); });
    tx("vertical-latin-upright", 96, 320, function () { makeText({ text: "UPRIGHT", at: [48, 8], vertical: true, style: { size: 24, baselineDirection: "crossStream" } }); });
    tx("vertical-cjk-hiragino", 96, 320, function () { makeText({ text: "縦書きの日本語テキスト", at: [48, 8], vertical: true, style: { size: 24, fontPostScriptName: FONTS.hiragino } }); });
    tx("vertical-paragraph-box", 192, 256, function () {
        makeText({ text: "縦組みの段落テキストは右から左へ行が進みます。", at: [8, 8], box: [176, 240], vertical: true, style: { size: 20, fontPostScriptName: FONTS.hiragino } });
    });
    var warps = { "warp-arc-50": { style: "warpArc", value: 50 }, "warp-flag-40": { style: "warpFlag", value: 40 }, "warp-bulge-60-persp": { style: "warpBulge", value: 60, h: 20, v: -10 },
        "warp-rise-vertical-30": { style: "warpRise", value: 30, vertical: true }, "warp-twist-35": { style: "warpTwist", value: 35 } };
    for (var wn in warps) {
        (function (wn, wv) { tx(wn, 320, 160, function () { makeText({ text: "WARPED TEXT", at: [24, 92], style: { size: 40, fontPostScriptName: FONTS.arialBold }, warp: wv }); }); })(wn, warps[wn]);
    }
    tx("path-circle", 256, 256, function () { makeText({ text: "Text set on a circular path goes all the way round", at: [0, 0], path: [circleAnchors(128, 128, 96), true], style: { size: 16 } }); });
    tx("path-wave-open", 320, 160, function () {
        makeText({ text: "Riding along an open wavy path", at: [0, 0], path: [[[16, 100, 30, -60], [160, 80, 40, 40], [304, 60, 30, -40]], false], style: { size: 20, fontPostScriptName: FONTS.georgia, color: [30, 60, 150] } });
    });
    tx("opentype-ligatures-on-off", 320, 112, function () {
        makeText({ text: "office affluent fjord", at: [8, 44], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, ligature: true }, name: "liga on" });
        makeText({ text: "office affluent fjord", at: [8, 96], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, ligature: false }, name: "liga off" });
    });
    tx("opentype-discretionary-ligatures", 320, 64, function () { makeText({ text: "Strict act of the asp", at: [8, 44], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, altligature: true } }); });
    tx("opentype-fractions", 320, 64, function () { makeText({ text: "1/2 3/4 15/16 cup", at: [8, 44], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, fractions: true } }); });
    tx("opentype-oldstyle-figures", 320, 64, function () { makeText({ text: "0123456789 in 1984", at: [8, 44], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, figureStyle: "oldStyle" } }); });
    tx("opentype-ordinals", 320, 64, function () { makeText({ text: "1st 2nd 3rd 4th No", at: [8, 44], style: { size: 30, fontPostScriptName: FONTS.sourceSerif, ordinals: true } }); });
    tx("scale-horizontal-vertical", 320, 96, function () { makeText({ text: "wide tall", at: [8, 64], style: { size: 30 }, runs: [{ from: 0, to: 4, horizontalScale: 160 }, { from: 5, to: 9, verticalScale: 170 }] }); });
    tx("underline-strikethrough", 320, 64, function () { makeText({ text: "underline strike both", at: [8, 40], style: { size: 24 }, runs: [{ from: 0, to: 9, underline: "underlineOnLeftInVertical" }, { from: 10, to: 16, strikethrough: "xHeightStrikethroughOn" }, { from: 17, to: 21, underline: "underlineOnLeftInVertical", strikethrough: "xHeightStrikethroughOn" }] }); });
    var aas = { none: "antiAliasNone", sharp: "antiAliasSharp", crisp: "antiAliasCrisp", strong: "antiAliasStrong", smooth: "antiAliasSmooth" };
    for (var aa in aas) {
        (function (aa, av) { tx("antialias-" + aa, 256, 64, function () { makeText({ text: PANGRAM, at: [6, 38], aa: av, style: { size: 17, fontPostScriptName: FONTS.times } }); }); })(aa, aas[aa]);
    }
    tx("text-with-layer-styles", 320, 96, function () {
        makeText({ text: "STYLED", at: [16, 72], style: { size: 64, fontPostScriptName: FONTS.arialBold, color: [230, 120, 30] } });
        setStyles({ ebbl: bevel({ size: 4 }), FrFX: strokeFx(2, "OutF", [40, 20, 0]) });
    });
    tx("text-on-gradient-blend-multiply", 320, 96, function (d) {
        d.activeLayer = d.layers[0];
        selectRect(0, 0, 320, 96);
        gradient(0, 0, 320, 0, SPECTRUM);
        d.selection.deselect();
        var l = makeText({ text: "Multiply 70%", at: [16, 64], style: { size: 44, fontPostScriptName: FONTS.georgia, color: [40, 40, 140] } });
        l.blendMode = BlendMode.MULTIPLY;
        l.opacity = 70;
    });
}

// ---------------------------------------------------------------------------------------------
// Adjustment layers in every colour mode and bit depth
// ---------------------------------------------------------------------------------------------

function adjLayer(cls, build, name) {
    var d = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putClass(cTID("AdjL"));
    d.putReference(cTID("null"), ref);
    var u = new ActionDescriptor();
    if (name) u.putString(cTID("Nm  "), name);
    var t = new ActionDescriptor();
    if (build) build(t);
    u.putObject(cTID("Type"), tid(cls), t);
    d.putObject(cTID("Usng"), cTID("AdjL"), u);
    executeAction(cTID("Mk  "), d, DialogModes.NO);
    return app.activeDocument.activeLayer;
}

function pct(d, key, v) { unit(d, key, "#Prc", v); }

/// Adjustment recipes: [name, class, builder]. Values are arbitrary but visible.
var ADJUSTMENTS = [
    ["levels", "Lvls", function (d) { levelsDesc(d, 15, 230, 1.3, 10, 245); }],
    ["curves", "Crvs", function (d) { curvesDesc(d, [[0, 0], [60, 35], [190, 225], [255, 255]]); }],
    ["curves-per-channel", "Crvs", function (d) { curvesDesc(d, [[0, 0], [255, 255]], { "Rd  ": [[0, 20], [128, 150], [255, 255]], "Bl  ": [[0, 0], [128, 100], [255, 230]] }); }],
    ["brightness-contrast", "BrgC", function (d) { d.putInteger(cTID("Brgh"), 25); d.putInteger(cTID("Cntr"), 30); d.putBoolean(sTID("useLegacy"), false); }],
    ["brightness-contrast-legacy", "BrgC", function (d) { d.putInteger(cTID("Brgh"), 25); d.putInteger(cTID("Cntr"), 30); d.putBoolean(sTID("useLegacy"), true); }],
    ["exposure", "Exps", function (d) { d.putDouble(cTID("Exps"), 0.8); d.putDouble(cTID("Ofst"), -0.02); d.putDouble(sTID("gammaCorrection"), 1.2); }],
    ["vibrance", "vibrance", function (d) { d.putInteger(sTID("vibrance"), 60); d.putInteger(cTID("Strt"), -15); }],
    ["hue-saturation", "HStr", function (d) {
        d.putBoolean(cTID("Clrz"), false);
        var l = new ActionList();
        var a = new ActionDescriptor();
        a.putInteger(cTID("H   "), 40);
        a.putInteger(cTID("Strt"), 25);
        a.putInteger(cTID("Lght"), -10);
        l.putObject(cTID("Hst2"), a);
        d.putList(cTID("Adjs"), l);
    }],
    ["hue-saturation-colorize", "HStr", function (d) {
        d.putBoolean(cTID("Clrz"), true);
        var l = new ActionList();
        var a = new ActionDescriptor();
        a.putInteger(cTID("H   "), 200);
        a.putInteger(cTID("Strt"), 40);
        a.putInteger(cTID("Lght"), 5);
        l.putObject(cTID("Hst2"), a);
        d.putList(cTID("Adjs"), l);
    }],
    ["color-balance", "ClrB", function (d) {
        function lvl(k, a, b, c) { var l = new ActionList(); l.putInteger(a); l.putInteger(b); l.putInteger(c); d.putList(cTID(k), l); }
        lvl("ShdL", 20, -10, 0);
        lvl("MdtL", -15, 10, 30);
        lvl("HghL", 0, 0, -20);
        d.putBoolean(cTID("PrsL"), true);
    }],
    ["black-white-tint", "BanW", function (d) {
        var v = { "Rd  ": 40, "Yllw": 60, "Grn ": 40, "Cyn ": 60, "Bl  ": 20, "Mgnt": 80 };
        for (var k in v) d.putInteger(cTID(k), v[k]);
        d.putBoolean(sTID("useTint"), true);
        d.putObject(sTID("tintColor"), cTID("RGBC"), rgbDesc([225, 211, 179]));
    }],
    ["photo-filter", "photoFilter", function (d) { d.putObject(cTID("Clr "), cTID("RGBC"), rgbDesc([236, 138, 0])); d.putInteger(cTID("Dnst"), 40); d.putBoolean(cTID("PrsL"), true); }],
    ["channel-mixer", "ChnM", function (d) {
        d.putBoolean(cTID("Mnch"), false);
        function ch(k, r, g, b, c) { var m = new ActionDescriptor(); pct(m, "Rd  ", r); pct(m, "Grn ", g); pct(m, "Bl  ", b); pct(m, "Cnst", c); d.putObject(cTID(k), cTID("ChMx"), m); }
        ch("Rd  ", 80, 30, -10, 0);
        ch("Grn ", 10, 90, 0, 5);
        ch("Bl  ", 0, 20, 70, 0);
    }],
    ["gradient-map", "GdMp", function (d) { d.putObject(cTID("Grad"), cTID("Grdn"), gradDesc([[0, [20, 10, 80]], [0.5, [220, 60, 60]], [1, [255, 240, 160]]])); d.putBoolean(cTID("Rvrs"), false); d.putBoolean(cTID("Dthr"), false); }],
    ["selective-color", "SlcC", function (d) {
        var l = new ActionList();
        function c(cls, cy, mg, ye, bk) { var a = new ActionDescriptor(); a.putEnumerated(cTID("Clrs"), cTID("Clrs"), cTID(cls)); pct(a, "Cyn ", cy); pct(a, "Mgnt", mg); pct(a, "Yllw", ye); pct(a, "Blck", bk); l.putObject(cTID("ClrC"), a); }
        c("Rds ", -30, 10, 0, 0);
        c("Bls ", 20, -20, 10, 5);
        c("Ntrl", 0, 0, -10, 0);
        d.putList(cTID("ClrC"), l);
        d.putEnumerated(cTID("Mthd"), cTID("CrcM"), cTID("Rltv"));
    }],
    ["invert", "Invr", null],
    ["posterize-4", "Pstr", function (d) { d.putInteger(cTID("Lvls"), 4); }],
    ["threshold-128", "Thrs", function (d) { d.putInteger(cTID("Lvl "), 128); }]
];

var ADJ = 96;

/// Flat base image (motif on the background layer) converted to `mode` and `bits`.
function adjBase(name, mode, bits) {
    var doc = newDoc(name, ADJ, ADJ, DocumentFill.WHITE);
    motif(ADJ, ADJ);
    if (mode === "gray") doc.changeMode(ChangeMode.GRAYSCALE);
    if (mode === "cmyk") doc.changeMode(ChangeMode.CMYK);
    if (mode === "lab") doc.changeMode(ChangeMode.LAB);
    if (bits !== 8) doc.bitsPerChannel = BITS[bits];
    return doc;
}

function adjustmentCases() {
    var combos = [["rgb", 8], ["rgb", 16], ["rgb", 32], ["gray", 8], ["gray", 16], ["gray", 32], ["cmyk", 8], ["cmyk", 16], ["lab", 8], ["lab", 16]];
    for (var c = 0; c < combos.length; c++) {
        var mode = combos[c][0], bits = combos[c][1];
        var dir = "adjustments/" + mode + bits + "/";
        // Baseline: no adjustment, just a pixel copy of the background, so mode/depth conversion
        // and merged-composite decoding are checked apart from the adjustments themselves.
        run(dir + "baseline-layer-copy.psd", function () {
            var doc = adjBase("baseline", mode, bits);
            doc.activeLayer.duplicate().name = "copy";
            return doc;
        });
        for (var i = 0; i < ADJUSTMENTS.length; i++) {
            (function (a) {
                run(dir + a[0] + ".psd", function () {
                    var doc = adjBase(a[0], mode, bits);
                    try {
                        adjLayer(a[1], a[2], a[0]);
                    } catch (e) {
                        // Not available in this mode/depth: skip the file instead of saving a no-op.
                        doc.close(SaveOptions.DONOTSAVECHANGES);
                        throw new Error("SKIP (not available in " + mode + bits + ")");
                    }
                    return doc;
                });
            })(ADJUSTMENTS[i]);
        }
    }
    var dir2 = "adjustments/rgb8/";
    run(dir2 + "masked-curves-gradient-mask-opacity60.psd", function () {
        var doc = adjBase("masked", "rgb", 8);
        var l = adjLayer("Crvs", function (d) { curvesDesc(d, [[0, 255], [255, 0]]); }, "inverted curves");
        // Adjustment layers come with a white mask: draw a gradient into it.
        selectRect(0, 0, ADJ, ADJ);
        var r = new ActionReference();
        r.putEnumerated(cTID("Chnl"), cTID("Chnl"), cTID("Msk "));
        var sd = new ActionDescriptor();
        sd.putReference(cTID("null"), r);
        sd.putBoolean(cTID("MkVs"), false);
        executeAction(cTID("slct"), sd, DialogModes.NO);
        gradient(0, 0, ADJ, 0, [[0, [0, 0, 0]], [1, [255, 255, 255]]]);
        doc.selection.deselect();
        l.opacity = 60;
        return doc;
    });
    run(dir2 + "clipped-hue-sat-blend-color.psd", function () {
        var doc = adjBase("clipped", "rgb", 8);
        newLayer("disc");
        fillEllipse(16, 16, 80, 80, [200, 200, 200]);
        var l = adjLayer("HStr", ADJUSTMENTS[8][2], "colorize clipped");
        l.grouped = true;
        l.blendMode = BlendMode.COLORBLEND;
        return doc;
    });
    run(dir2 + "stack-levels-curves-hue-posterize.psd", function () {
        var doc = adjBase("stack", "rgb", 8);
        adjLayer("Lvls", ADJUSTMENTS[0][2], "levels");
        adjLayer("Crvs", ADJUSTMENTS[1][2], "curves");
        adjLayer("HStr", ADJUSTMENTS[7][2], "hue/sat");
        adjLayer("Pstr", function (d) { d.putInteger(cTID("Lvls"), 6); }, "posterize");
        return doc;
    });
}

// ---------------------------------------------------------------------------------------------
// Layer comps
// ---------------------------------------------------------------------------------------------

/// Layer comps captured with Appearance (blend mode, opacity, fill opacity, layer style),
/// Position and Visibility (positions are left alone: a scripted translate is recorded only as
/// the effects reference point `FXRefPoint`, and applying the comp does not move the layer). Each comp is a different look of the same two layers; the file
/// is saved once per comp with that comp applied, so its merged composite is Photoshop's own
/// rendering of the comp, and its 1065 resource / `cmls` items hold every comp's settings.
var LC = 96;

function layerCompDoc() {
    var doc = newDoc("layer comps", LC, LC, DocumentFill.WHITE);
    gradient(0, 0, LC, LC, [[0, [40, 120, 200]], [1, [250, 230, 120]]]);
    var a = newLayer("square");
    fillRect(12, 12, 60, 60, [210, 50, 40]);
    var b = newLayer("disc");
    fillEllipse(36, 36, 84, 84, [40, 170, 90]);
    return { doc: doc, a: a, b: b };
}

/// The comps of layerCompDoc(): a function per comp that sets the layers to that look.
var LAYER_COMPS = [
    ["plain", function (s) {
        s.a.blendMode = BlendMode.NORMAL; s.a.opacity = 100; s.a.fillOpacity = 100;
        s.b.blendMode = BlendMode.NORMAL; s.b.opacity = 100; s.b.fillOpacity = 100;
    }],
    ["multiply-screen", function (s) {
        s.a.blendMode = BlendMode.MULTIPLY; s.a.opacity = 40; s.a.fillOpacity = 100;
        s.b.blendMode = BlendMode.SCREEN; s.b.opacity = 100; s.b.fillOpacity = 70;
    }],
    ["styled-difference", function (s) {
        s.doc.activeLayer = s.a;
        setStyles({ FrFX: strokeFx(4, "OutF", [20, 20, 160]) });
        s.a.blendMode = BlendMode.NORMAL; s.a.opacity = 80; s.a.fillOpacity = 30;
        s.b.blendMode = BlendMode.DIFFERENCE; s.b.opacity = 60; s.b.fillOpacity = 100;
    }],
    ["hidden-disc", function (s) {
        s.a.blendMode = BlendMode.OVERLAY; s.a.opacity = 100; s.a.fillOpacity = 100;
        s.b.visible = false;
    }]
];

function clearStyle(layer) {
    app.activeDocument.activeLayer = layer;
    try {
        var d = new ActionDescriptor();
        var ref = new ActionReference();
        ref.putEnumerated(cTID("Lyr "), cTID("Ordn"), cTID("Trgt"));
        d.putReference(cTID("null"), ref);
        executeAction(sTID("disableLayerStyle"), d, DialogModes.NO);
    } catch (e) {}
}

function layerCompCases() {
    for (var applied = 0; applied < LAYER_COMPS.length; applied++) {
        (function (applied) {
            run("layer-comps/appearance-applied-" + LAYER_COMPS[applied][0] + ".psd", function () {
                var s = layerCompDoc();
                for (var i = 0; i < LAYER_COMPS.length; i++) {
                    // Every comp starts from the same baseline: no style, both layers visible.
                    clearStyle(s.a);
                    s.b.visible = true;
                    LAYER_COMPS[i][1](s);
                    s.doc.layerComps.add(LAYER_COMPS[i][0], "", true, true, true);
                }
                s.doc.layerComps[applied].apply();
                return s.doc;
            });
        })(applied);
    }
}

// ---------------------------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------------------------

var savedPrefs = {
    ruler: app.preferences.rulerUnits,
    type: app.preferences.typeUnits,
    compat: app.preferences.maximizeCompatibility,
    dialogs: app.displayDialogs
};
app.preferences.rulerUnits = Units.PIXELS;
app.preferences.typeUnits = TypeUnits.PIXELS;
app.preferences.maximizeCompatibility = QueryStateType.ALWAYS;
app.displayDialogs = DialogModes.NO;
try {
    smartFilterCases();
    effectCases();
    textCases();
    adjustmentCases();
    layerCompCases();
} finally {
    app.preferences.rulerUnits = savedPrefs.ruler;
    app.preferences.typeUnits = savedPrefs.type;
    app.preferences.maximizeCompatibility = savedPrefs.compat;
    app.displayDialogs = savedPrefs.dialogs;
}
RESULTS.join("\n");
