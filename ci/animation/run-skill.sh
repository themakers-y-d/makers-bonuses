#!/bin/bash
# Audit harness (not part of the skill): performs style-maker's SKILL.md steps exactly as an agent would,
# against the PUBLISHED files in ~/.claude/skills/style-maker (downloaded from main by the INSTALL message).
# Usage: run-skill.sh part1 | part2 <path-to-video>
# Never uses set -e: every step is recorded PASS/FAIL in $SUM and the run continues where it can.
SUM="${GITHUB_STEP_SUMMARY:-/dev/null}"
LOGD="${AUDIT_LOGS:-$PWD/audit-logs}"; mkdir -p "$LOGD"
MODEL="${AUDIT_MODEL:-ivrit}"
rec() { echo "| $1 | $2 | $3 |" >> "$SUM"; echo "== $1: $2 ($3)"; }
run() { # run <name> <cmd...>: records PASS/FAIL, keeps output in $LOGD/<name>.log
  local n="$1"; shift
  "$@" > "$LOGD/$n.log" 2>&1; local rc=$?
  cat "$LOGD/$n.log" | tail -40
  if [ $rc -eq 0 ]; then rec "$n" PASS "rc=0"; else rec "$n" FAIL "rc=$rc"; fi
  return $rc
}
waitfor() { # waitfor <name> <log> <marker>: kit wait loop exactly as SKILL.md says, max ~25 min
  local n="$1" log="$2" mk="$3" out i
  for i in $(seq 1 17); do
    out=$(bash ~/reel-studio/kit wait "$log" "$mk" 2>&1); echo "$out" | tail -2
    case "$out" in
      *READY*) rec "$n" PASS "READY after $i wait calls"; return 0 ;;
      *FAILED*|*STUCK*) rec "$n" FAIL "$(echo "$out" | tail -1)"; cat "$log" | tail -30; return 1 ;;
    esac
  done
  rec "$n" FAIL "never READY"; return 1
}

echo "uname: $(uname -sm)   HOME=$HOME"
[ "$1" = "part1" ] && {
  echo "| step | result | detail |" >> "$SUM"; echo "|---|---|---|" >> "$SUM"
  rec "env" INFO "$(uname -sm) HOME=$HOME"
  # SKILL.md step 1 (the check)
  run step1-check bash -c "find ~/.claude/skills -maxdepth 1 -name 'reel-style-*' 2>/dev/null; ls ~/reel-studio/kit 2>/dev/null && bash ~/reel-studio/kit doctor; true"
  # SKILL.md step 6, item 1: write install.sh "as it is" from the published SKILL.md
  mkdir -p ~/reel-studio
  awk '/וכתוב לתוכה את הקובץ `install.sh`/{f=1;next} f&&/^```bash/{g=1;next} g&&/^```/{exit} g' \
      ~/.claude/skills/style-maker/SKILL.md > ~/reel-studio/install.sh
  if [ "${AUDIT_CRLF:-0}" = "1" ]; then
    sed -i 's/$/\r/' ~/reel-studio/install.sh
    rec "crlf" INFO "install.sh rewritten with CRLF, $(grep -c $'\r' ~/reel-studio/install.sh) CR lines"
    run crlf-base-as-is bash ~/reel-studio/install.sh base
    ls -la ~/reel-studio/ | tee "$LOGD/crlf-dir.txt"; [ -f ~/reel-studio/kit ] && od -c ~/reel-studio/kit | head -5 | tee -a "$LOGD/crlf-dir.txt"
    run crlf-kit-doctor bash ~/reel-studio/kit doctor
    # the proposed fix: strip CR before running, then re-run
    tr -d '\r' < ~/reel-studio/install.sh > ~/reel-studio/install.tmp && mv ~/reel-studio/install.tmp ~/reel-studio/install.sh
    rec "crlf-fix" INFO "CR lines after tr: $(grep -c $'\r' ~/reel-studio/install.sh)"
  fi
  run install-base bash ~/reel-studio/install.sh base
  grep -q "BASE READY" "$LOGD/install-base.log" && rec base-marker PASS "BASE READY" || rec base-marker FAIL "no BASE READY"
  # item 3: libs in the background with nohup (fallback form), then this shell EXITS: part2 waits in a new shell
  nohup bash ~/reel-studio/install.sh libs > ~/reel-studio/install.log 2>&1 &
  rec "libs-bg" INFO "started pid $! with nohup, shell exits now"
  exit 0
}

[ "$1" = "part2" ] && {
  VIDEO_ORIG="$2"
  waitfor libs-wait ~/reel-studio/install.log INSTALLED
  cp ~/reel-studio/install.log "$LOGD/" ; cp ~/reel-studio/pip.log "$LOGD/" 2>/dev/null
  # item 4: model in background, wait
  nohup bash ~/reel-studio/kit model "$MODEL" > ~/reel-studio/model.log 2>&1 &
  waitfor model-wait ~/reel-studio/model.log "MODEL READY"
  cp ~/reel-studio/model.log "$LOGD/"
  # item 5: doctor
  run doctor bash ~/reel-studio/kit doctor
  grep -q "ALL GOOD" "$LOGD/doctor.log" && rec doctor-marker PASS "ALL GOOD" || rec doctor-marker FAIL "$(tail -1 "$LOGD/doctor.log")"
  grep -q "x264=yes" "$LOGD/doctor.log" && rec x264 PASS yes || rec x264 FAIL "x264 missing"
  # step 5 check command, on a small fake style file with Hebrew
  mkdir -p ~/.claude/skills/reel-style-ci
  printf -- '---\nname: reel-style-ci\ndescription: The personal reel style of ci. Use whenever the owner says apply my style.\n---\n1) נוכחות הדובר: שכבה מעל\n' > ~/.claude/skills/reel-style-ci/SKILL.md
  run step5-check bash -c 'F=~/.claude/skills/reel-style-ci/SKILL.md; head -3 "$F"; sed -n "s/^description: //p" "$F" | grep -c ": "; grep -c "^[0-9]*) " "$F"; grep -c "$(printf "\342\200\224")" "$F"; grep -c "<" "$F"; true'
  # step 7: font
  run font bash ~/reel-studio/kit font --hand
  # step 8: intake. First try the ORIGINAL path directly (to learn if the ASCII copy rule is needed), then the rule.
  run info-original-path bash ~/reel-studio/kit info "$VIDEO_ORIG"
  N="reel-$(date +%Y%m%d-%H%M)"
  VIDEO=$(mkdir -p ~/reel-studio/in && cp "$VIDEO_ORIG" ~/reel-studio/in/$N.mp4 && echo ~/reel-studio/in/$N.mp4)
  rec "ascii-copy" INFO "$VIDEO"
  run info bash ~/reel-studio/kit info "$VIDEO"
  JOB=$(sed -n 's/^JOB FOLDER //p' "$LOGD/info.log" | tr -d '\r')
  rec "job-folder" INFO "$JOB"
  if ! run face bash ~/reel-studio/kit face "$VIDEO"; then
    # SKILL.md: LOW CONFIDENCE / NO FACE FOUND -> --manual. A crash (not NO FACE FOUND) is a finding.
    grep -q "NO FACE FOUND" "$LOGD/face.log" && rec face-kind INFO "clean NO FACE FOUND" || rec face-kind FAIL "crash, not the clean NO FACE FOUND path"
    run face-manual bash ~/reel-studio/kit face "$VIDEO" --manual 360 220 680 520
  fi
  run sheet bash ~/reel-studio/kit sheet "$VIDEO"
  run band bash ~/reel-studio/kit band "$VIDEO" --captions-top 75
  # step 9: transcribe (short video: directly)
  run transcribe bash ~/reel-studio/kit transcribe "$VIDEO" --model "$MODEL"
  # step 11: scaffold + a minimal agent-written scenes.py (card + iris + one-word captions)
  run scaffold bash ~/reel-studio/kit scaffold "$VIDEO"
  PYEXE=~/reel-studio/.venv/bin/python; [ -x "$PYEXE" ] || PYEXE=~/reel-studio/.venv/Scripts/python.exe
  "$PYEXE" - "$JOB" <<'PY' > "$LOGD/scenes-edit.log" 2>&1 && rec scenes-edit PASS ok || rec scenes-edit FAIL "see log"
import sys, json, re
from pathlib import Path
jd = Path(sys.argv[1]); p = jd / "scenes.py"; s = p.read_text(encoding="utf-8")
w = json.loads((jd / "words.json").read_text(encoding="utf-8"))["words"]
t = lambda i, d: w[i]["s"] if len(w) > i else d
s = s.replace("SCENES = [\n    # dict(name=\"card\", t=2.20, until=3.40),\n]",
              f"SCENES = [dict(name='card', t={t(2, 1.5)}, until={t(5, 3.0)})]")
s = s.replace("FULLSCREEN = [\n", f"FULLSCREEN = [({t(7, 4.5)}, {t(10, 6.5)}, (540, 900)),\n", 1)
s = s.replace('                c.text(540, mid, "מילה", 56, INK, 600)',
              '                c.text(540, mid, "דפי נחיתה", 56, INK, 600)\n'
              '    cw = current_word(t, WORDS)\n'
              '    if cw:\n'
              '        c.text(540, 1440, cw["w"], 90, (255, 255, 255), 800, stroke=8, stroke_fill=(0, 0, 0))')
p.write_text(s, encoding="utf-8"); print(s[-900:])
PY
  cat "$LOGD/scenes-edit.log" | tail -12
  # step 12: stills
  run render-check bash ~/reel-studio/kit render "$VIDEO" --check 0.5 2.0 3.0 5.0 6.0 8.0
  # step 13: sound
  run sfx bash ~/reel-studio/kit sfx
  DUR=$(sed -n 's/.*"duration": \([0-9.]*\).*/\1/p' "$LOGD/info.log" | head -1)
  printf '{"end": %s, "bed": {"type": "pad", "under_lu": 17}, "cues": [{"name": "card", "t": 2.0, "layers": [{"sound": "knock", "db": -8}]}, {"name": "iris", "t": 5.0, "layers": [{"sound": "whoosh", "db": -12}]}]}\n' "$DUR" > "$JOB/cues.json"
  run mix bash ~/reel-studio/kit mix "$VIDEO" "$JOB/cues.json"
  # step 14: full render in the background, exactly the SKILL.md form (log path = the JOB FOLDER string kit printed)
  nohup bash ~/reel-studio/kit render "$VIDEO" --audio "$JOB/mix.wav" > "$JOB/render.log" 2>&1 &
  waitfor render-wait "$JOB/render.log" DONE
  cp "$JOB/render.log" "$LOGD/" 2>/dev/null
  OUT=$(sed -n 's/^DONE //p' "$JOB/render.log" | tr -d '\r')
  rec "out" INFO "$OUT"
  # step 15: verify, then cp -n next to the original
  run verify bash ~/reel-studio/kit verify "$OUT" --at 1 3 5 7
  grep -q "FILE OK" "$LOGD/verify.log" && rec verify-marker PASS "FILE OK" || rec verify-marker FAIL "no FILE OK"
  DEST="$(dirname "$VIDEO_ORIG")/$(basename "$VIDEO_ORIG" .mp4)-animated.mp4"
  run copy-back cp -n "$OUT" "$DEST"
  ls -la "$(dirname "$VIDEO_ORIG")" | tee -a "$LOGD/copy-back.log"
  # collect artifacts
  mkdir -p "$LOGD/job"; cp "$JOB"/*.png "$JOB"/*.json "$JOB"/scenes.py "$LOGD/job/" 2>/dev/null
  cp "$JOB"/checks/sheet.png "$LOGD/job/checks-sheet.png" 2>/dev/null
  cp ~/reel-studio/fonts/test.png "$LOGD/job/font-test.png" 2>/dev/null
  cp "$DEST" "$LOGD/job/" 2>/dev/null
  STUDIO_DIRS=$(find ~ -maxdepth 1 -name 'reel-studio*' 2>/dev/null | tr '\n' ' ')
  rec "studio-folders" INFO "$STUDIO_DIRS ($(du -sh ~/reel-studio 2>/dev/null | cut -f1))"
  exit 0
}
echo "usage: run-skill.sh part1 | part2 <video>"; exit 1
