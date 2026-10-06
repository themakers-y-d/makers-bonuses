# Morty, this one is for you

The owner brought a MAKERS gift to install: the video editor. This file is written to you so you do not have to work out what to do. The owner does not need to read it. If you saved this file inside the system folder to read it, delete it when the install is done; it is not part of their vault. Speak to the owner in Hebrew, as always; the lines in code blocks marked as messages are theirs word for word.

## What it is, in one line

A skill that edits a video the owner filmed by message and not by seconds: it reads the Hebrew transcript, proposes which lines to keep with a reason for every cut, and after one approval renders a finished cut with Hebrew captions and music under the voice, beside the original, which it never touches.

## Decisions already made for you

Do not spend questions on them.

**Who does the work: the Designer, in the main conversation, from step 2 to the end, install included.** The job is how a video comes out, and the skill is a conversation that stops for the owner's approval of the cut list. A worker in its own window cannot hold that conversation. You say the move line in step 1 and the Designer takes it from there. No chain.

**The project:** `3-work/now/video/`. If it exists, work inside it. Every video gets a dated record at its top level, its working material in `_process/`, and the caption style the owner settles on is kept there as `caption-style.json`.

**Where things live.** The skill goes into the system's own `.claude/skills/video-editor/`, so it travels with the system and shows as `/video-editor`. The tools go into `~/reel-studio` in the home folder, the same folder, Python environment and Hebrew transcription model the reel style builder uses: an owner who installed that gift skips the big download. The videos stay beside the originals, never inside the system.

**Skills:** `video-editor`, and `/final-pass` at the end of every run. No `/connect-a-tool` and no `/ship-it-live`: nothing connects to an account and nothing goes live.

**Your questions:** the ones in step 4, word for word, never more than three, in one message. Most owners get one. The skill asks its own questions about a video at the moment it matters.

**The row in `tools.md`** is written by the Designer in step 7, once, after step 6 proved the tools work. If a rule file that loads when you open `tools.md` names another writer for connections, this row is still yours to write: it records a local tool, after proof, with its off switch, which is exactly what that file is for.

**What is kept at the end:** the skill, one row in `tools.md`, and, if the owner tried a video, an edited version beside it and a dated record in `3-work/now/video/`.

## Two rules not to work around

**Downloading about 2 GB and running commands is the owner's decision.** Step 4 asks before anything downloads, and nobody approves in their place.

**`~/reel-studio` is shared.** Never delete it, never reinstall over a working one, and never touch `install.sh`, `kit` or anything else the reel style builder put there. This install adds its own files beside them.

## Order of work

### שלב 1. The move line

If this is the owner's first session and your own file asks for a first-session line, say it first, in one line, then continue here.

Send this message:

```
זו עבודה של המעצב שלך. הוא מתקין את עורך הווידאו ועורך איתך כאן, בשיחה הזו.
```

Then open `2-makers/designer/designer.md`, become the Designer for the rest of this file, and continue at step 2.

### שלב 2. Where you are

First find out which computer this is, without asking: run `uname -s`. `Darwin` is a Mac. `MINGW`, `MSYS` or `CYGWIN` is Windows with Git Bash. Both continue below with the same commands.

If `uname` itself fails, you are on Windows in PowerShell, without Git for Windows, and every command in this file and in the skill needs it. Check in PowerShell whether it is installed but not found: `@("$env:ProgramFiles\Git\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe") | Where-Object { Test-Path $_ }`.

• Nothing printed: say "כדי לערוך וידאו אני צריך את Git for Windows, כלי חינמי שדרכו Claude Code מריץ פקודות. ההתקנה לוקחת כמה דקות, ווינדוס עשוי לפתוח חלון שמבקש אישור, ואז מאשרים. מאשר שאתקין?" After a yes, run in PowerShell, allowing ten minutes: `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements`. If winget is missing or fails, give the owner https://git-scm.com/download/win and ask them to run the file and accept the defaults. Then run the check above again.
• A path printed: run `setx CLAUDE_CODE_GIT_BASH_PATH "<that path>"` and say: "Git for Windows מותקן. עכשיו סגור את Claude Code לגמרי, כולל החלון שהוא פתוח בו, פתח אותו שוב באותה תיקייה, והדבק לי שוב את הודעת ההתקנה." Stop here. The next paste starts this file again and `uname` answers.
• A path printed and `$env:CLAUDE_CODE_GIT_BASH_PATH` already set: the owner already reopened and it still does not run bash. Do not install again. Say: "Git for Windows מותקן, אבל Claude Code עוד לא משתמש בו. הפעל מחדש את המחשב, פתח את Claude Code והדבק שוב את הודעת ההתקנה." Stop here.

Then check that this is a MAKERS system: a `.claude/skills/` folder beside `1-me/` or `2-makers/`, in the folder you are working in.

```bash
pwd; ls -d .claude/skills 1-me 2-makers 2>/dev/null
```

`.claude/skills` and at least one of the other two printed: continue. Otherwise say in one sentence that this is not their MAKERS folder, ask them to open Claude Code in the folder they open every day and paste the message again, and stop without touching anything.

### שלב 3. What is already on the computer

Silently, with no message to the owner:

```bash
ls -d ~/reel-studio/.venv ~/reel-studio/models/models--* .claude/skills/video-editor .claude/skills/video-editing-skill 2>/dev/null
PY=~/reel-studio/.venv/bin/python; [ -x "$PY" ] || PY=~/reel-studio/.venv/Scripts/python.exe; [ -x "$PY" ] && "$PY" -c "import importlib.util as u; m = [x for x in ('numpy', 'PIL', 'cv2', 'faster_whisper', 'imageio_ffmpeg', 'certifi') if not u.find_spec(x)]; print('LIBS OK' if not m else 'LIBS MISSING ' + ' '.join(m))"; true
```

Read the result into four facts:

• **The tools.** `LIBS OK` means the Python environment and its libraries are in place, almost always from the reel style builder. No `.venv`, or `LIBS MISSING`, means step 5 installs them. A fresh computer prints nothing here, and that is the usual case, not a fault.
• **The model.** `models--ivrit-ai--whisper-large-v3-turbo-ct2` is the Hebrew model. `models--Systran--faster-whisper-medium` or `models--Systran--faster-whisper-small` is a general one, which also works. None of them means step 5 downloads one.
• **An earlier copy of this editor.** `.claude/skills/video-editor` means the owner installed it before: step 6 downloads over it, which is the update.
• **The old method.** `.claude/skills/video-editing-skill` is an older, text-only video method some owners copied from the skills hub. It would compete with this skill for the same sentences, so step 4 asks about it.

### שלב 4. One message: what happens, and the questions

Send one message, built from the facts of step 3. The opening, with exactly one of the two first items:

```
מתקין לך את עורך הווידאו. ככה זה ילך:
1) מצאתי במחשב את הכלים שהתקנת עם בונה הסגנון לרילס, אז אין הורדה גדולה.
1) הורדה של פעם אחת לתיקייה אחת, `reel-studio` בתיקיית הבית, בלי הרשאות מנהל ובלי לגעת בשום דבר אחר במחשב: בערך 500 מגה של כלים ועוד מודל תמלול. זה לוקח 10 עד 25 דקות, ויותר באינטרנט איטי, עם רגעים ארוכים של שקט. זה תקין, ואכתוב לך התקדמות.
2) שלושה קבצים קטנים לתיקיית הסקילים של המערכת שלך, ושורה אחת ברשימת הכלים שלך עם הדרך לכבות.
3) אם יש לך סרטון, נערוך אותו מיד אחרי, כאן.
Claude Code יבקש ממך כמה פעמים לאשר כתיבה לתיקיית ההגדרות ולהריץ פקודות. זה רגיל, אשר. כדאי להישאר ליד המחשב, כי כל אישור שמחכה לך עוצר את העבודה.
```

When the tools were found but no model was, the first item is the second one with "בערך 500 מגה של כלים ועוד" removed and "5 עד 15 דקות" in place of "10 עד 25 דקות".

Then, in the same message, only the questions that apply, numbered in the order you ask them, word for word:

• Only when no model was found: "איזה מודל תמלול להוריד? א) עברי מדויק, בערך 1.6 ג'יגה (מומלץ) ב) קטן, בערך חצי ג'יגה, מהיר יותר ופחות מדויק בעברית. ומאשר את ההורדה?"
• Only when the old method was found: "יש אצלך גם שיטת עריכת וידאו ישנה, `video-editing-skill`. להסיר אותה, כדי ששתיהן לא יתבלבלו? (כן / לא)"
• Always: "יש לך סרטון לנסות עליו? אם כן, גרור אותו לכאן עכשיו, ונערוך אותו מיד אחרי ההתקנה. אם לא, זה לא חובה."

Wait for the answer. No answer to the model question is not a yes: nothing downloads until the owner says so. "לא יודע" on the model is the Hebrew one, after the yes to download.

### שלב 5. The tools, only when missing

On Mac and on Windows in Git Bash the commands of this step are the same: the script below picks the right download for the computer by itself.

When step 3 found `LIBS OK` and a model, skip this step entirely and say nothing about it. Otherwise, write `~/reel-studio/install-editor.sh` with exactly this content. It uses the same pinned versions as the reel style builder, so the two gifts keep sharing one folder:

```bash
#!/bin/bash
# The video editor's tools, shared with the reel style builder.
# base: uv and Python (about a minute). libs: the libraries (the long part). model NAME: the transcription model.
# wait LOG MARK: returns within about 90 seconds with READY, STILL RUNNING, STUCK or FAILED.
STUDIO="$HOME/reel-studio"
mkdir -p "$STUDIO/tools" "$STUDIO/in" "$STUDIO/models" && cd "$STUDIO" || exit 1
export UV_PYTHON_INSTALL_DIR="$STUDIO/tools/python" UV_CACHE_DIR="$STUDIO/tools/cache" VIRTUAL_ENV="$STUDIO/.venv"
PY="$STUDIO/.venv/bin/python"; [ -x "$PY" ] || PY="$STUDIO/.venv/Scripts/python.exe"
if [ "$1" = "base" ]; then
  if [ ! -x tools/uv/uv ] && [ ! -x tools/uv/uv.exe ]; then
    case "$(uname -sm)" in
      "Darwin arm64")  UVPKG=uv-aarch64-apple-darwin.tar.gz ;;
      "Darwin x86_64") UVPKG=uv-x86_64-apple-darwin.tar.gz ;;
      MINGW*|MSYS*|CYGWIN*) UVPKG=uv-x86_64-pc-windows-msvc.zip ;;
      *) echo "PROBLEM unsupported computer $(uname -sm)"; exit 1 ;;
    esac
    UVVER=0.12.19
    case "$UVPKG" in
      uv-aarch64-apple-darwin.tar.gz) UVSHA=a9a8df1eedeb192f2e47e40e2faabfb387db4b850209118786d42f89dde3e0ba ;;
      uv-x86_64-apple-darwin.tar.gz)  UVSHA=cb5fa57bafe68fc0fb94b17f06bee0b0b9a7feb94ccbd110445afa0696e39273 ;;
      uv-x86_64-pc-windows-msvc.zip)  UVSHA=6dbb02d79e419522f1c500f0adb1cddcff0cda7d59b0d66ea7f5e3b4a1b2f5f0 ;;
    esac
    curl -fsSL -o "tools/$UVPKG" "https://github.com/astral-sh/uv/releases/download/$UVVER/$UVPKG" || { echo "PROBLEM no internet connection, or GitHub is blocked"; exit 1; }
    GOT=$( (shasum -a 256 "tools/$UVPKG" 2>/dev/null || sha256sum "tools/$UVPKG") | cut -d' ' -f1 )
    [ "$GOT" = "$UVSHA" ] || { echo "PROBLEM the downloaded file does not match its checksum, stopping"; rm -f "tools/$UVPKG"; exit 1; }
    mkdir -p tools/uv
    case "$UVPKG" in
      *.zip) if command -v unzip >/dev/null 2>&1; then unzip -oq "tools/$UVPKG" -d tools/uv; else powershell -NoProfile -Command "Expand-Archive -Force 'tools/$UVPKG' 'tools/uv'"; fi ;;
      *) tar -xzf "tools/$UVPKG" -C tools/uv --strip-components 1 ;;
    esac
  fi
  if [ -x "$PY" ]; then echo "the Python environment is already here, kept as it is"; else tools/uv/uv venv --python "${PYVER:-3.12}" "$STUDIO/.venv" || exit 1; fi
  echo "BASE READY"
fi
if [ "$1" = "libs" ]; then
  tools/uv/uv pip install numpy==2.5.3 pillow==12.3.0 opencv-python-headless==4.14.0.94 faster-whisper==1.2.1 imageio-ffmpeg==0.6.0 certifi==2026.7.22 > "$STUDIO/pip.log" 2>&1 &
  PIP=$!
  while kill -0 $PIP 2>/dev/null; do echo "installing libraries, $(du -sm "$STUDIO/.venv" 2>/dev/null | cut -f1) MB so far"; sleep 15; done
  wait $PIP || { tail -5 "$STUDIO/pip.log"; echo "PROBLEM the libraries did not install"; exit 1; }
  tools/uv/uv cache clean >/dev/null 2>&1
  echo "INSTALLED $(du -sh "$STUDIO" | cut -f1) in $STUDIO"
fi
if [ "$1" = "model" ]; then
  case "${2:-ivrit}" in
    ivrit)  ID=ivrit-ai/whisper-large-v3-turbo-ct2; REV=72ad623a37947395efcc3933132353790e5a12f5 ;;
    medium) ID=medium; REV= ;;
    small)  ID=small; REV= ;;
    *) echo "PROBLEM unknown model $2"; exit 1 ;;
  esac
  ( while true; do echo "downloaded so far $(du -sm "$STUDIO/models" 2>/dev/null | cut -f1) MB"; sleep 20; done ) & WATCH=$!
  HF_HUB_DISABLE_TELEMETRY=1 "$PY" -c "import sys; from faster_whisper.utils import download_model; p = download_model(sys.argv[1], cache_dir=sys.argv[2], revision=sys.argv[3] or None); print('MODEL READY', p)" "$ID" "$STUDIO/models" "$REV"; RC=$?
  kill $WATCH 2>/dev/null
  [ $RC = 0 ] || echo "PROBLEM the model did not download"
fi
if [ "$1" = "wait" ]; then
  LOG="$2"; MARK="$3"; T=0
  while [ $T -lt 90 ]; do
    if [ -f "$LOG" ]; then
      grep -q "$MARK" "$LOG" && { tail -1 "$LOG"; echo "READY"; exit 0; }
      grep -q -e "PROBLEM" -e "Traceback" "$LOG" && { tail -5 "$LOG"; echo "FAILED"; exit 2; }
      [ -n "$(find "$LOG" -mmin +5 2>/dev/null)" ] && { tail -1 "$LOG"; echo "STUCK nothing new in the log for 5 minutes"; exit 3; }
    fi
    sleep 5; T=$((T + 5))
  done
  tail -1 "$LOG" 2>/dev/null; echo "STILL RUNNING (run the same wait command again)"
fi
```

Then run the parts the facts of step 3 call for, in this order, skipping any that are already in place:

1) Without `.venv`: `bash ~/reel-studio/install-editor.sh base`, in the foreground, allowing ten minutes; it usually takes a minute. Done when `BASE READY` prints.
2) Without `LIBS OK`: tell the owner "מתקין עכשיו את הספריות, בין שלוש לעשר דקות, עם שקט ביניהן. זה תקין." and run it in the background, with your tool's background option or `nohup bash ~/reel-studio/install-editor.sh libs > ~/reel-studio/install.log 2>&1 &`. Then wait: `bash ~/reel-studio/install-editor.sh wait ~/reel-studio/install.log INSTALLED`.
3) Without a model: tell the owner "מוריד עכשיו את מודל התמלול, בין חמש לחמש עשרה דקות. אכתוב לך כמה ירד." and run, in the background the same way, `bash ~/reel-studio/install-editor.sh model ivrit > ~/reel-studio/model.log 2>&1` (or `model small` when the owner chose ב). Then wait: `bash ~/reel-studio/install-editor.sh wait ~/reel-studio/model.log "MODEL READY"`.

Each `wait` returns within about a minute and a half. `STILL RUNNING`: tell the owner in one line how far it got (the megabytes on the last line) and run it again. `READY`: next part. `STUCK`: run the same part once more; the model download continues where it stopped. `FAILED` on the libraries: show the owner the last lines in one sentence and run the part once more. `FAILED` on the Hebrew model: download `model medium` instead and tell the owner in one line. A warning about `HF_TOKEN` or symlinks in the log is harmless.

If `base` fails on a Windows computer with an ARM processor, run it again this way, then `libs` again as in item 2. On a Mac this line does nothing:

```bash
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) PYVER=cpython-3.12-windows-x86_64-none bash ~/reel-studio/install-editor.sh base ;; esac
```
 Any other failure twice: show the owner the last three lines, say in one sentence what is missing, and stop. The script is safe to run again later; nothing is deleted.

### שלב 6. The skill, into the system

The commands are the same on Mac and on Windows in Git Bash. Download the three files of the skill straight into the system's skill folder, from the system folder you checked in step 2:

```bash
D="$(pwd)/.claude/skills/video-editor"; mkdir -p "$D" && for f in SKILL.md craft.md edit.py; do curl -fsSL -o "$D/$f" "https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/video-editor/$f" || echo "PROBLEM $f did not download"; done
```

Claude Code asks the owner to approve writing into `.claude/`. That is expected; it was announced in step 4.

Check the download, each line on its own so one failure does not hide another:

```bash
D="$(pwd)/.claude/skills/video-editor"; head -2 "$D/SKILL.md"
D="$(pwd)/.claude/skills/video-editor"; sed -n 's/^description: //p' "$D/SKILL.md" | grep -c ': '; true
D="$(pwd)/.claude/skills/video-editor"; wc -c "$D/SKILL.md" "$D/craft.md" "$D/edit.py"
D="$(pwd)/.claude/skills/video-editor"; grep -l '^404' "$D/SKILL.md" "$D/craft.md" "$D/edit.py"; true
```

Expected: `---` and `name: video-editor`, then `0`, then a size for each of the three files with none of them zero, then nothing. A bad file: download it once more. If it fails again, tell the owner in one line that the download from GitHub does not go through, and stop. Nothing is deleted; pasting the install message again later finishes the job.

Then write the launcher and run the tool check, exactly as Step 1 of the skill does:

```bash
SK="$(pwd)/.claude/skills/video-editor"; [ -f "$SK/edit.py" ] || { echo "NOT IN THE SYSTEM FOLDER"; exit 1; }; mkdir -p ~/reel-studio && printf '#!/bin/bash\nPY="$HOME/reel-studio/.venv/bin/python"; [ -x "$PY" ] || PY="$HOME/reel-studio/.venv/Scripts/python.exe"\nexport REEL_STUDIO="$HOME/reel-studio" PYTHONIOENCODING=utf-8 PYTHONUTF8=1\nexec "$PY" %q "$@"\n' "$SK/edit.py" > ~/reel-studio/editor && bash ~/reel-studio/editor doctor
```

The last line must be `ALL GOOD`. A `MISSING` library: run the `libs` part of step 5 again. No transcription model: the `model` part of step 5. `x264=NO` on the video line: the video encoder that came with the tools cannot encode on this computer; tell the owner in one sentence and stop. Anything else: show the owner the last lines and stop.

After `ALL GOOD`, send:

```
עורך הווידאו מותקן אצלך, והכלים עברו בדיקה.
כדי שהוא יופיע אצלך לבד בפעם הבאה, צריך לסגור ולפתוח את Claude Code, כי סקילים נטענים רק בפתיחה. אזכיר לך את זה בסוף. עכשיו אין צורך.
```

### שלב 7. Closing the loop

**The row in `tools.md`.** Open `tools.md` in the system folder and add one row to its existing table, now that step 6 proved the tool works. If the line `*No tools connected.*` is there, remove it, because it is no longer true. If `tools.md` does not exist, create it with the table header `| Tool | What it can do | Connected | How to switch it off |` and its separator line. The row, with today's date:

```
| עורך וידאו מקומי, בתיקייה `reel-studio` | read + write, על קבצים במחשב בלבד. קורא סרטון שנתת לו ושומר לידו גרסאות חדשות. לא מעלה ולא שולח כלום החוצה | <YYYY-MM-DD> | מוחקים את התיקייה `video-editor` שבתוך `.claude/skills` של המערכת. את `reel-studio` שבתיקיית הבית מוחקים רק אם בונה הסגנון לרילס לא בשימוש, כי שניהם משתמשים בה |
```

If an earlier install already wrote this row, update its date and do not add a second one.

**The old method.** Only when the owner said yes in step 4: `rm -rf .claude/skills/video-editing-skill`, and say in one line that it is removed. On no, leave it, and do not ask again.

**For the Archivist,** at the session debrief, as proposals and not written by you:
• "designer.md: עריכת וידאו היא של המעצב, בשיחה הראשית, עם הסקיל /video-editor. סגנון הכתוביות של הבעלים שמור בקובץ 3-work/now/video/caption-style.json."
• "morty.md, בטבלת הצוות: סרטון לעריכה הולך למעצב."

### שלב 8. The first video, now

When the owner dragged a video or gave its path in step 4, edit it now, still as the Designer, in this conversation. The skill is not loaded as a skill until Claude Code reopens, and it does not need to be: open `.claude/skills/video-editor/SKILL.md` and follow it from Step 1, on that video. What the owner sees, in order:

1) Steps 1 to 3 of the skill: the tool check passes silently, and one message arrives with what is already known and at most three questions about this video.
2) Step 4: the transcript runs, with a progress line every minute and a half.
3) Step 5: the message in one sentence, the opening line, the cut list by line numbers with a reason for every cut, and how long it will come out. The owner approves or changes it.
4) Steps 6 to 8: the edit is built, the caption style comes from their brief or the safe default with one line saying which, and a sheet of frames opens before the full render.
5) Step 9: the full render, with a percent after every check.
6) Steps 10 to 12: the delivered file is checked and opens in the player, the record lands in `3-work/now/video/`, and the report asks what to change.
7) Step 13: each note makes the next numbered version from the source.

When the owner is done with the video, or stops, continue at step 9 here. When there was no video in step 4, go straight to step 9.

### שלב 9. Close and reopen, and the next time

Send:

```
עוד דבר אחד, ואז זה שלך.
סגור את Claude Code לגמרי ופתח אותו מחדש באותה תיקייה, כדי שהעורך ייטען כמו כל סקיל. במק: Cmd+Q, לא רק סגירת החלון. בווינדוס: Alt+F4 או סגירת כל החלונות של התוכנה. בטרמינל כותבים /exit או לוחצים Ctrl+C פעמיים.
מאז פשוט כתוב "תערוך לי את הסרטון" וגרור אותו לכאן, או לחץ `/video-editor`. הכלים כבר אצלך, והסגנון של הכתוביות נשמר אחרי הסרטון הראשון.
להסרה: מוחקים את התיקייה `video-editor` שבתוך `.claude/skills` של המערכת ואת השורה שלו בקובץ `tools.md`. את `reel-studio` שבתיקיית הבית מוחקים רק אם בונה הסגנון לרילס לא בשימוש.
```

`/final-pass` adds its closing line after this, as it does everywhere, and the Designer names the files it opened in one short line.

## When something does not work

The skill says what to do at every failure of transcription, cutting and rendering. Do not try to fix `edit.py` in chat.

If after reopening `/video-editor` is not in the menu, check that step 6 passed and that the owner really quit Claude Code (Cmd+Q on Mac, Alt+F4 or closing every window on Windows) and did not only close one window. In File Explorer on Windows or in Finder on Mac, the folder `.claude/skills/video-editor` inside the system must hold three files.

A real break in the system itself belongs to Rick, not to live debugging in chat.
