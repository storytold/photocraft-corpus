<p align="center">
  <a href="https://getartcraft.com/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/brand/artcraft-logo-white.svg">
      <img alt="ArtCraft" src="docs/brand/artcraft-logo.svg" width="200">
    </picture>
  </a>
</p>

<h1 align="center">PhotoCraft Corpus</h1>

<p align="center">
  <a href="https://sonarcloud.io/project/overview?id=storytold_photocraft-corpus"><img alt="Scanned by SonarCloud" src="https://img.shields.io/badge/Scanned_by-SonarCloud-4b9fd5?style=flat-square&logo=sonarqubecloud&logoColor=white"></a>
</p>

<p align="center">
  <b>Real-file test oracles for PhotoCraft and the Crafting Apps.</b>
</p>

<p align="center">
  PSDs made in Adobe Photoshop by our own scripts. Each file stores Photoshop's rendering of
  itself, and PhotoCraft's tests compare their output with that rendering, file by file.
  Pinned by commit and verified with sha256.
</p>

<p align="center">
  <img alt="License: MIT OR Apache-2.0" src="https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue">
  <img alt="Files: 258 PSDs" src="https://img.shields.io/badge/photoshop-258%20PSDs-2f7bf5">
</p>

<p align="center">
  <a href="https://discord.gg/artcraft"><img alt="Join the ArtCraft community on Discord" src="https://img.shields.io/badge/Join%20us%20on%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" height="40"></a>
</p>

<p align="center">
  <a href="https://github.com/storytold/photocraft"><b>PhotoCraft on GitHub</b></a> ·
  <a href="https://getartcraft.com/apps/photocraft">PhotoCraft on getartcraft.com</a> ·
  <a href="https://getartcraft.com/">ArtCraft</a> ·
  <a href="https://getartcraft.com/apps">All Crafting Apps</a>
</p>

> [!NOTE]
> **ArtCraft is a community of artists from all walks of life.** Painters, photographers,
> filmmakers, illustrators, designers, animators, hobbyists, and people who picked up a pencil
> last week. If you make things, you're one of us. **[Come say hi on Discord](https://discord.gg/artcraft).**

**Contents:** [What this is](#what-this-is) · [Using this from PhotoCraft](#using-this-from-photocraft) · [Local layout](#local-layout-authoring-clone-consuming-copy-local-mode) ·
[Layout](#layout) · [Fetching](#fetching) · [Verifying](#verifying) ·
[Adding or regenerating files](#adding-or-regenerating-files) · [Pinning](#pinning-workflow) ·
[Size guidance](#size-guidance) · [`photoshop/`](#photoshop-photoshop-oracle-psds) · [`gimp/`](#gimp-gimp-xcf-oracles) ·
[Provenance](#provenance) · [The Crafting Apps](#the-crafting-apps) · [License and credits](#license-and-credits)

## What this is

These are real-file oracles for [PhotoCraft](https://github.com/storytold/photocraft) and for any
Crafting App that reads PSD. Each test file is a document together with the output of the
application that made it. A PSD saved with **Maximize Compatibility** holds a merged composite,
which is Photoshop's own rendering of its layer stack. Importers, compositors, filter stacks and
text engines are checked against that composite.

The files live here, outside the app repositories, so the apps' git history stays small. Apps
never track this repository's `main`. Each app fetches it at a **pinned commit** and checks every
file against a sha256 manifest, so test results can't change without a reviewed pin bump.

## Using this from PhotoCraft

PhotoCraft is the primary consumer. From a PhotoCraft checkout:

```sh
cargo xtask corpus --photoshop   # this repo's photoshop/ at the pinned commit -> corpus/photoshop
cargo xtask corpus --gimp        # this repo's gimp/ at its pinned commit -> corpus/gimp
cargo xtask corpus --all         # every corpus: this repo's sets plus psd-tools, ag-psd and PngSuite
cargo xtask corpus               # list where each corpus lives and which commit is pinned
cargo xtask test-corpus          # fetch everything, then run every corpus test
```

- **Where the files land:** `corpus/photoshop/` in the PhotoCraft checkout. It is gitignored and
  never committed. A complete, verified copy is left alone, so running the command again is cheap.
- **The pin:** `PHOTOCRAFT_CORPUS_COMMIT` in
  [`xtask/src/corpus_pins.rs`](https://github.com/storytold/photocraft/blob/main/xtask/src/corpus_pins.rs) (every
  corpus pin is in that one file). The manifest the download is checked against is
  `xtask/photoshop-corpus.sha256`. `gimp/` has its own pin (`PHOTOCRAFT_CORPUS_GIMP_COMMIT`) and manifest
  (`xtask/gimp-corpus.sha256`), fetched by `cargo xtask corpus --gimp`, so the two sets move independently.
- **Bumping the pin:** in a PhotoCraft PR, set `PHOTOCRAFT_CORPUS_COMMIT` to the new commit here, then run
  `cargo xtask corpus --photoshop --update-manifest` and commit the manifest diff. Re-run the
  tests below and raise their floors if more files pass (see [Pinning](#pinning-workflow)).
- **Tests that use the files** sit behind PhotoCraft's `corpus` cargo feature, so plain
  `cargo test` doesn't build them. `cargo xtask test-corpus` runs them:
  - `photoshop_oracle_corpus` in `crates/io/tests/corpus.rs` imports each PSD, flattens it,
    compares the result with the merged composite, and checks the PSD export round trip. It prints
    per-feature totals and pass floors.
  - `crates/engine/tests/photoshop_oracles.rs` re-renders every smart object through the
    smart-filter stack and every type layer through the text engine, then compares with the
    merged composite.

  With the feature on, a missing `corpus/photoshop` is a failure, never a silent skip.
  PhotoCraft's CI always runs these tests in its `corpus` job. That job caches `corpus/` keyed on
  the pins and manifests, so it downloads only when a pin changes, and it re-verifies the sha256
  of every file before testing.

### Local layout: authoring clone, consuming copy, local mode

| What | Where | What it is |
|---|---|---|
| **Authoring clone** | `photocraft-corpus/`, next to `photocraft/` (for example `~/dev/craft-apps/photocraft-corpus`), cloned with `git clone git@github.com:storytold/photocraft-corpus.git` | A normal git clone. Generators write here, and commits and pushes happen here. |
| **Consuming copy** | `photocraft/corpus/photoshop/` (gitignored) | A plain directory: the pinned snapshot that `cargo xtask corpus --photoshop` downloads and verifies. It is not a git repo, a submodule or a subtree. |
| **Local mode** | `cargo xtask corpus --photoshop --local`, or `cargo xtask test-corpus --local` | Copies `photoshop/` from the authoring clone (`../photocraft-corpus`, or `PHOTOCRAFT_CORPUS_REPO=<path>`) into the consuming copy instead of downloading. It warns when the clone's HEAD differs from the pin, so you can test regenerated files against PhotoCraft before pushing and bumping the pin. |

Why not a submodule or subtree? A **subtree** would put every binary back into PhotoCraft's git
history, which is exactly what this repository avoids. A **submodule** makes every contributor
deal with `git submodule update --init`, detached HEADs and stale checkouts, and CI would have to
fetch it anyway. A pinned commit plus a sha256 manifest gives the same reproducibility, and
`--local` covers the authoring loop.

## Layout

There is one top-level folder per source, i.e. per application that authored the files:

| Folder | Source | Files |
|---|---|---:|
| [`photoshop/`](#photoshop-photoshop-oracle-psds) | Adobe Photoshop 2026 (27.10), driven by [`tools/photoshop-oracles/`](tools/photoshop-oracles) | 258 |
| [`gimp/`](#gimp-gimp-xcf-oracles) | GIMP 3.2.6 and the documented historical releases, driven by [`tools/gimp-xcf/`](tools/gimp-xcf) | 106 |

The repository also contains:

- `tools/<generator>/`: the script that produced each folder, kept next to its output.
- `SHA256SUMS`: one `sha256  path` line for every corpus file, across all folders.
- `LICENSE-MIT`, `LICENSE-APACHE`, `NOTICE`: the dual licence.
- `docs/brand/`: the ArtCraft logos, which are not open source (see
  [License and credits](#license-and-credits)).

**Third-party corpora are not copied here.** PhotoCraft fetches those (PngSuite, the psd-tools
test files, ...) from their upstreams, also pinned and verified. This repository only holds
files we author ourselves.

## Fetching

From PhotoCraft, see [Using this from PhotoCraft](#using-this-from-photocraft).

Directly, for another app or for browsing:

```sh
git clone --depth 1 https://github.com/storytold/photocraft-corpus.git
# or a pinned snapshot without git (generic User-Agent, no personal details):
curl -fsSL -A Photocraft-dev -o corpus.tar.gz https://codeload.github.com/storytold/photocraft-corpus/tar.gz/<commit>
```

If another app consumes this repository, copy the pattern (not the code): pin a commit, keep your
own sha256 manifest, verify after download, and let the tests skip when the files are absent. See
the craftrules
[test-corpora standard](https://github.com/storytold/craftrules/blob/main/standards/test-corpora.md).

## Verifying

```sh
shasum -a 256 -c SHA256SUMS      # macOS; on Linux: sha256sum -c SHA256SUMS
```

Each consuming app also keeps its own copy of the manifest (PhotoCraft:
`xtask/photoshop-corpus.sha256`). A download that doesn't match is rejected, so a file can't
change behind a pin.

## Adding or regenerating files

1. **Only generator-made files.** Each file is created from scratch by a script under `tools/`
   that drives the authoring application. Hand-made, downloaded or found files don't belong here.
   That includes personal or private images and anything copyrighted that we don't own (see
   [`AGENTS.md`](AGENTS.md)).
2. **Run the generator.** For Photoshop: a Mac with Photoshop, macOS Automation permission for
   your terminal, and the [fonts](#fonts) installed. The steps are under
   [Regenerating](#regenerating). Look at the results; a contact sheet works well.
3. **Test against PhotoCraft before pushing:** from the photocraft checkout, run
   `cargo xtask test-corpus --local`, which copies from this clone and runs the corpus tests (see
   [Local layout](#local-layout-authoring-clone-consuming-copy-local-mode)).
4. **Refresh the manifest**, covering every folder:
   `find photoshop gimp -type f \( -name '*.psd' -o -name '*.xcf' -o -name '*.png' \) | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS`
5. **Make one commit per batch**, with a message that names what changed and the application
   version.

### Pinning workflow

1. Commit and push here (step 5 above).
2. Open a PR in PhotoCraft that bumps `PHOTOCRAFT_CORPUS_COMMIT` in `xtask/src/corpus_pins.rs`,
   runs `cargo xtask corpus --photoshop --update-manifest`, and commits the regenerated
   `xtask/photoshop-corpus.sha256`.
3. In the same PR, run `cargo xtask test-corpus` and raise the floors where results improved.
   Never lower a floor silently.

Commits are immutable and old pins must stay fetchable, so **never rewrite this repository's
history** (no force-push, no history rewrite).

## Size guidance

- Keep each file as small as the feature allows: 64–320 px canvases and a few layers. Remove
  padding where the authoring application allows it.
- Prefer many small single-feature files over a few big ones. A failing file should name its
  feature.
- Keep a set under about 50 MB on disk and about 10 MB packed. `photoshop/` is 50 MB raw and
  5.4 MB packed. Most of the raw size is zero padding: Photoshop pads every embedded smart object
  to 1 MiB, and that padding compresses away.
- If a set ever needs hundreds of MB, give it its own folder and its own fetch flag. Don't grow
  the default download.

## `photoshop/`: Photoshop oracle PSDs

256 small PSDs created from scratch with **Adobe Photoshop 2026 (27.10.0) on macOS** by the
ExtendScript generator in [`tools/photoshop-oracles/`](tools/photoshop-oracles). Each file is
saved with **Maximize Compatibility** turned on, so its merged composite is Photoshop's own
rendering of the layer stack. PhotoCraft compares its import and re-render against that composite.

| Directory | Files | What it exercises |
|---|---:|---|
| `smart-filters/` | 30 | Smart objects (128×128) with smart filters: Gaussian Blur (r 1.5/4/20), Unsharp Mask, Add Noise (uniform, gaussian mono), Motion Blur, High Pass, Median, Minimum, Maximum, Box Blur, Emboss, Mosaic, Levels, Curves, Shadows/Highlights; filter masks (gradient, hard, ellipse); filter blend mode/opacity; stacked filters; transformed smart objects; layer opacity/blend over a smart object |
| `effects/` | 37 | Bevel & Emboss in every style (outer, inner, emboss, pillow, stroke emboss) × technique (smooth, chisel hard, chisel soft); direction, soften, angle/altitude/depth; contours and gloss contours (with and without anti-aliasing, ranges); stroke emboss with inside/center strokes; Satin; outer glow (soft, precise + spread, contour, gradient); inner glow (edge, center + choke, contour); a combination |
| `text/` | 54 | Point and paragraph type: style runs (sizes, colours, fonts), tracking, kerning (metrics / optical / off), manual leading, baseline shift, faux bold/italic, all caps, small caps (faux and OpenType), super/subscript, point alignment, paragraph alignment and all four justifications, hyphenation on/off, indents and space before/after, horizontal/vertical scale, underline/strikethrough, vertical Latin (rotated/upright) and CJK text, a vertical paragraph, five warps, text on a closed and an open path, OpenType ligatures (on/off), discretionary ligatures, fractions, old-style figures, ordinals, the five anti-alias modes, type with layer styles and with a blend mode |
| `adjustments/<mode><bits>/` | 135 | Adjustment layers in RGB 8/16/32, Grayscale 8/16/32, CMYK 8/16 and Lab 8/16: Levels, Curves (composite and per channel), Brightness/Contrast (modern and legacy), Exposure, Vibrance, Hue/Saturation (and Colorize), Color Balance, Black & White with tint, Photo Filter, Channel Mixer, Gradient Map, Selective Color, Invert, Posterize, Threshold, where Photoshop offers them in that mode and depth. Each directory has `baseline-layer-copy.psd` with no adjustment, which tests mode/depth decoding on its own. `rgb8/` adds a masked adjustment with opacity, a clipped adjustment with a blend mode, and a stack |

File names give the feature and its parameters (`bevel-inner-chisel-soft`,
`sf-unsharp-mask-300-r5-t8`). When Photoshop doesn't offer an adjustment in a mode or depth
(for example Vibrance in Grayscale), the generator skips it rather than saving a no-op file.

All files are small (≤ 320×320). Each smart-object file is about 1.1 MB because Photoshop pads
every embedded smart object to 1 MiB with zeros, and that padding compresses away in git.

### How it was generated

- `tools/photoshop-oracles/run-jsx.sh` runs an ExtendScript file in the installed Photoshop
  through AppleScript `do javascript`, addressing Photoshop by bundle id
  (`com.adobe.Photoshop`), so any installed version works. On Photoshop 27.10,
  `do javascript file` fails with error 8800, so the script's source text is passed instead.
- The only permission needed is macOS **Automation** for your terminal → Adobe Photoshop, which
  macOS asks for on the first run. Nothing is clicked, and Photoshop doesn't need focus.
- `generate.jsx` works on one small document at a time: it saves the document into `photoshop/`
  and closes it. While it runs it sets Units to pixels, Maximize Compatibility to Always and
  dialogs off, and puts these preferences back when it finishes.
- Everything is made from scratch: generated gradients, shapes and text. The contour curves and
  gradients are our own point lists in the script. No third-party images, and no Photoshop
  presets, patterns, styles or contours.
- No ICC profiles are embedded (`embedColorProfile = false`). CMYK and Lab files were converted
  from RGB with Photoshop's default colour settings at generation time, so their pixel values
  are just data.
- Smart filters are applied through Action Manager events on a smart object. Photoshop 27.10
  accepts Levels, Curves and Shadows/Highlights as smart filters. **Add Noise** stores its
  random seed (`FlRs`), so Photoshop re-renders it identically.
- Type layers are created with Action Manager `make textLayer` descriptors that carry style and
  paragraph runs.
  - **Text on a path** uses the text-shape value `char: onACurve` plus a `path` (`pathClass`)
    whose coordinates are relative to `textClickPoint`. This value isn't documented; we read its
    name from Photoshop's own descriptor key strings, after `onPath` turned out to be wrong.
  - **Paragraph (box) text** is created through the DOM (`TextType.PARAGRAPHTEXT`) and then
    restyled with the same runs, because `make` with a `box` shape produces path text instead.
- `dump-text.jsx` (dumps a type layer's `textKey` descriptor) and `fonts.jsx` (lists fonts) are
  diagnostics.

### Fonts

The type files use these fonts, by PostScript name:

| Font | Where it comes from |
|---|---|
| `ArialMT`, `Arial-BoldMT` | Ships with macOS and Windows; Liberation Sans is metric-compatible |
| `TimesNewRomanPSMT` | Ships with macOS and Windows; Liberation Serif is metric-compatible |
| `Georgia`, `Georgia-Italic` | Ships with macOS and Windows |
| `CourierNewPSMT` | Ships with macOS and Windows; Liberation Mono is metric-compatible |
| `SourceSerifRoman-Regular` | Source Serif, SIL OFL. Photoshop bundles it as a variable font. Used for the OpenType features (liga, dlig, frac, onum, smcp, ordn) |
| `HiraginoSans-W3` | Ships with macOS; used for the CJK text |

The merged composites don't depend on fonts. Re-rendering the type layers only makes sense when
the same fonts are installed.

### Regenerating

You need a Mac with Photoshop installed. On the first run, grant your terminal Automation
access to Adobe Photoshop (System Settings › Privacy & Security › Automation). The fonts listed
above must be installed.

```sh
tools/photoshop-oracles/generate.sh               # everything (a few minutes)
tools/photoshop-oracles/generate.sh '^text/'      # or a subset, by regular expression on the path
find photoshop gimp -type f \( -name '*.psd' -o -name '*.xcf' -o -name '*.png' \) | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS
```

The script prints one line per file:

- `ok`: generated and saved
- `skip`: not available in that mode or depth
- `FAIL`: something went wrong

The output has the same content each time but is not identical byte for byte, because Photoshop
writes fresh document ids, timestamps and XMP. So regenerate only when the set itself changes,
then follow the [pinning workflow](#pinning-workflow).

## `gimp/`: GIMP XCF oracles

51 small XCF files written by **GIMP 3.2.6** and the documented historical releases,
each saved next to the author's merged preview as a PNG, plus one original linked-resource PNG
and three compressed wrappers: **106 files**. The modern Python generator and historical
ScriptFu generators live in [`tools/gimp-xcf/`](tools/gimp-xcf). Adjacent provenance records
distinguish ordinary authoring from historical graph bootstrap/rewrite observations.
PhotoCraft tests check source storage against procedural facts and imported content against
independently constructed native documents. PNG previews describe GIMP's source appearance;
they do not require a second GIMP compositor in PhotoCraft.

| File | What it exercises |
|---|---|
| `layers-8bit` | three RGB layers: offsets (one off-canvas), opacity, Multiply and Screen, a hidden layer, lock alpha, a colour tag, 300 dpi, guides |
| `groups` | a group with two children and a nested pass-through group, group opacity |
| `mask` | a layer mask painted with a gradient, one applied and one disabled |
| `gray16` | 16-bit grayscale, two layers, one with alpha |
| `float-linear` | 32-bit float linear-light RGB, values above 1.0 |
| `indexed` | a 16-colour indexed image with transparency |
| `text` | a text layer (DejaVu Sans, referenced by name only) |
| `channel` | an extra channel and a saved selection |
| `legacy-modes` | Addition, Subtract, Divide, Dodge, Burn, Grain merge, HSV Hue, HSV Value, LCH Color, Hard light, Exclusion, Linear light |
| `precision-u32-nonlinear` | RGB unsigned 32-bit endpoints and rounding boundaries, alpha, negative layer offset; precision 350 |
| `precision-half-hdr` | RGB half subnormal/normal boundaries, signed zero and finite negative/above-one samples; precision 550 |
| `precision-float-hdr` | RGB float subnormals, signed zero and finite HDR; precision 650 |
| `precision-double-gray-boundaries` | Gray double midpoint ties for f32 narrowing, double/f32 subnormals, signed zero and finite HDR; precision 750 |
| `text-unicode-fixed-markup` | Unicode multiline text, nested font resource, styled markup, fixed 120×60 box and negative offset; fonts referenced by name only |
| `paths-fractional-open-closed` | Named open and closed cubic paths with fractional, negative and off-canvas coordinates |
| `vector-solid-dashed-stroke` | Native vector layer referencing the closed path, solid fill, 3.5 px stroke, custom dash, round cap and bevel join |
| `text-unicode-modified-cache`, `vector-modified-cache` | The same semantic source after a destructive fill and replaced procedural pixels; text modified flag 2 and vector flag 1 |
| `floating-rgb-negative-offset`, `floating-channel-negative-offset` | Original 9×7 RGB/Gray floating pixels at (-2, 3), attached to a layer/channel; attachment and nonempty pixels survive stock reopen |
| `link-relative-stored-pixels` | Original 12×9 `link-source.png`, relative resource locator, cached pixels and unaffected sibling |
| `metadata-channel-view` | Unequal DPI, mm units, nonpersonal comment/Exif/XMP, selected channel, channel overlay and twelve sample points |
| `effect-*-owner` | Brightness/contrast, levels, exposure and anisotropic Gaussian blur; active effect configuration on one owner and an unaffected sibling, 65% effect opacity and explicit full-white image-global source filter masks |
| `effect-curves-per-channel-owner` | Original smooth master, red, blue and alpha curve anchors on an offset 19×13 owner, 65% effect opacity, full-white image-global filter mask and an unaffected sibling; public stock GIMP Curve API, with distinct serialized channel groups preserved by stock reopen/resave |
| `effect-stack-common-mask`, `effect-stack-distinct-masks-disabled` | Two ordered effect stages, common or distinct selection-derived masks; one disabled stage in the distinct case |
| `profile-original-{rgb,gray}-{linear,perceptual}` | Original generated ICC matrix/gamma profiles assigned to literal float samples; exact native bytes checked before save and after stock reopen |

The precision batch uses varied small sizes, 96 dpi and a layer offset of (-2, 1). Its generator
checks exact buffer bits before saving and after reopening XCF. Its PNGs are clipped previews;
stored HDR/precision data must be checked against the procedural samples and native counterparts.
`precision-u32-nonlinear.xcf.gz`, `.bz2` and `.xz` contain exactly the same XCF bytes, encoded
independently with Python's standard library (gzip without filename/time, XZ CRC64/8 MiB dictionary).
Set `PHOTOCRAFT_XCF_CASES=precision_variants` to regenerate only these eleven files. Each failed
case makes generation fail, and the batch checks creator/path metadata on its reopened sources.

The additional source batches can be selected independently with `PHOTOCRAFT_XCF_CASES`:
`native_text_paths`, `floating_relationships`, `linked_resource`, `metadata_view`, `tone_effects`, `effect_stack_masks`, `per_channel_curve_effect`
and `assigned_color_profiles` (comma-separated when selecting several). They add no input images,
font files, presets or third-party profiles. The assigned profiles are original ICC v2 data built
by the generator: requested gamma 1.8 (stored as ICC u8Fixed8 461/256), D50 white, and a deliberately synthetic RGB matrix with columns
(.6, .2, .01), (.25, .7, .1), (.1142, .1, .7149). Color samples cycle through .125/.25/.5/.75,
with alpha 1. Matrix/white XYZ values are rounded to ICC signed 15.16. The linear/perceptual source precision codes are 600/675. PNGs are GIMP source
previews; native PhotoCraft compositing and editing require separate native expectations.

The `per_channel_curve_effect` case uses only the public stock GIMP 3.2.6 Curve API. Its master, red, blue and alpha smooth anchors are distinct; the green curve is identity. The full-canvas selection is explicitly captured before clearing the live selection, so all source filter-mask samples remain white. The offset owner has procedural partial transparency. Stock reopen/resave preserves the channel groups and envelope. The PNG is a GIMP-source preview; native import tests verify declared PhotoCraft curve ordering/interpolation and alpha policies rather than requiring a GIMP spline evaluator.

These batches require publication to the upstream corpus and a consuming-app pin update
before ordinary upstream CI can fetch them. A fork branch alone does not establish pinned
upstream reproducibility; source-dependent tests must remain opt-in until that integration. A mask-attached floating probe was excluded because stock GIMP 3.2.6
drops its own floating layer on reopen; the valid floating batch covers RGB-layer and Gray-channel
attachments only. Current public APIs do not author legacy movement links or monitored-link flags.

`layers-8bit`, `groups`, `mask`, `text` and `legacy-modes` also come as `<name>-perceptual.xcf`:
the same image with every layer set to blend and composite in gamma-encoded RGB (GIMP's default is
linear light for most modes), which is the space PhotoCraft composes in. The perceptual files must
match PhotoCraft's composite closely; the default ones measure the known gap between the two.

### How it was generated

- `tools/gimp-xcf/generate.sh` runs GIMP headless (`-i -n`; the Flatpak `org.gimp.GIMP` by
  default, `GIMP="<command>"` picks another build) with the Python-Fu batch interpreter, which
  executes `xcf_fixtures.py` inside GIMP. No window opens and no preference is changed.
- Every pixel is procedural: the formulas are in the script and mirrored by PhotoCraft's test.
  The precision, floating and assigned-profile batches read back only their own newly generated files to check storage and wrapping.
  The text layer uses the font GIMP's context defaults to (DejaVu
  Sans in the baseline authoring environment, Sans-serif resolving to Verdana for the new Windows text case), referenced by name only; its PNG oracle does not depend on the font being installed.
- GIMP writes its own Exif into both files (dimensions, 300 dpi in the baseline and 96 dpi in the precision batch, and a small JPEG thumbnail in
  the PNGs). Only the assigned-profile batch embeds profiles, all generated from original numeric data in the script; the baseline float file is linear light by its precision.
- GIMP stamps a modification time into the PNGs, so regenerated files differ byte for byte.
  Regenerate only when the set itself changes, then follow the [pinning workflow](#pinning-workflow).

### Historical GIMP 2.99.18 text and vector storage

`historical-2-99-18-text-path-u8` and `historical-2-99-18-text-path-float` are
independently authored and reopened with stock GIMP 2.99.18. They are genuine XCF
version 19 files, with a 64×32 RGB canvas, editable black text at (0,0), and one
original closed two-anchor Bezier path. The source precisions are U8 nonlinear
(150) and float linear (600). Their PNG previews cover the document canvas;
the wider text layer is clipped by that canvas, and the path is not stroked.
Fonts are referenced by name only (`Sans-serif`, resolving to Cascadia Code
Regular in this authoring environment). The source uses a `GimpFont` object;
these files do not establish the older string-only font grammar or GEGL graphs.

The version-specific ordinary ScriptFu generator is
[`tools/gimp-xcf/historical_2_99_18.scm`](tools/gimp-xcf/historical_2_99_18.scm).
It saves each XCF, deletes the original image, reopens the saved file in the
same GIMP version, and queries its text, font, precision and exact path controls
before exporting the PNG. Run its documented batch command with an isolated
`GIMP3_DIRECTORY`, then run
`python3 tools/gimp-xcf/historical_png_metadata.py gimp` to remove ancillary
PNG profile/text metadata while preserving critical pixel chunks byte for byte.
The exact official installer hash, commands, source facts, PNG dimensions and
asset hashes are recorded in
[`historical_2_99_18.provenance.json`](tools/gimp-xcf/historical_2_99_18.provenance.json).

### Historical graph stock-writer cross-validation (disclosed bootstrap)

`historical-2-99-18-graph-invert-linear` and
`historical-2-99-18-graph-original-over-inverted` contain finite stored
`gegl:gegl` effects in genuine stock-resaved XCF version 20. The initial inputs
were **handcrafted documented-wire bootstrap seeds, not GIMP UI-authored files**.
Stock GIMP 2.99.18 loaded each seed through ordinary `gimp-file-load`, wrote a
new XCF through `gimp-xcf-save`, deleted the original image, reopened the saved
bytes and exported a preview after ordinary public `gimp-drawable-merge-filters`.
No development gate, internal setter or custom graph interpreter was used.

The stock writer added an empty typed `error` string absent from the seed,
normalized compositing fields and rewrote the stored coverage-mask records.
The original 8×6 RGBA owner pixels remain unchanged in the saved XCF; the
reopened preview changes all 48 pixels. Source alpha is partial: source pixel
(0,0) is `(17,13,29,64)`, while the graph previews are `(199,199,199,112)` and
`(176,176,176,148)`. This observes the source graph plus its outer filter
compositing; it does not prescribe GIMP compositing for native PhotoCraft imports.

The original bootstrap generator is
[`historical_2_99_18_graph_seed.py`](tools/gimp-xcf/historical_2_99_18_graph_seed.py),
and the ordinary stock resave/reopen generator is
[`historical_2_99_18_graph.scm`](tools/gimp-xcf/historical_2_99_18_graph.scm).
Exact commands, wire facts, full observed pixel arrays and hashes are in
[`historical_2_99_18_graph.provenance.json`](tools/gimp-xcf/historical_2_99_18_graph.provenance.json).
These qualify only the two listed finite graph forms, not arbitrary graph
evaluation, current GIMP 3.2.6 graph acceptance or UI authoring.

### GIMP 2.10.32 legacy string-font and PATHS producer witness

`historical-2-10-32-legacy-text-path.{xcf,png}` was created from scratch by
verified stock GIMP 2.10.32, saved, deleted and reopened in that same version
through ordinary ScriptFu. Its actual XCF version is0 (`gimp xcf file`), with
editable black `Legacy XCF` text at (0,0), size12pixels, a stored
`(font "Sans-serif")` string and a closed original two-anchor Bezier path in
`PROP_PATHS`23, record version3. This is independent historical producer
evidence for that font form and path record, not GDynText or every historical
PATHS version. The 64×32 PNG is the reopened canvas preview; the path is not
stroked and the wider text is clipped to the canvas.

The original version-specific generator is
[`historical_2_10_32.scm`](tools/gimp-xcf/historical_2_10_32.scm).
[`historical_2_10_32.provenance.json`](tools/gimp-xcf/historical_2_10_32.provenance.json)
records the official installer checksum, matching extracted console binary,
ordinary generation and PNG metadata-removal commands, source/readback facts
and asset hashes. The reused console is an actual x86binary; rejected optional
x86_64 GEGL extensions did not prevent the finite text/path save/reopen/export
workflow. The receipt records those warnings without claiming full runtime
qualification. No font/profile files or third-party art are included.

## Provenance

Everything here is original work by the PhotoCraft contributors. The files are generated from
scratch by the scripts in `tools/`, with Adobe Photoshop and GIMP used only as the authoring
tools. Their output was observed clean-room: none of their code, presets, patterns, styles,
contours, ICC profiles or other assets are included. Fonts are referenced by name only. The files
contain no personal or private images and no copyrighted material we don't own.


### Original named markup colors (stock GIMP 3.2.6 / Pango 1.58.2)

`gimp/text-named-markup-colors.{xcf,png}` is a newly authored 300×70 editable
text document, saved, deleted and reopened by stock GIMP. It retains original
`foreground`, `color` and `fgcolor` span aliases, named CSS/X11 colors (including
green/gray, numbered shades, spaced and mixed-case aliases) and alpha32768.
The source markup is preserved verbatim. Unknown color markup is independently
queried and rejected without replacing previous valid text. Font names only are
referenced; no fonts, external profiles or third-party assets are bundled.
`tools/gimp-xcf/named_markup_colors.py` reproduces the source and observations;
the adjacent provenance JSON records exact RGB16/RGBA16 public Pango results,
source markup, official producer hash, save/reopen facts and final asset hashes.
The PNG has only pixel-defining chunks; native PhotoCraft text/shaping and
compositing remain its own rules rather than a GIMP raster-fidelity requirement.


### Original pre-endian-fix high-depth XCFs (stock GIMP 2.9.6)

Six `gimp/historical-2-9-6-v{007,009,011}-{float,u16-asymmetric}-rle`
XCF/PNG pairs are genuinely authored by an isolated official Windows x64 GIMP
2.9.6 producer. The public ScriptFu/PDB generator creates original 8×6 RGB
partial-alpha samples, saves, deletes and reopens each image, queries all 48
actual native sample bytes and exports a preview. No input XCF or renamed
version header is involved. U16 nonlinear precision250 uses asymmetric original
values; F32 nonlinear precision650 uses original procedural colors.
`tools/gimp-xcf/historical_2_9_6.scm` reproduces the batch; its adjacent provenance
JSON records the official installer hash, all public pixel readbacks, exact wire
facts and final asset hashes. Independent bounded wire inspection confirms all
48 stored pixels equal the stock reopened public PDB bytes for every file.

These genuine pre-version12 files store little-endian high-depth samples on
this verified Windows x64 producer. The file headers and regenerated metadata
do **not** identify producer byte order: external provenance establishes it.
They must not be represented as universally little-endian historical XCFs.
Version9 uses Overlay mode23; version11 uses Normal mode28 and 64-bit offsets.
The official writer promotes version10 to11, so this batch does not qualify an
independent version10 producer. Version8 F32 zlib now has a genuine ordinary GUI Save As witness: `historical-2-9-6-v008-float-zlib.xcf`. Both independent stock reopen passes and the decoded stored bytes match all48 original samples exactly; version8 U16 producer coverage is not claimed. Stock metadata is cleared before save and the writer
regenerates nonpersonal dimensions/resolution XML; PNGs retain pixel chunks only.


### Historical XCF8 internal zlib witness

Use the verified stock GIMP 2.9.6 development runtime documented above. This is historical
format coverage, separate from stable GIMP2.10.32/3.2.6 coverage. Generate the original
v007 F32 case with `historical_2_9_6.scm`, open it in that runtime, choose **Save As**, give
it the new name `historical-2-9-6-v008-float-zlib.xcf`, enable **Save this XCF file with
better but slower compression**, and save. The public PDB has no compression selector;
this normal GUI step is deliberately recorded rather than represented as fully automated.
Do not change the precision, legacy Normal mode or original pixel data.

Load `historical_2_9_6.scm` and `historical_2_9_6_v008.scm` in the same stock runtime,
then call `(historical-v8-readback-and-preview "<saved-xcf>" "<facts-file>" "<preview-png>")`.
Sanitize only the exported PNG's ancillary chunks with the existing
`historical_png_metadata.py:sanitize` helper. The adjacent
`historical_2_9_6_v008.provenance.json` records all48 raw reopened pixel vectors,
source and preview hashes, compression2/precision650 and the external byte-order facts.
It contains no local paths. The XCF is1499bytes and its sanitized PNG is129bytes.

This qualifies this Windows F32 zlib producer case; it does not qualify every historical
producer or version10. Repeated ordinary stock public-PDB saves using modern modes
produced version11; no verified ordinary version10 authoring route is established.


## The Crafting Apps

PhotoCraft is one of the **Crafting Apps**: free, open-source creative tools from the
[ArtCraft](https://getartcraft.com/) team, each written from scratch in Rust and each able to
stand on its own.

PhotoCraft is this corpus's primary consumer. Any app in the table that reads PSD or similar
formats can use it.

| | App | What it's for | Code | Learn more |
|:-:|---|---|---|---|
| <img src="https://raw.githubusercontent.com/storytold/photocraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.photocraft.png" alt="" width="32" height="32"> | **PhotoCraft** | Image editing: layers, masks, type and real PSD files | [GitHub](https://github.com/storytold/photocraft) | [Website](https://getartcraft.com/apps/photocraft) |
| <img src="https://raw.githubusercontent.com/storytold/vectorcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.vectorcraft.png" alt="" width="32" height="32"> | **VectorCraft** | Vector illustration | [GitHub](https://github.com/storytold/vectorcraft) | [Website](https://getartcraft.com/apps/vectorcraft) |
| <img src="https://raw.githubusercontent.com/storytold/filmcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.filmcraft.png" alt="" width="32" height="32"> | **FilmCraft** | Video editing, color and sound | [GitHub](https://github.com/storytold/filmcraft) | [Website](https://getartcraft.com/apps/filmcraft) |
| <img src="https://raw.githubusercontent.com/storytold/lightcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.lightcraft.png" alt="" width="32" height="32"> | **LightCraft** | Photo library and raw development | [GitHub](https://github.com/storytold/lightcraft) | [Website](https://getartcraft.com/apps/lightcraft) |
| <img src="https://raw.githubusercontent.com/storytold/pdfcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.pdfcraft.png" alt="" width="32" height="32"> | **PdfCraft** | Reading, organizing and protecting PDFs | [GitHub](https://github.com/storytold/pdfcraft) | [Website](https://getartcraft.com/apps/pdfcraft) |
| <img src="https://raw.githubusercontent.com/storytold/effectcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.effectcraft.png" alt="" width="32" height="32"> | **EffectCraft** | Motion graphics and visual effects | [GitHub](https://github.com/storytold/effectcraft) | [Website](https://getartcraft.com/apps/effectcraft) |
| <img src="https://raw.githubusercontent.com/storytold/designcraft/main/assets/app-icon/hicolor/64x64/apps/ai.storyteller.designcraft.png" alt="" width="32" height="32"> | **DesignCraft** | Page layout and publishing | [GitHub](https://github.com/storytold/designcraft) | [Website](https://getartcraft.com/apps/designcraft) |

And [**ArtCraft**](https://getartcraft.com/) itself, our AI image and video studio for artists who want real control.

<br>

<p align="center">
  <a href="https://discord.gg/artcraft"><img alt="Join the ArtCraft community on Discord" src="https://img.shields.io/badge/Join%20us%20on%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" height="40"></a>
</p>

<h3 align="center">Come make things with us</h3>

<p align="center">
  Our Discord is where artists of every kind hang out: people who paint, shoot, draw, cut film,
  set type, and people still figuring out what they like to make. Share what you're working on,
  ask for help, tell us what's broken, or tell us what you wish these tools could do.
  Whatever your medium and however long you've been at it, you're welcome here.
</p>

<p align="center">
  <a href="https://discord.gg/artcraft"><b>discord.gg/artcraft</b></a> ·
  <a href="https://getartcraft.com/">getartcraft.com</a> ·
  <a href="https://getartcraft.com/apps">The Crafting Apps</a> ·
  <a href="https://getartcraft.com/apps/photocraft">PhotoCraft</a>
</p>

## License and credits

PhotoCraft Corpus is dual-licensed under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option.
Copyright (c) 2026 ArtCraft Team and the PhotoCraft contributors. Required notices are in [NOTICE](NOTICE).

This repository bundles no third-party assets. Every test file was generated from scratch by the
scripts in [`tools/`](tools/), with Adobe Photoshop and GIMP as the authoring tools (see
[Provenance](#provenance)). Fonts are referenced by name only.

The ArtCraft name, wordmark and logos in [`docs/brand/`](docs/brand/) are trademarks of the
ArtCraft Team and are not covered by this license. They may be used only unmodified, and only as
part of this repository and PhotoCraft, under [`docs/brand/LICENSE-brand.txt`](docs/brand/LICENSE-brand.txt).
Forks and modified versions must remove them.

<sub>Adobe, Photoshop, Illustrator, Premiere Pro, Lightroom, Acrobat, After Effects and InDesign are trademarks or registered trademarks of Adobe Inc. in the United States and/or other countries. PhotoCraft is an independent, open-source project and is not affiliated with, sponsored by or endorsed by Adobe Inc.; these names are used only to describe the workflows it is compatible with.</sub>

<p align="center">
  <a href="https://getartcraft.com/"><img alt="ArtCraft" src="docs/brand/artcraft-mark.svg" width="28"></a><br>
  <sub>Made by the <a href="https://getartcraft.com/">ArtCraft</a> team and community.</sub>
</p>
