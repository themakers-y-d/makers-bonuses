# Bringing a MAKERS system back on a new computer

You are Claude Code, opened in an empty folder on a new computer. The owner's old computer is gone, and their MAKERS system has a private backup on their GitHub, in a repository called `makers-backup` (sometimes `makers-backup-2`). Your job is to bring the whole system back into this folder. The owner does not need to read this file. Speak to them in Hebrew, in short messages; the lines in code blocks marked as messages are theirs word for word.

## Rules

Never create a repository, never push, never change anything on GitHub. This file only reads from the backup. Never print, paste or write down a token. If anything here does not match what you see, stop and say what you see.

### שלב 1. Where you are

Run `uname -s`. `Darwin` is a Mac. `MINGW`, `MSYS` or `CYGWIN` is Windows with Git Bash. If `uname` fails, you are on Windows without Git for Windows: say "צריך קודם את Git for Windows, כלי חינמי. מאשר שאתקין?", and after a yes run in PowerShell `winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements`, then ask them to close Claude Code completely, open it again in the same folder, and paste the message again. Stop there.

On a Mac, run `xcode-select -p`. If it fails, run `xcode-select --install` and say: "נפתח חלון של אפל. לחץ Install ואז Agree, וכתוב לי כשההתקנה הסתיימה." Wait.

Check the folder is empty, apart from hidden system files:

```bash
pwd; ls -A | grep -vE '^(\.DS_Store|desktop\.ini|\.obsidian)$'
```

Anything listed: say the folder is not empty, ask them to create a new empty folder, open Claude Code in it, and paste the message again. Stop.

### שלב 2. The message

Send:

```
מחזיר לך את המערכת מהגיבוי בגיטהאב. ככה זה ילך:
1) כלי קטן של גיטהאב יורד לתיקייה אחת בבית.
2) אתה מתחבר לגיטהאב עם קוד שאתן לך. תצטרך את הסיסמה של גיטהאב, ואם יש לך אימות דו שלבי, גם את הטלפון או את קודי השחזור.
3) כל המערכת יורדת לתיקייה הזו, ואז פותחים אותה באובסידיאן.
זה לוקח בערך עשר דקות. מאשר?
```

Wait for a yes.

### שלב 3. The GitHub tool and the login

Install the tool exactly as in step 7 of the install file of this gift, and log in exactly as in its step 8, including running the login in the background and sending the code: https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/backup/INSTALL-makers.md . Read only those two steps of it; everything else there is for a first install.

### שלב 4. Which backup

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe
"$G" repo list --limit 100 --json name,pushedAt --jq '.[] | select(.name | startswith("makers-backup")) | "\(.name) \(.pushedAt)"'
```

One line: that is the backup. Several: show the owner the names and the dates of the last upload, and ask which. None: say no backup was found on this GitHub account, and ask if they have another one.

### שלב 5. Bring it down

Say before: "מוריד עכשיו את המערכת. בין חצי דקה לכמה דקות, בלי פלט בינתיים."

```bash
G=~/.makers-backup/gh/bin/gh; [ -x "$G" ] || G=~/.makers-backup/gh/bin/gh.exe
U=$("$G" api user --jq .login); R=makers-backup
git clone -q -c core.longpaths=true -c credential."https://github.com".helper= -c credential."https://github.com".helper="!\"$G\" auth git-credential" "https://github.com/$U/$R.git" .restore-tmp \
  && mv .restore-tmp/.git . && rm -rf .restore-tmp && git remote rename origin makers-backup && { git branch -q --unset-upstream main 2>/dev/null || true; } && git config remote.makers-backup.push refs/makers/backup:refs/heads/main && git checkout -q -f main && git update-ref refs/makers/backup refs/remotes/makers-backup/main \
  && ls -d .claude/skills 1-me 2-makers 2>/dev/null; git remote
```

Replace `makers-backup` in `R=` with the name chosen in step 4. Expected: `.claude/skills` and at least one of `1-me` and `2-makers`, and the remote `makers-backup` (renamed from `origin` on purpose, so an ordinary `git push` never reaches the backup). The system is back, and the backup continues from here on its own: the hooks came back with it.

### שלב 6. Open it, and what did not come back

Send:

```
המערכת חזרה. עכשיו שני דברים:
1) באובסידיאן: Open folder as vault, ובוחרים את התיקייה הזו.
2) סוגרים ופותחים את Claude Code באותה תיקייה, כדי שהצוות והגיבוי ייטענו.
מה לא חזר, כי הוא אף פעם לא עלה לגיבוי: סיסמאות וטוקנים, קובץ .env, סרטונים וקבצים גדולים. חיבורים לכלים חיצוניים צריך לחבר מחדש, ורשימת החיבורים שלך מחכה בקובץ tools.md.
```

On a Mac the close is Cmd+Q, on Windows Alt+F4. If the owner had the backup running on the old computer, say once: the old computer must not run the backup any more; if it ever comes back to life, remove the hooks there first.
