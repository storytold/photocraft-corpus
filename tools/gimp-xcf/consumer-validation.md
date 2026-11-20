# XCF consumer qualification

## Revisions and scope

The asset snapshot is [photocraft-corpus `6d9daf0a`](https://github.com/Terra854/photocraft-corpus/commit/6d9daf0a00ee0495c4afdf6ead66979ec5e90974).
The consumer is [PhotoCraft `9bba4e969`](https://github.com/Terra854/photocraft/commit/9bba4e969ab4c1b3948ab96be0e86be409c5795a),
the current six-part XCF series' [part 6](https://github.com/storytold/photocraft/pull/11033).
This replaces the closed #7098 link as the applicable consumer qualification.

Local execution used Windows x86_64 and Rust 1.100.0. IO tests used ordinary release
optimization, with LTO off and 16 codegen units; Rayon used four threads and tests
ran serially. `RUST_MIN_STACK` was unset. External inputs were craft-fonts
`b076417b5880bd4154bd22f00695b1d28c6bea83` and craft-i18n
`6cda65339671e346583c84801ce0b961766b437d`; system fonts were disabled.
No dependency versions, importer algorithms, preview tolerances or corpus pins
were changed for this qualification.

The consumer uses the replacement `graph-*` XCF22 filenames and includes gzip,
bzip2 and XZ wrappers in local corpus fetching. Its source-evidence assertions
check source top-left text positions through native baseline layout coordinates,
and require the unassigned named-markup source to remain untagged. Exact original
pixels, fonts, colors, alpha, paths, masks, native edits and save/reopen assertions
remain enforced. A fresh stock GIMP 3.2.6 reopen independently confirmed that the
named-markup source is unassigned RGB/U8 nonlinear precision 150 at offset (3,4).

## Results

| Check | Result |
|---|---|
| IO XCF unit tests | 816 passed; 3 manual performance/resource probes ignored |
| Ordinary IO XCF integration tests | 53 passed; 14 source/historical checks initially ignored |
| Explicit source-evidence checks | All 13 passed, including both application-authored graphs |
| Explicit historical high-depth check | Passed for all ten genuine producer files, checking all 48 pixels per file, explicit provenance byte order, native editing and save/reopen |
| Corpus-tool pinned-path tests | 4 passed |
| Corpus-tool routing tests | 13 passed |
| Strict IO/corpus-tool Clippy, all targets | Passed |
| Scoped IO/corpus-tool formatting | Passed |

This is **900 distinct passing tests**. The explicitly enabled checks account for
all 14 normally ignored integration checks. The three manual unit performance/resource
probes were not run; repeated controls below are not counted as additional tests.
Other-format suites, full UI/browser interaction and other platforms' runtime suites
were not run for this corpus rework. Corpus Sonar scanning alone is not importer
validation.

The installed GIMP input set was compared with the snapshot's manifest: all **112**
asset files match exactly. All **370** committed corpus hashes were verified,
including all 286 unchanged baseline assets. New PNG CRCs, matching canvas sizes,
wrapper decompression and privacy-marker checks passed. These checks supplement
source-authoring and recorded producer provenance. The historical authoring
applications were not all rerun; their unmodified files retain the recorded evidence.

## Reproduction

Check out the corpus asset and consumer revisions above, and configure the pinned
font/catalogue inputs before compiling. From the PhotoCraft checkout, set
`PHOTOCRAFT_CORPUS_REPO` to the authoring corpus checkout and run:

```sh
cargo xtask corpus --gimp --local
```

Local-mode warnings about the older official pin are expected. This copies the
expanded source assets without changing the app's tracked pin or manifest.
For the local release configuration, set `CARGO_PROFILE_RELEASE_LTO=off` and
`CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16`, then run:

```sh
cargo test --release --locked -p photocraft-io --features corpus,heif --lib --test it xcf -- --nocapture
cargo test --release --locked -p photocraft-io --features corpus,heif --test it xcf_source_evidence:: -- --include-ignored --nocapture
cargo test --release --locked -p photocraft-io --features corpus,heif --test it xcf_historical_records::genuine_historical_highdepth_sources_use_explicit_provenance_order_and_editable_native_reopen -- --exact --include-ignored --nocapture
cargo test --locked -p xtask pinned::tests
cargo test --locked -p xtask corpus::tests
cargo clippy --locked -p xtask -p photocraft-io --all-targets --features photocraft-io/corpus,photocraft-io/heif -- -D warnings
cargo fmt -p xtask -p photocraft-io -- --check
```

The separate stock-GIMP graph reproduction is documented in `graph_filters.py`
and its adjacent provenance/source-facts records. Two fresh-profile runs reproduced
all four graph assets byte-for-byte. A third process reopened the committed graphs,
verified source and preview pixels, and confirmed no assigned ICC profiles.

## Local-fetch regression control

A stock corpus-tool binary from consumer parent `9f38b2870805a70b7bfbaafad2963d1c6d0e98d1`
installed 109 XCF/PNG assets and omitted all three compressed wrappers. Using the
same current IO test binary, the wrapper source-evidence test failed because the
gzip file was missing; the unchanged precision-only control passed. The corrected
loader installed all 112 assets, whose hashes matched the original snapshot again,
and the wrapper test passed. No source fixture or importer algorithm was mutated
for this control.

The expanded assets are still absent from the official upstream pin. After corpus
acceptance, a reviewed immutable GIMP pin/manifest update and removal of the relevant
source-test ignores remain necessary for ordinary upstream corpus CI to run them.
