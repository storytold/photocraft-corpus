#!/bin/sh
# Regenerate gimp/ with GIMP 3.2, headless (no window, no profile changes).
# Needs the GIMP Flatpak (org.gimp.GIMP) by default; GIMP="<command>" picks another build, for
# example GIMP=gimp for a distribution package.
# Usage: tools/gimp-xcf/generate.sh      Afterwards refresh SHA256SUMS (see README.md).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
gimp=${GIMP:-"flatpak run --command=gimp org.gimp.GIMP"}
cd "$root"
mkdir -p gimp
# shellcheck disable=SC2086  # $gimp is a command line, split on purpose
exec $gimp -i -n --batch-interpreter=python-fu-eval \
  -b "exec(open('tools/gimp-xcf/xcf_fixtures.py').read())" -b 'quit()'
