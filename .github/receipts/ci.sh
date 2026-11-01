#!/bin/bash
# Installs the receipts skill from receipts/INSTALL.md exactly as an owner's agent would (the pinned commit must
# already be on GitHub), into a home folder with Hebrew letters and a space, then runs selftest and status.
# Usage: bash .github/receipts/ci.sh <repo-root> <empty work folder>
set -euo pipefail
ROOT=$1; WORK=$2
H="$WORK/בית עם רווח"; mkdir -p "$H"
if command -v py >/dev/null 2>&1; then PY="py -3"; else PY=python3; fi
$PY --version
# the install command is the line of INSTALL.md that starts with "PY -c"
CMD=$(grep -m1 '^PY -c ' "$ROOT/receipts/INSTALL.md")
[ -n "$CMD" ] || { echo "no PY -c line in INSTALL.md"; exit 1; }
CMD="${CMD#PY }"
# Python reads the home folder from USERPROFILE on Windows and from HOME elsewhere; set both
export HOME="$H" USERPROFILE="$(cygpath -w "$H" 2>/dev/null || echo "$H")"
eval "$PY $CMD" | tee "$WORK/install.txt"
grep -q '^INSTALLED ' "$WORK/install.txt"
for d in .claude .agents; do
  S="$H/$d/skills/receipts"
  [ -f "$S/SKILL.md" ] && [ -f "$S/collect_receipts.py" ] || { echo "missing files in $S"; exit 1; }
done
$PY "$H/.claude/skills/receipts/collect_receipts.py" selftest | tee "$WORK/selftest.txt"
grep -q '^SELFTEST OK' "$WORK/selftest.txt"
$PY "$H/.claude/skills/receipts/collect_receipts.py" status | tee "$WORK/status.txt"
grep -q '^SETUP_NEEDED email' "$WORK/status.txt"
# a saved setting with a Notepad-style UTF-16 password must still read as ready, and print nothing secret
mkdir -p "$H/.receipts-skill" && printf 'me@gmail.com\n' > "$H/.receipts-skill/email.txt"
$PY -c "open(r'''$(cygpath -w "$H/.receipts-skill/gmail-password.txt" 2>/dev/null || echo "$H/.receipts-skill/gmail-password.txt")''','w',encoding='utf-16').write('abcd efgh ijkl mnop\r\n')"
$PY "$H/.claude/skills/receipts/collect_receipts.py" status | tee "$WORK/status2.txt"
grep -q '^READY me@gmail.com' "$WORK/status2.txt"
echo "RECEIPTS CI OK"
