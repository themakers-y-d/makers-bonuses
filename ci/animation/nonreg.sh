#!/bin/bash
# Audit only: Mac non-regression. Same job, same scenes.py, same mix: the OLD kit.py (main @ 9ac0831)
# against the NEW kit.py already installed. Compares face.json, the check stills and the decoded frames.
SUM="${GITHUB_STEP_SUMMARY:-/dev/null}"; LOGD="$PWD/audit-logs"
rec() { echo "| $1 | $2 | $3 |" >> "$SUM"; echo "== $1: $2 ($3)"; }
PY=~/reel-studio/.venv/bin/python
VIDEO=$(cat "$LOGD/video-path.txt"); JOB=$(cat "$LOGD/job-path.txt"); NEWOUT=$(cat "$LOGD/out-path.txt")
OLD=$RUNNER_TEMP/oldkit; mkdir -p "$OLD"
curl -fsSL -o "$OLD/kit.py" https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/9ac0831/skills/style-maker/kit.py
NEW=~/.claude/skills/style-maker/kit.py
rec nonreg-kit-diff INFO "$(diff "$OLD/kit.py" "$NEW" | grep -c '^[<>]') changed lines old vs new"
# face
cp "$JOB/face.json" "$RUNNER_TEMP/face-new.json"
"$PY" "$OLD/kit.py" face "$VIDEO" > "$LOGD/nonreg-face-old.log" 2>&1
cmp -s "$JOB/face.json" "$RUNNER_TEMP/face-new.json" && rec nonreg-face PASS "face.json identical" || rec nonreg-face FAIL "face.json differs"
# stills
T="0.5 2.0 3.0 5.0 6.0 8.0"
"$PY" "$NEW" render "$VIDEO" --check $T > /dev/null 2>&1; mkdir -p "$RUNNER_TEMP/cn"; cp "$JOB"/checks/check_*.png "$RUNNER_TEMP/cn/"
"$PY" "$OLD/kit.py" render "$VIDEO" --check $T > "$LOGD/nonreg-check-old.log" 2>&1
n=0; d=0; for f in "$RUNNER_TEMP"/cn/*.png; do n=$((n+1)); cmp -s "$f" "$JOB/checks/$(basename "$f")" || d=$((d+1)); done
[ $d -eq 0 ] && rec nonreg-stills PASS "$n stills byte-identical" || rec nonreg-stills FAIL "$d of $n stills differ"
# full render, decoded frames
"$PY" "$OLD/kit.py" render "$VIDEO" --audio "$JOB/mix.wav" --out "$RUNNER_TEMP/old.mp4" > "$LOGD/nonreg-render-old.log" 2>&1
OLDOUT=$(sed -n 's/^DONE //p' "$LOGD/nonreg-render-old.log")
FF=$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -v error -i "$NEWOUT" -map 0:v -f framemd5 - | grep -v '^#' | awk -F, '{print $NF}' > "$RUNNER_TEMP/new.md5"
"$FF" -v error -i "$OLDOUT" -map 0:v -f framemd5 - | grep -v '^#' | awk -F, '{print $NF}' > "$RUNNER_TEMP/old.md5"
nf=$(wc -l < "$RUNNER_TEMP/new.md5"); dd=$(diff "$RUNNER_TEMP/new.md5" "$RUNNER_TEMP/old.md5" | grep -c '^<')
[ "$dd" -eq 0 ] && rec nonreg-render PASS "$nf decoded frames identical" || rec nonreg-render FAIL "$dd of $nf frames differ"
exit 0
