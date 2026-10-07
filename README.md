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
[Size guidance](#size-guidance) · [`photoshop/`](#photoshop-photoshop-oracle-psds) ·
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
cargo xtask corpus --all         # every corpus: this repo's sets plus psd-tools, ag-psd and PngSuite
cargo xtask corpus               # list where each corpus lives and which commit is pinned
cargo xtask test-corpus          # fetch everything, then run every corpus test
```

- **Where the files land:** `corpus/photoshop/` in the PhotoCraft checkout. It is gitignored and
  never committed. A complete, verified copy is left alone, so running the command again is cheap.
- **The pin:** `PHOTOCRAFT_CORPUS_COMMIT` in
  [`xtask/src/corpus_pins.rs`](https://github.com/storytold/photocraft/blob/main/xtask/src/corpus_pins.rs) (every
  corpus pin is in that one file). The manifest the download is checked against is
  `xtask/photoshop-corpus.sha256`.
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
   `find photoshop -name '*.psd' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS`
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
find photoshop -name '*.psd' | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS
```

The script prints one line per file:

- `ok`: generated and saved
- `skip`: not available in that mode or depth
- `FAIL`: something went wrong

The output has the same content each time but is not identical byte for byte, because Photoshop
writes fresh document ids, timestamps and XMP. So regenerate only when the set itself changes,
then follow the [pinning workflow](#pinning-workflow).

## Provenance

Everything here is original work by the PhotoCraft contributors. The files are generated from
scratch by the scripts in `tools/`, with Adobe Photoshop used only as the authoring tool.
Photoshop's output was observed clean-room: none of its code, presets, patterns, styles,
contours, ICC profiles or other assets are included. Fonts are referenced by name only. The files
contain no personal or private images and no copyrighted material we don't own.

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
scripts in [`tools/`](tools/), with Adobe Photoshop as the authoring tool (see
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
