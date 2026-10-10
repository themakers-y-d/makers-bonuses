#!/bin/bash
# The video editor gift, installed and run the way an owner's computer runs it, on Mac and on Windows (Git Bash).
# The workflow calls this, and it runs the same on a Mac by hand:
#   bash .github/video-editor/ci.sh <repo> <empty work folder>
# Every install command comes out of the runbooks (runbook-blocks.py). HOME is a folder with Hebrew letters and a
# space in its name, so the studio, the system folder and the videos all live under such a path.
# Env: SKILL_FROM=pinned (default) downloads the skill exactly as step 5 does, from the pinned commit;
#      RAW_BASE=http://127.0.0.1:PORT serves those downloads locally (before the pinned commit is on GitHub);
#      SKILL_FROM=checkout copies the three files from this checkout instead (a working tree, not a release);
#      MODEL_CACHE=<folder> keeps the small transcription model between runs.
set -u
REPO="$(cd "$1" && pwd)"; ROOT="$2"
fail() { echo "FAIL $*"; exit 1; }
step() { echo; echo "======== $*"; }
lastline() { tail -n 1 | tr -d '\r'; }
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1 ;; *) WIN=0 ;; esac
PYX=""; for c in python3 python; do if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then PYX="$c"; break; fi; done
[ -n "$PYX" ] || fail "no Python on this runner to read the runbooks with"

mkdir -p "$ROOT" || fail "cannot create $ROOT"
ROOT="$(cd "$ROOT" && pwd)"
H="$ROOT/בית עם רווח"
SYS="$H/Documents/MAKERS"
VIDS="$H/Desktop/סרטונים לבדיקה"
B="$ROOT/blocks"
mkdir -p "$SYS/.claude/skills" "$SYS/1-me" "$SYS/2-makers" "$VIDS" "$H/.claude/skills"
export HOME="$H"
# Python finds the home folder through USERPROFILE on Windows; on an owner's computer the two are the same folder
if [ "$WIN" = 1 ]; then USERPROFILE="$(cygpath -w "$H")"; export USERPROFILE; fi
unset REEL_STUDIO VIRTUAL_ENV PYTHONHOME
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
upath() { if [ "$WIN" = 1 ]; then cygpath -u "$1"; else printf '%s\n' "$1"; fi; }   # a path the engine printed, for bash
npath() { if [ "$WIN" = 1 ]; then cygpath -m "$1"; else printf '%s\n' "$1"; fi; }   # a path for a native Windows program
sha() { (shasum -a 256 "$1" 2>/dev/null || sha256sum "$1") | cut -d' ' -f1; }
# poll a runbook `wait` command until its last line is READY; anything else but STILL RUNNING stops the run
poll() {
  local f="$1" out
  for _ in $(seq 1 40); do
    out="$(cd "$SYS" && bash "$f" 2>&1)"; echo "$out" | tail -n 2
    case "$(echo "$out" | lastline)" in READY) return 0 ;; "STILL RUNNING"*) ;; *) return 1 ;; esac
  done
  return 1
}
ed() { bash "$H/reel-studio/editor" "$@"; }

step "runbook blocks"
"$PYX" "$REPO/.github/video-editor/runbook-blocks.py" "$REPO" "$B" || fail "the runbooks changed shape"
echo "HOME=$HOME"; [ "$WIN" = 1 ] && echo "USERPROFILE=$USERPROFILE"

step "fix-word tests"
"$PYX" "$REPO/.github/video-editor/test_fix_word.py" "$REPO/skills/video-editor/edit.py" || fail "fix-word tests"

step "Hebrew line order tests (the editor's captions and the style builder's words)"
"$PYX" "$REPO/.github/video-editor/test_bidi.py" "$REPO/skills/video-editor/edit.py" "$REPO/skills/style-maker/kit.py" || fail "Hebrew line order tests"

step "INSTALL step 3: what is on the computer (a fresh one prints nothing)"
(cd "$SYS" && bash "$B/step3-look.sh") | tee "$ROOT/step3.txt"
grep -q "LIBS OK" "$ROOT/step3.txt" && fail "step 3 found tools on a fresh computer"

step "INSTALL step 5: the skill into the system (${SKILL_FROM:-pinned})"
if [ "${SKILL_FROM:-pinned}" = checkout ]; then
  mkdir -p "$SYS/.claude/skills/video-editor"
  for f in SKILL.md craft.md edit.py; do cp "$REPO/skills/video-editor/$f" "$SYS/.claude/skills/video-editor/$f" || fail "copy $f"; done
else
  DL="$B/step5-download.sh"
  if [ -n "${RAW_BASE:-}" ]; then sed "s#https://raw.githubusercontent.com#$RAW_BASE#g" "$DL" > "$B/step5-download-local.sh"; DL="$B/step5-download-local.sh"; fi
  (cd "$SYS" && bash "$DL") | tee "$ROOT/step5.txt"
  grep -q PROBLEM "$ROOT/step5.txt" && fail "a skill file did not download"
  (cd "$SYS" && bash "$B/step5-check.sh") | tee "$ROOT/step5-check.txt"
  [ "$(grep -c ': OK$' "$ROOT/step5-check.txt")" = 3 ] || fail "the downloaded files do not match the fingerprints in step 5"
  # the pinned files are the files of this commit: a skill change that was not pinned again shows here
  for f in SKILL.md craft.md edit.py; do
    want="$(git -C "$REPO" show "HEAD:skills/video-editor/$f" | (shasum -a 256 2>/dev/null || sha256sum) | cut -d' ' -f1)"
    [ "$want" = "$(sha "$SYS/.claude/skills/video-editor/$f")" ] || fail "$f at the pinned commit is not $f of this commit: pin INSTALL-makers.md again"
  done
  echo "the pinned files are the files of this commit"
fi
(cd "$SYS" && bash "$B/step5-launcher.sh") | tee "$ROOT/launcher.txt"
grep -q "LAUNCHER READY" "$ROOT/launcher.txt" || fail "no launcher"

step "INSTALL step 6: the tools"
cp "$B/install-editor.sh" "$H/reel-studio/install-editor.sh"
(cd "$SYS" && bash "$B/step6-base.sh") 2>&1 | tee "$ROOT/base.txt"
grep -q "BASE READY" "$ROOT/base.txt" || fail "base did not finish"
(cd "$SYS" && bash "$B/step6-libs.sh")
if ! poll "$B/step6-libs-wait.sh"; then
  # the runbook: FAILED on the libraries, run the part once more (a dropped connection is the usual cause)
  echo "the libraries failed once, running the part again as step 6 says"; mv "$H/reel-studio/install.log" "$H/reel-studio/install-1.log"
  (cd "$SYS" && bash "$B/step6-libs.sh")
  poll "$B/step6-libs-wait.sh" || { tail -20 "$H/reel-studio/pip.log" 2>/dev/null; fail "the libraries did not install"; }
fi
PY="$H/reel-studio/.venv/bin/python"; [ -x "$PY" ] || PY="$H/reel-studio/.venv/Scripts/python.exe"
"$PY" -c "import av, sys; print('python', sys.version.split()[0], 'av', av.__version__); sys.exit(0 if av.__version__ == '18.1.0' else 1)" || fail "av is not 18.1.0"
if [ -n "${MODEL_CACHE:-}" ] && ls -d "$MODEL_CACHE"/models--Systran--faster-whisper-small >/dev/null 2>&1; then
  mkdir -p "$H/reel-studio/models" && cp -R "$MODEL_CACHE"/models--Systran--faster-whisper-small "$H/reel-studio/models/" && echo "the small model came from the cache"
fi
# the owner's choice ב in step 4: the small model (it saves CI the 1.6 GB Hebrew one)
sed 's/editor model ivrit/editor model small/' "$B/step6-model.sh" > "$B/step6-model-small.sh"
grep -q "model small" "$B/step6-model-small.sh" || fail "the model line changed"
(cd "$SYS" && bash "$B/step6-model-small.sh")
poll "$B/step6-model-wait.sh" || { tail -5 "$H/reel-studio/model.log"; fail "the model did not download"; }
if [ -n "${MODEL_CACHE:-}" ] && ! ls -d "$MODEL_CACHE"/models--Systran--faster-whisper-small >/dev/null 2>&1; then
  mkdir -p "$MODEL_CACHE" && cp -R "$H/reel-studio/models/models--Systran--faster-whisper-small" "$MODEL_CACHE/"
fi
(cd "$SYS" && bash "$B/step6-doctor.sh") | tee "$ROOT/doctor.txt"
[ "$(lastline < "$ROOT/doctor.txt")" = "ALL GOOD" ] || fail "doctor did not end ALL GOOD"

step "SKILL Step 1: the launcher again and the check, from the system folder"
(cd "$SYS" && bash "$B/skill-step1.sh") | tee "$ROOT/step1.txt"
[ "$(lastline < "$ROOT/step1.txt")" = "ALL GOOD" ] || fail "Step 1 of the skill did not end ALL GOOD"

step "the clips"
FF="$(upath "$("$PY" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" | tr -d '\r')")"
V="$VIDS/ריל לבדיקה 1.mp4"; BARS="$VIDS/פסים וצליל.mp4"; MUSIC="$VIDS/מוזיקה שלי.m4a"
cp "$REPO/video-editor/.ci/speech-he.mp4" "$V" || fail "no speech clip"
"$FF" -hide_banner -loglevel error -y -f lavfi -i "smptehdbars=size=1080x1920:rate=30" -f lavfi -i "sine=frequency=440:sample_rate=48000" \
  -t 12 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$(npath "$BARS")" || fail "could not make the colour bars clip"
"$FF" -hide_banner -loglevel error -y -f lavfi -i "sine=frequency=220:sample_rate=48000" -f lavfi -i "sine=frequency=330:sample_rate=48000" \
  -filter_complex "amix=inputs=2,volume=0.5" -t 20 -c:a aac "$(npath "$MUSIC")" || fail "could not make the music"
SV="$(sha "$V")"; SB="$(sha "$BARS")"; SM="$(sha "$MUSIC")"
ls -la "$VIDS"

step "speech: info, transcribe (small), fix-word"
ed info "$V" | tee "$ROOT/info.txt"
JOB="$(upath "$(grep '^JOB FOLDER ' "$ROOT/info.txt" | sed 's/^JOB FOLDER //' | tr -d '\r')")"
[ -d "$JOB" ] || fail "no job folder"
nohup bash "$H/reel-studio/editor" transcribe "$V" --model small > "$JOB/transcribe.log" 2>&1 &
printf 'bash ~/reel-studio/editor wait "%s" TRANSCRIBED\n' "$JOB/transcribe.log" > "$B/wait-transcribe.sh"
poll "$B/wait-transcribe.sh" || { cat "$JOB/transcribe.log"; fail "transcribe"; }
grep '^TRANSCRIBED ' "$JOB/transcribe.log" || fail "transcribe did not end TRANSCRIBED"
cat "$JOB/transcript.txt"
HEB="$("$PY" -c "import re,sys; t=open(sys.argv[1],encoding='utf-8').read(); print(len(re.findall('[א-ת]{2,}', t)))" "$JOB/transcript.txt")"
[ "${HEB:-0}" -ge 5 ] || fail "the transcript has $HEB Hebrew words"
echo "Hebrew words in the transcript: $HEB"
W1="$("$PY" -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); L=d['lines'][0]; print(d['words'][L['w0']]['w'])" "$JOB/words.json" | tr -d '\r')"
ed fix-word "$V" "$W1" "בדיקה" --line 1 | tee "$ROOT/fix.txt"
grep -q '^FIXED ' "$ROOT/fix.txt" || fail "fix-word"
grep -q '^  1) .*בדיקה' "$JOB/transcript.txt" || fail "fix-word did not reach transcript.txt"

step "speech: silences, fillers, edl, style, sheet"
ed silences "$V" | tail -n 3
ed fillers "$V" | tail -n 3
NL="$("$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1],encoding='utf-8'))['lines']))" "$JOB/words.json")"
ed edl "$V" --keep "1-$NL" --use silence,fillers | tee "$ROOT/edl.txt" | head -n 5
grep -q '^EDL ' "$ROOT/edl.txt" || fail "edl"
ed style "$V" --format reel | tee "$ROOT/style.txt"
STY="$(upath "$(grep '^STYLE ' "$ROOT/style.txt" | sed 's/^STYLE //' | tr -d '\r')")"
[ -f "$STY" ] || fail "no style file"
ed sheet "$V" --format reel --style "$STY" | tee "$ROOT/sheet.txt"
grep -qi 'png' "$ROOT/sheet.txt" || fail "no sheet"

render_and_verify() {   # <name> <render args...>
  local name="$1"; shift
  nohup bash "$H/reel-studio/editor" render "$@" > "$JOB/render-$name.log" 2>&1 &
  printf 'bash ~/reel-studio/editor wait "%s" DONE\n' "$JOB/render-$name.log" > "$B/wait-render-$name.sh"
  poll "$B/wait-render-$name.sh" || { tail -n 20 "$JOB/render-$name.log"; fail "render $name"; }
  OUT="$(upath "$(grep '^DONE ' "$JOB/render-$name.log" | sed 's/^DONE //' | tr -d '\r')")"
  [ -f "$OUT" ] || fail "render $name made no file"
  ed verify "$OUT" | tee "$ROOT/verify-$name.txt"
  [ "$(lastline < "$ROOT/verify-$name.txt")" = "FILE OK" ] || fail "verify $name did not end FILE OK"
}

step "speech: render reel, burned captions, ducked music"
render_and_verify reel "$V" --format reel --captions burn --style "$STY" --music "$MUSIC" --duck
grep -E '^captions +PASS' "$ROOT/verify-reel.txt" || fail "no burned captions found in the reel"
"$PY" -c "import json,sys,glob; r=[json.load(open(p,encoding='utf-8')) for p in glob.glob(sys.argv[1]+'/renders/*.json')]; \
r=[x for x in r if x['format']=='reel']; sys.exit(0 if r and r[-1]['music'] and r[-1]['duck'] and r[-1]['captions']=='burn' else 1)" "$JOB" \
  && echo "the reel's render record: burned captions, music, ducked" || fail "the reel was not made with ducked music"

step "speech: render wide, soft captions"
ed style "$V" --format wide --style "$STY" > "$ROOT/style-wide.txt"
render_and_verify wide "$V" --format wide --captions soft --style "$STY"
grep -E '^captions +PASS' "$ROOT/verify-wide.txt" || fail "no subtitle track in the wide version"
ls "$VIDS"/*.srt >/dev/null 2>&1 || fail "no subtitle file beside the wide version"

step "colour bars: a cut by time, no captions (no speech), source format"
ed info "$BARS" | tail -n 1
ed edl "$BARS" --remove "2s-4s" | head -n 2
JOBB="$(upath "$(ed info "$BARS" | grep '^JOB FOLDER ' | sed 's/^JOB FOLDER //' | tr -d '\r')")"
JOB_SAVE="$JOB"; JOB="$JOBB"
render_and_verify bars "$BARS" --format source --captions none
JOB="$JOB_SAVE"

step "the sources are untouched"
[ "$(sha "$V")" = "$SV" ] && [ "$(sha "$BARS")" = "$SB" ] && [ "$(sha "$MUSIC")" = "$SM" ] || fail "a source file changed"
echo "sha256 unchanged: speech, colour bars, music"
ls -la "$VIDS"

step "no CRLF in any text file the install and the engine wrote"
CR=0; N=0
while IFS= read -r -d '' f; do
  N=$((N + 1))
  if [ "$(tr -cd '\r' < "$f" | wc -c | tr -d ' ')" != 0 ]; then echo "CRLF in $f"; CR=1; fi
done < <(find "$H/reel-studio/editor" "$H/reel-studio/install-editor.sh" "$H/reel-studio/edits" "$VIDS" -type f \
           \( -name editor -o -name '*.sh' -o -name '*.json' -o -name '*.txt' -o -name '*.srt' \) -print0)
[ "$CR" = 0 ] || fail "CRLF found"
echo "$N text files, all LF"

step "the reel style builder after the editor (install order): base, then its doctor"
mkdir -p "$H/.claude/skills/style-maker"
for f in SKILL.md axes.md kit.py; do cp "$REPO/skills/style-maker/$f" "$H/.claude/skills/style-maker/$f"; done
cp "$REPO/style-maker/RUNBOOK-makers.md" "$H/.claude/skills/style-maker/makers.md"
cp "$B/style-install.sh" "$H/reel-studio/install.sh"
(cd "$SYS" && bash "$B/style-base.sh") 2>&1 | tee "$ROOT/style-base.txt"
grep -q "BASE READY" "$ROOT/style-base.txt" || fail "the style builder base did not finish"
grep -q "already here, kept" "$ROOT/style-base.txt" || fail "the style builder rebuilt the shared Python environment"
(cd "$SYS" && bash "$B/style-doctor.sh") | tee "$ROOT/kit-doctor.txt"
grep -q "^ALL GOOD" "$ROOT/kit-doctor.txt" || fail "kit doctor did not say ALL GOOD"
(cd "$SYS" && bash "$B/step6-doctor.sh") | tee "$ROOT/doctor-after.txt"
[ "$(lastline < "$ROOT/doctor-after.txt")" = "ALL GOOD" ] || fail "the editor's doctor after the style builder"

echo; echo "ALL CHECKS PASSED ($(uname -s))"
