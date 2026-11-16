#!/bin/bash
# Runs one of the skill's Python scripts with the Python in ~/reel-studio, the folder the MAKERS gifts share.
#   bash run.sh <script.py> [arguments]
# Prints "NO TOOLS" and exits 3 when that Python is not installed yet (then: install-tools.sh base).
# REEL_STUDIO overrides the folder, for tests only.
STUDIO="${REEL_STUDIO:-$HOME/reel-studio}"
PY="$STUDIO/.venv/bin/python"; [ -x "$PY" ] || PY="$STUDIO/.venv/Scripts/python.exe"
[ -x "$PY" ] || { echo "NO TOOLS"; exit 3; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="$1"; shift
export PYTHONIOENCODING=utf-8 HF_HUB_DISABLE_XET=1
exec "$PY" "$HERE/$S" "$@"
