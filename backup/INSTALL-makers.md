# Morty, this one is for you

The owner brought a MAKERS gift to install: the backup. This file is written to you so you do not have to work out what to do. The owner does not need to read it. If you saved this file inside the system folder to read it, delete it when the install is done; it is not part of their vault. Speak to the owner in Hebrew, as always; the lines in code blocks marked as messages are theirs word for word.

## What it is, in one line

A private copy of the whole system on the owner's GitHub, updated by itself while they work, so the day the computer is stolen, broken or wiped, the system comes back on a new one.

## Decisions already made for you

Do not spend questions on them.

**Who does the work: you, Morty, in the main conversation, from step 1 to the end.** A backup belongs to no trade in the team, and the install stops twice for the owner (a GitHub account, a login code), which a worker in its own window cannot do. No handoff, no chain.

**How it runs.** The engine is `.claude/skills/backup/backup.sh`, inside the system, so it is backed up with everything else and comes back with it. Two hooks in `.claude/settings.json` run it: at every session start, and after a reply at most once every three hours. There is no scheduled job at a fixed hour, on purpose: the computer may be closed at that hour, and the system only changes while the owner works.

**What it sends.** A snapshot of the current files, built in the engine's own index and kept on the ref `refs/makers/backup`. The owner's branch, staging area and the Archivist's restore points are never touched, and their local history never leaves the computer. Passwords, keys, `.env`, videos, audio, zip files and anything over 49 MB never go up; the list is `exclude-base`, and a file with a token inside is held back on its own.

**Where things live.** The GitHub command line tool, `gh`, goes into `~/.makers-backup/gh` in the home folder, with no admin rights, and is used only for the login and for creating the repository. The repository is called `makers-backup`, it is **private**, and it lives on the owner's own GitHub account.

**Skills:** `backup` (installed in step 9), and `/final-pass` at the end. No `/connect-a-tool` and no `/ship-it-live`: the repository is the owner's own private storage and nothing goes live.

**Your questions:** the ones in step 4, word for word, never more than three, in one message.

**The row in `tools.md`** is yours, written once in step 13, after step 11 proved a backup reached GitHub.

**What is kept at the end:** the `backup` skill folder, two hooks in `.claude/settings.json`, a `.git` folder in the system if there was none, one row in `tools.md`, and the private repository on GitHub.

## Rules not to work around

**The repository is private, always.** Never create it public, never change its visibility, and step 10 checks it before anything is sent.

**Never run `git config --global`,** and never change the owner's branch, commits or staging area. The engine never needs any of that.

**Never force a push,** never delete `.git` or anything in it, and never print, paste or write down a token. `gh` keeps its own login.

**A parent folder's repository does not count.** The history and the backup belong to this system folder, not to whatever it sits inside.

## Order of work

### שלב 1. The move line

If this is the owner's first session and your own file asks for a first-session line, say it first, in one line, then continue here.

Send this message:

```
גיבוי לא שייך לאף מקצוע בצוות, אז אני מקים אותו בעצמי, כאן בשיחה הזו.
```

### שלב 2. Where you are

First find out which computer this is, without asking: run `uname -s`. `Darwin` is a Mac. `MINGW`, `MSYS` or `CYGWIN` is Windows with Git Bash. Both continue below with the same commands unless a step says otherwise.

If `uname` itself fails, you are on Windows in PowerShell, without Git for Windows, and the backup needs it: the hooks run through it. Check in PowerShell whether it is installed but not found: `@("$env:ProgramFiles\Git\bin\bash.exe", "${env:ProgramFiles(x86)}\Git\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe") | Where-Object { Test-Path $_ }`.

• Nothing printed: say "כדי לגבות אני צריך את Git for Windows, כלי חינמי שדרכו Claude Code מריץ פקודות, ושהגיבוי עצמו נשען עליו. ההתקנה לוקחת כמה דקות, ווינדוס עשוי לפתוח חלון שמבקש אישור, ואז מאשרים. מאשר שאתקין?" After a yes, run in PowerShell, allowing ten minutes: `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements`. If winget is missing or fails, give the owner https://git-scm.com/download/win and ask them to run the file and accept the defaults. Then run the check above again.
• A path printed and `$env:CLAUDE_CODE_GIT_BASH_PATH` already set: the owner already reopened and it still does not run bash. Do not install again. Say: "Git for Windows מותקן, אבל Claude Code עוד לא משתמש בו. הפעל מחדש את המחשב, פתח את Claude Code והדבק שוב את הודעת ההתקנה." Stop here.
• A path printed and the variable not set yet: run `setx CLAUDE_CODE_GIT_BASH_PATH "<that path>"` and say: "Git for Windows מותקן. עכשיו סגור את Claude Code לגמרי, כולל החלון שהוא פתוח בו, ואם פתחת אותו מתוך טרמינל, סגור גם את הטרמינל. פתח אותו שוב באותה תיקייה, והדבק לי שוב את הודעת ההתקנה." Stop here. The next paste starts this file again and `uname` answers.

Then check that this is a MAKERS system: a `.claude/skills/` folder beside `1-me/` or `2-makers/`, in the folder you are working in.

```bash
pwd; ls -d .claude/skills 1-me 2-makers 2>/dev/null
```

`.claude/skills` and at least one of the other two printed: continue. Otherwise say in one sentence that this is not their MAKERS folder, ask them to open Claude Code in the folder they open every day and paste the message again, and stop without touching anything.

### שלב 3. What is already here

Silently, with no message to the owner:

```bash
case "$(uname -s)" in Darwin) xcode-select -p >/dev/null 2>&1 && echo "GIT READY" || echo "GIT MISSING MAC" ;; *) git --version >/dev/null 2>&1 && echo "GIT READY" || echo "GIT MISSING" ;; esac
[ -d .git ] && echo "OWN REPO"
[ -d .git ] && git remote get-url makers-backup 2>/dev/null | sed 's/^/REMOTE /'
ls -d .claude/skills/backup 2>/dev/null && echo "BACKUP SKILL PRESENT"
grep -l "backup.sh" .claude/settings.json 2>/dev/null && echo "HOOKS PRESENT"
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe; [ -x "$G" ] && { echo "GH PRESENT"; "$G" auth status 2>&1 | grep -E "Logged in to github.com" | sed 's/^ *//'; }
pwd | grep -qiE "Mobile Documents|OneDrive|Dropbox|Google Drive" && echo "IN A CLOUD FOLDER"
du -sk . 2>/dev/null | cut -f1 | sed 's/^/SIZE KB /'
```

The first line runs before anything else on purpose: on a Mac without Apple's developer tools, any `git` command opens Apple's install window, so this block calls `git` only inside a folder that already has its own `.git`, which proves git is there.

Read the result into facts:

• `GIT MISSING MAC`: the Mac has no developer tools yet, and step 6 installs them. A fresh Mac prints this, and it is the usual case, not a fault.
• `OWN REPO`: the Archivist already keeps restore points here. Nothing changes for them, and the backup never touches the remote they may call `origin`. No `OWN REPO` means step 10 creates this folder's own `.git`, even when a parent folder has one.
• `REMOTE`: a backup address is already connected, so this is a reinstall, and step 10 keeps it. If it is not a `github.com/.../makers-backup` address, ask the owner what it is before going on, and never replace it without their yes.
• `BACKUP SKILL PRESENT` or `HOOKS PRESENT`: an earlier install. Steps 9 and 12 update in place.
• `GH PRESENT` with a `Logged in` line: step 7 and step 8 are already done.
• `IN A CLOUD FOLDER`: the system sits in iCloud, OneDrive or Dropbox, against the workshop setup. The backup still works; say it once in step 4 and do not move anything.
• `SIZE KB`: over 1000000 (1 GB), say in step 4 that the first upload will take longer. Over 2000000 (2 GB), stop after step 4's message and ask before going on: GitHub accepts at most 2 GB in one upload, and the owner should first move videos and archives that are not already excluded out of the system folder.

### שלב 4. One message: what happens, and the questions

Send one message, built from the facts of step 3, before anything is installed. The opening:

```
מקים לך גיבוי למערכת. ככה זה ילך:
1) עותק פרטי של כל המערכת, כולל הצוות והסקילים, ייכנס לחשבון גיטהאב שלך. רק אתה רואה אותו.
2) מעכשיו הוא יתעדכן לבד בזמן שאתה עובד: בכל פתיחה של המערכת, ולכל היותר פעם בשלוש שעות. בלי שעה קבועה ובלי שהמחשב יצטרך להיות דלוק בלילה.
3) קבצי סיסמאות ומפתחות, קבצים שנראה שיש בהם טוקן, סרטונים וקבצים מעל 49 מגה לא עולים לשם. סיסמה שכתבת במילים בתוך פתק כן עולה, אז סיסמאות שומרים במנהל סיסמאות.
מה יבקשו ממך: חשבון גיטהאב, אישור בדפדפן עם קוד שאתן לך, וכמה אישורים בתוך Claude Code. זה לוקח 15 עד 30 דקות, ורובו רק לאשר.
```

Add only the lines that apply, in this order, word for word:

• `GIT MISSING MAC`: "במק שלך עוד אין את כלי המפתחים של אפל. ייפתח חלון שמבקש להתקין אותם, לוחצים Install, וזה לוקח בין חמש לחמש עשרה דקות."
• No `OWN REPO`: "אוסיף לתיקייה של המערכת תיקייה נסתרת אחת, שבה נשמרת ההיסטוריה. שום קובץ שלך לא זז."
• `IN A CLOUD FOLDER`: "שמתי לב שהמערכת יושבת בתיקייה שמסתנכרנת לענן. הגיבוי יעבוד גם ככה, ולא נוגע בזה עכשיו."
• `SIZE KB` over 1000000: "המערכת שלך גדולה, אז הגיבוי הראשון ייקח יותר זמן. הבאים מהירים."

Then the questions that apply, numbered in the order you ask them, word for word:

• Unless `GH PRESENT` with `Logged in`: "יש לך כבר חשבון בגיטהאב? (כן / לא / לא יודע)"
• Always: "מאשר שאתחיל?"

End your turn and wait. Nothing is installed before a yes.

### שלב 5. A GitHub account, only when there is none

"לא" or "לא יודע": send this, and wait:

```
גיטהאב הוא אתר נפרד, וחשבון גוגל לא מספיק. פותחים חשבון חינמי, שלוש דקות:
1) נכנסים לכתובת הזו:
https://github.com/signup
2) מכניסים מייל, סיסמה ושם משתמש באנגלית. שם קצר שקל לזכור.
3) גיטהאב שולח קוד למייל, מדביקים אותו בדף.
4) אם הוא שואל על תוכנית, בוחרים Free.
את הסיסמה של גיטהאב שמור גם מחוץ למחשב, למשל במנהל הסיסמאות בטלפון. ביום שהמחשב מת, זה המפתח לגיבוי. אם גיטהאב מבקש להפעיל אימות דו שלבי, הוא נותן גם קודי שחזור. שמור גם אותם, באותו מקום.
כשסיימת, כתוב לי "יש".
```

"לא יודע" usually means an account from long ago: the same message works, and GitHub says so if the mail is already taken; then they log in instead.

### שלב 6. Apple's developer tools, Mac only, only when missing

Only on `GIT MISSING MAC`:

```bash
case "$(uname -s)" in Darwin) xcode-select --install 2>&1 ;; esac
```

Say: "נפתח אצלך חלון של אפל. לחץ Install ואז Agree, וכתוב לי כשהוא אומר שההתקנה הסתיימה." Wait for their answer, then check:

```bash
case "$(uname -s)" in Darwin) xcode-select -p >/dev/null 2>&1 && git --version ;; esac
```

A version line: continue. Nothing: ask whether the window is still installing. If it never opened, run the install command once more and wait for their answer again.

### שלב 7. The GitHub tool, into the home folder

Skip when `GH PRESENT`. The commands are the same on Mac and on Windows in Git Bash; the script picks the right file and checks its fingerprint, so what runs is exactly what was tested. Say before: "מוריד כלי קטן של גיטהאב, בערך 15 מגה, לתיקייה אחת בבית. כמה שניות עד דקה של שקט, זה תקין."

```bash
(
V=2.102.0; D=~/.makers-backup; mkdir -p "$D" && cd "$D" || exit 1
case "$(uname -sm)" in
  "Darwin arm64")  F=gh_${V}_macOS_arm64.zip;    S=da922c20d1792e5b2cbf375593d7a658acf034c12c84e007e71c76ef959c337e ;;
  "Darwin x86_64") F=gh_${V}_macOS_amd64.zip;    S=b245f24eb2bf5f75b426b4c26da3651a107f8d5b6f4fddfbfccc5679041378b3 ;;
  MINGW*|MSYS*|CYGWIN*)
    case "$PROCESSOR_ARCHITECTURE" in
      ARM64) F=gh_${V}_windows_arm64.zip; S=5dcf12aa8525eabd0c46ec414f323ab6cf65229fc2cd46543cc705001bbaf223 ;;
      *)     F=gh_${V}_windows_amd64.zip; S=ae64e556ecc240b200f7eba60d550e4bb60d78e860e69dd88c449405b86067f4 ;;
    esac ;;
  *) echo "UNKNOWN COMPUTER $(uname -sm)"; exit 1 ;;
esac
REL=https://github.com/cli/cli/releases; curl -fsSL --retry 3 -o gh.zip "$REL/download/v${V}/${F}" || { echo "DOWNLOAD FAILED"; exit 1; }
if command -v shasum >/dev/null 2>&1; then H=$(shasum -a 256 gh.zip | cut -d' ' -f1); else H=$(sha256sum gh.zip | cut -d' ' -f1); fi
[ "$H" = "$S" ] || { echo "FINGERPRINT MISMATCH"; rm -f gh.zip; exit 1; }
rm -rf gh unpack && mkdir unpack && { unzip -q gh.zip -d unpack 2>/dev/null || powershell.exe -NoProfile -Command "Expand-Archive -Force gh.zip unpack"; } || { echo "UNPACK FAILED"; exit 1; }
if [ "$(ls unpack | wc -l | tr -d ' ')" = 1 ] && [ -d "unpack/$(ls unpack)" ]; then mv "unpack/$(ls unpack)" gh; else mv unpack gh; fi; rm -rf unpack gh.zip
G=gh/bin/gh; [ -x "$G" ] || G=gh/bin/gh.exe; "$G" --version | head -1
)
```

The parentheses keep the folder change inside this block, so the next steps still run from the system folder.

Expected: `gh version 2.102.0`. `DOWNLOAD FAILED`: try once more; again, tell the owner the download from GitHub does not go through right now, and stop; pasting the install message later continues from here. `FINGERPRINT MISMATCH`: stop and tell the owner in one line that the file that arrived is not the expected one, so nothing was installed. Never skip the check.

The unpack works whether the zip has one top folder (Mac) or its files at the top (Windows), and on Windows without `unzip` it falls back to PowerShell.

### שלב 8. The login, with a code

Skip when step 3 showed `Logged in`. The login waits for the owner in the browser, so **run it in the background** (your Bash tool's background option), then read its output after about five seconds:

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe; "$G" auth login --hostname github.com --git-protocol https --web --clipboard 2>&1
```

The output has the one-time code, eight characters with a dash in the middle, as `One-time code (XXXX-XXXX) copied to clipboard` or as `First copy your one-time code: XXXX-XXXX`. It is already on their clipboard. Do not count on a browser opening by itself; send the address. Send:

```
עכשיו ההתחברות. הקוד שלך הוא XXXX-XXXX, והוא כבר מועתק.
1) פתח בדפדפן את https://github.com/login/device
2) התחבר לגיטהאב אם הוא מבקש, והדבק את הקוד.
3) לחץ Authorize github.
כתוב לי כשהדף אומר שההתחברות הצליחה.
```

When they answer, check, on Mac and Windows alike:

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe; "$G" auth status 2>&1 | grep -E "Logged in to github.com" ; "$G" api user --jq .login
```

A `Logged in` line and a username: continue, and keep the username for step 10. Nothing yet: the code expires after about fifteen minutes; run the login again in the background and send the new code.

### שלב 9. The engine and the skill, into the system

Download the three files of the skill straight into the system's skill folder. They come from one fixed version of the gift, and each file is checked against its fingerprint:

```bash
D="$(pwd)/.claude/skills/backup"; mkdir -p "$D" && curl -fsSL --retry 3 -o "$D/SKILL.md" "https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/4c9f7ea3d4352b09bc4c1ee7469f8afebc7faf98/skills/backup/SKILL.md" || echo "PROBLEM SKILL.md did not download"
D="$(pwd)/.claude/skills/backup"; mkdir -p "$D" && curl -fsSL --retry 3 -o "$D/backup.sh" "https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/4c9f7ea3d4352b09bc4c1ee7469f8afebc7faf98/skills/backup/backup.sh" || echo "PROBLEM backup.sh did not download"
D="$(pwd)/.claude/skills/backup"; mkdir -p "$D" && curl -fsSL --retry 3 -o "$D/exclude-base" "https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/4c9f7ea3d4352b09bc4c1ee7469f8afebc7faf98/skills/backup/exclude-base" || echo "PROBLEM exclude-base did not download"
D="$(pwd)/.claude/skills/backup"; if command -v shasum >/dev/null 2>&1; then H="shasum -a 256"; else H="sha256sum"; fi; ( cd "$D" && printf '%s  %s\n' dbd202c519632975aa2a22ca58a015c85338a131b0d00970bbbad52ddb5ecbb4 SKILL.md db5e7ccdad04bab513535de5ead85ca7f02c1101f5aa75004b5d4c2adc0bb4ea backup.sh 6b449dc67601b2c90b99ae605aedbbcd52b6caae37f1598d934339e31f0978a4 exclude-base | $H -c - )
```

Expected: `SKILL.md: OK`, `backup.sh: OK`, `exclude-base: OK`. `FAILED`: download that file once more and check again; if it fails again, tell the owner the download from GitHub does not go through, and stop. Claude Code asks the owner to approve writing into `.claude/`; that was announced in step 4.

### שלב 10. The private repository

From the system folder. Only when there is no `.git` here (step 3 did not print `OWN REPO`), create one; the owner agreed in step 4:

```bash
[ -d .git ] || git init -q -b main && echo "REPO READY"
```

Then create the private repository on their GitHub and connect it under the remote name `makers-backup`, never `origin`: an `origin` is what any ordinary `git push` sends the owner's real history to, and the backup must never be one command away from that. Skip the creation when step 3 showed a `REMOTE`:

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe
U=$("$G" api user --jq .login)
if "$G" repo view "$U/makers-backup" >/dev/null 2>&1; then echo "EXISTS"; else "$G" repo create makers-backup --private --description "MAKERS system backup" >/dev/null && echo "CREATED"; fi
git remote get-url makers-backup >/dev/null 2>&1 || git remote add makers-backup "https://github.com/$U/makers-backup.git"
git config remote.makers-backup.push refs/makers/backup:refs/heads/main
git remote get-url makers-backup
"$G" repo view "$U/makers-backup" --json visibility --jq .visibility
```

The last line must be `PRIVATE`. Anything else: stop, say so, and do not send anything.

`EXISTS` on a first install means a `makers-backup` from before, maybe from another computer. Ask, word for word: "בחשבון הגיטהאב שלך כבר יש גיבוי בשם makers-backup. זה גיבוי של המערכת הזו ממחשב אחר, או משהו ישן שאפשר לא לגעת בו? אם זה מחשב חדש ואתה רוצה להחזיר ממנו את המערכת, תגיד לי, וזה מסלול אחר." Then, by the answer:

• "Old, leave it": create `makers-backup-2` with the same command, connect it under the same remote name, `makers-backup`, and use the new address from here on.
• "This system, from another computer that is gone": connect it under the remote name `makers-backup`, then run `git fetch -q makers-backup main && git update-ref refs/makers/backup refs/remotes/makers-backup/main`. The next backup is added on top of the old ones, so the history is kept and what is in this folder now becomes the latest version. Say that in one sentence before running it.
• "I want the old system back on this computer": this folder already has a system, and a restore goes into an empty folder. Stop here and send: "כדי להחזיר את המערכת מהגיבוי, צור תיקייה ריקה חדשה, פתח בה את Claude Code, והדבק את הודעת השחזור מדף המתנה, תחת ׳ביום שהמחשב מת׳." Nothing in this folder was changed.

Now let git use the login of the GitHub tool for this repository only:

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe
git config --local --unset-all credential."https://github.com".helper 2>/dev/null
git config --local --add credential."https://github.com".helper ""
git config --local --add credential."https://github.com".helper "!\"$G\" auth git-credential"
git ls-remote makers-backup >/dev/null && echo "ACCESS OK"
```

`ACCESS OK`: continue. Anything else: run step 8 again, then this block.

### שלב 11. The first backup

Say before: "שולח עכשיו את הגיבוי הראשון. זה יכול לקחת בין חצי דקה לכמה דקות, ובמערכת גדולה יותר, בלי שום פלט בינתיים. זה תקין, ואעדכן אותך."

Start it detached, so a big first upload is never cut off by a command timeout, and an upload cannot resume once cut:

```bash
nohup bash .claude/skills/backup/backup.sh run >/dev/null 2>&1 < /dev/null & echo STARTED
```

Then check every minute or so, with no message to the owner between checks unless five minutes passed (then one line, "עדיין עולה, זה תקין"):

```bash
ls -d .git/makers-backup/lock >/dev/null 2>&1 && echo "STILL RUNNING" || bash .claude/skills/backup/backup.sh status
```

When it no longer says `STILL RUNNING`, `status` shows the result: `LAST GOOD BACKUP` with today's time is the success.

No `LAST GOOD BACKUP` and a `LAST PROBLEM` line: handle it with the skill file you just installed, section "Back up now", then start this step again. When `status` lists files kept out on purpose, tell the owner which ones and why in one sentence, and that the skill knows how to bring a file back in once the secret is out of it.

### שלב 12. The hooks

The hooks go into `.claude/settings.json` of the system. If the file does not exist, create it with exactly this content. If it exists, add these two entries with your editing tool, keeping everything already there, inside the existing `hooks` object if there is one; never rewrite the file from scratch. If `HOOKS PRESENT` came up in step 3, check that both are there and leave them.

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/skills/backup/backup.sh\" start", "timeout": 120 } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/skills/backup/backup.sh\" stop", "timeout": 120 } ] }
    ]
  }
}
```

Then read the file back and confirm it is valid JSON:

```bash
grep -c "backup.sh" .claude/settings.json; { python3 -m json.tool .claude/settings.json || py -m json.tool .claude/settings.json; } >/dev/null 2>&1 && echo "JSON OK" || echo "JSON NOT CHECKED"
```

Expected: `2` and `JSON OK`. `JSON NOT CHECKED` means no Python was there to check it, not that it is broken: open the file and read it through, every bracket and comma. A broken settings file stops every hook in the system, not only this one.

### שלב 13. Proof, and the record

Send the owner the address of their backup and let them see it with their own eyes:

```
הגיבוי הראשון נמצא בגיטהאב. תפתח את הקישור ותראה את התיקיות של המערכת שלך: https://github.com/<username>/makers-backup
ליד השם כתוב Private, כלומר רק אתה רואה אותו.
```

Then add one row to the table in `tools.md`, never rewriting the file:

```
| GitHub, makers-backup | read + write. The login reaches every repository on the account; the backup only ever writes to makers-backup | <today's date> | Remove the two backup hooks from .claude/settings.json; the copy stays on GitHub until the repository is deleted there |
```

And offer the Archivist one proposed line for `4-learned/log.md`: the date, "גיבוי למערכת הוקם, לגיטהאב פרטי, מתעדכן בפתיחה ובזמן עבודה".

Run `/final-pass` on what you are about to hand back.

### שלב 14. Reopen Claude Code, and next time

Hooks and skills load only when Claude Code opens. Send:

```
זהו, הגיבוי חי. נשאר צעד אחד: לסגור ולפתוח את Claude Code, כדי שהגיבוי האוטומטי ייכנס לתוקף.
במק: Cmd+Q, ולא רק סגירת החלון. בווינדוס: Alt+F4, או סגירת כל החלונות של התוכנה.
ופותחים שוב באותה תיקייה.
מעכשיו, כדי לבדוק, אומרים לי "מתי היה הגיבוי האחרון?". ואם הגיבוי לא מצליח יומיים ברצף, אני אגיד לך בעצמי בפתיחה.
```

If you saved this file inside the system folder to read it, delete it now.
