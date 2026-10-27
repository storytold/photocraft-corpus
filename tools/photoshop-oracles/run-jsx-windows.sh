#!/bin/sh
# Run an ExtendScript file in Adobe Photoshop for Windows (natively from a POSIX shell such as
# Git Bash/MSYS2, or under Wine), the counterpart of run-jsx.sh (macOS, AppleScript).
# Usage: run-jsx-windows.sh <script.jsx> [arg...]
# Arguments are passed to the script as `arguments[0..]`; path arguments are converted to Windows
# paths. Prints the script's result.
#
# Photoshop has no `do javascript` on Windows: a .jsx passed on its command line is run by the
# running instance, without arguments and without returning a value. So this writes a small
# wrapper that evaluates the script with the arguments and writes its result to a file, then
# waits for that file. Start Photoshop first and leave it open (its first start takes minutes).
#   PHOTOSHOP_EXE  how to start Photoshop.exe, e.g.
#                  'wine "C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe"'
#                  (default: the newest "Adobe Photoshop*" under Program Files, natively)
#   JSX_TIMEOUT    seconds to wait for the result (default 3600)
set -eu
[ $# -ge 1 ] || { echo "usage: $0 <script.jsx> [arg...]" >&2; exit 2; }
script=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
shift

# POSIX path -> Windows path (Wine: Z:\...; MSYS2/Cygwin: cygpath).
winpath() {
    if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"
    elif command -v winepath >/dev/null 2>&1; then winepath -w "$1" 2>/dev/null
    else printf 'Z:%s' "$1" | sed 's|/|\\|g'
    fi
}
# A string as a JavaScript string literal (backslashes and quotes escaped).
jsstr() { printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; }

if [ -z "${PHOTOSHOP_EXE:-}" ]; then
    exe=$(ls -d "/c/Program Files/Adobe/Adobe Photoshop"*/Photoshop.exe 2>/dev/null | sort | tail -n 1)
    [ -n "$exe" ] || { echo "Photoshop.exe not found; set PHOTOSHOP_EXE" >&2; exit 2; }
    PHOTOSHOP_EXE="\"$exe\""
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
result="$work/result.txt"
args=""
for a in "$@"; do
    if [ -e "$a" ] || [ -e "$(dirname "$a")" ] && [ "${a#/}" != "$a" ]; then a=$(winpath "$a"); fi
    args="$args${args:+, }$(jsstr "$a")"
done
cat > "$work/run.jsx" <<EOF
#target photoshop
(function () {
    var src = new File($(jsstr "$(winpath "$script")"));
    src.encoding = "UTF-8";
    src.open("r");
    // Preprocessor lines (#target, #include) are not JavaScript inside eval.
    var code = src.read().replace(/^#.*\$/mg, "");
    src.close();
    var r;
    try { r = eval(code); } catch (e) { r = "FAIL  script: " + e + (e.line ? " (line " + e.line + ")" : ""); }
    var out = new File($(jsstr "$(winpath "$result").part"));
    out.encoding = "UTF-8";
    out.open("w");
    out.write(r === undefined ? "" : String(r));
    out.close();
    out.rename($(jsstr "$(basename "$result")"));
}).apply(null, [$args]);
EOF
eval "$PHOTOSHOP_EXE \"\$(winpath \"\$work/run.jsx\")\"" >/dev/null 2>&1 &
waited=0
while [ ! -f "$result" ]; do
    [ "$waited" -lt "${JSX_TIMEOUT:-3600}" ] || { echo "no result after ${JSX_TIMEOUT:-3600} s" >&2; exit 1; }
    sleep 2
    waited=$((waited + 2))
done
cat "$result"
echo
