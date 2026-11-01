# AGENTS.md: working on the PhotoCraft corpus

## 1. Read first

1. [`README.md`](README.md): what this repository is, the layout, fetching, pinning,
   regenerating, size guidance, licence.
2. The craftrules standards, especially
   [test corpora](https://github.com/storytold/craftrules/blob/main/standards/test-corpora.md) and
   [licensing](https://github.com/storytold/craftrules/blob/main/standards/licensing.md)
   (repository: https://github.com/storytold/craftrules).
3. PhotoCraft's [`AGENTS.md`](https://github.com/storytold/photocraft/blob/main/AGENTS.md):
   the clean-room rule and how its tests use these files.

## 2. Where things live

| What | Where |
|---|---|
| Authoring clone | `photocraft-corpus/` next to `photocraft/`, a normal clone of `git@github.com:storytold/photocraft-corpus.git`. Work, commit and push here. |
| Consuming copy | `photocraft/corpus/photoshop/`, `photocraft/corpus/gimp/` and `photocraft/corpus/jxl/`: gitignored plain directories filled by `cargo xtask corpus --photoshop`, `--gimp` and `--jxl`. Never edit them. |
| Local mode | `cargo xtask corpus --photoshop --local` (or `cargo xtask test-corpus --local`) copies from the authoring clone (or `PHOTOCRAFT_CORPUS_REPO=<path>`) and warns if HEAD differs from the pin. |

It is not a submodule or a subtree: a subtree would put the binaries back into PhotoCraft's
history, and submodules cause init and detached-HEAD friction for contributors.

## 3. What may be added

- **Only files we generate ourselves**, with a generator script committed under `tools/` that
  creates them from scratch in the authoring application.
- **No personal or private images.** No photographs of people, nothing from anyone's disk or
  screen, and no personal details in file contents, metadata, layer names or file names. The
  files must stay free of user paths and names: check the XMP before committing.
- **Nothing copyrighted that we don't own.** No third-party images, fonts, presets, patterns,
  styles, contours, ICC profiles or sample files, even permissively licensed ones.
  Third-party corpora are fetched by the apps from their upstream, never copied here.
  Clean-room: observe the authoring application's output only.

## 4. Adding or regenerating files, step by step

1. **Edit the generator** (`tools/photoshop-oracles/generate.jsx` for `photoshop/`,
   `tools/gimp-xcf/xcf_fixtures.py` for `gimp/`, `tools/jxl-fixtures/jxl_fixtures.py` for `jxl/`): add a case, give the file a name that states
   the feature and its parameters, and keep the canvas small.
2. **Prerequisites:**
   - a Mac with Adobe Photoshop installed;
   - macOS **Automation** permission for your terminal → Adobe Photoshop (asked on the first
     run; System Settings › Privacy & Security › Automation);
   - the fonts listed in the README.

   Don't change Photoshop's preferences by hand. The generator sets what it needs and restores
   it afterwards.

   For `gimp/`: GIMP 3.2 (the Flatpak `org.gimp.GIMP`, or `GIMP="<command>"` for another build);
   it runs headless and touches no preference.

   For `jxl/`: libjxl's `cjxl` 0.7 or newer on `PATH` and Python with Pillow.
3. **Run** `tools/photoshop-oracles/generate.sh '<regex>'` for the cases you touched (or no
   argument for everything). Every line must read `ok` or `skip`. Look at the output.
   For `gimp/`, `tools/gimp-xcf/generate.sh` regenerates the whole set (it prints one `wrote`
   line per file and `done`). For `jxl/`, `python3 tools/jxl-fixtures/jxl_fixtures.py` does (one
   line per file with its size).
4. **Test locally against PhotoCraft:** in the photocraft checkout, run
   `cargo xtask test-corpus --local -- --nocapture`. It copies `photoshop/` from this clone and
   runs every corpus test (cargo feature `corpus`) with per-file tables.
5. **Always update `SHA256SUMS`** in the same commit:
   `find photoshop gimp jxl -type f \( -name '*.psd' -o -name '*.xcf' -o -name '*.png' -o -name '*.jxl' -o -name '*.jpg' \) | LC_ALL=C sort | xargs shasum -a 256 > SHA256SUMS`
   (add any new source folder and extension to the `find`).
6. **Make one commit per batch**, with a clear message (what changed, which Photoshop version),
   then push to `main`.
7. **Bump the pin in PhotoCraft through a PR:**
   - set `PHOTOCRAFT_CORPUS_COMMIT` in `xtask/src/corpus_pins.rs`;
   - run `cargo xtask corpus --photoshop --update-manifest` and commit the manifest;
   - run `cargo xtask test-corpus` and raise the floors if more files pass.

   PhotoCraft's CI `corpus` job then fetches the new pin, since its cache key changes with the
   pin.

## 5. Rules

- **Never rewrite history:** no force-push, no amending pushed commits, no history rewriting.
  The apps pin commits, and every old pin must stay fetchable.
- **Keep files small:** a canvas of at most 320 px and a few layers per feature. Remove padding
  where the application allows it, and prefer many single-feature files. A set should stay under
  about 50 MB raw and 10 MB packed.
- **One folder per source application**, with its generator under `tools/`.
- **When fetching anything,** use the generic `Photocraft-dev` User-Agent and never put personal
  details in requests.
