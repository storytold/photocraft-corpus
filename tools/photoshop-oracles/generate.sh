#!/bin/sh
# Regenerate photoshop/ with the installed Adobe Photoshop (macOS; or Windows/Wine, see run-jsx-windows.sh).
# Usage: tools/photoshop-oracles/generate.sh [filter-regex]   e.g. '^text/' or 'bevel-inner'
# Prints one line per file: ok / skip (feature not available in that mode) / FAIL.
# Afterwards refresh SHA256SUMS (see README.md).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
out=$(cd "$here/../.." && pwd)/photoshop
mkdir -p "$out"
runner=run-jsx.sh
command -v osascript >/dev/null 2>&1 || runner=run-jsx-windows.sh
exec "$here/$runner" "$here/generate.jsx" "$out" "${1:-}"
