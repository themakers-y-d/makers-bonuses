---
name: backup
description: Checks, runs and restores the off-site backup of this MAKERS system, the private GitHub copy that the backup engine updates while the owner works. Use whenever the owner says things like "מתי היה הגיבוי האחרון", "הגיבוי עובד?", "תגבה עכשיו", "גבה", "תחזיר את הקובץ מהגיבוי", "מה היה בקובץ ביום שלישי", "קנו לי מחשב חדש", "המחשב התקלקל", "תכבה את הגיבוי", "is my backup working", "back up now", "restore from backup", and whenever a session-start line begins with MAKERS BACKUP. Always use this instead of running git commands by hand on the backup. Undoing something from this session stays with Rick and his restore points; this skill is the copy that lives off the computer.
---

# The backup

The engine is `backup.sh`, beside this file. It builds a snapshot of the system folder in its own index, keeps it on the ref `refs/makers/backup`, and sends it through the git remote named `makers-backup` (never `origin`) to the private repository on the owner's GitHub, as its `main`. The owner's own branch, staging area and the Archivist's restore points are never touched and never leave the computer.

It runs on its own from two hooks in `.claude/settings.json`, detached so it never holds the session: at every session start, and after a reply, at most once every three hours. Speak to the owner in Hebrew, in one or two sentences, and never paste raw output at them.

## Is it working

```bash
bash .claude/skills/backup/backup.sh status
```

Say when the last good backup was, in days or hours, and what is kept out on purpose. When there was a problem, say it in their words and offer to fix it now.

## Back up now

```bash
bash .claude/skills/backup/backup.sh now
```

`BACKED UP` is the only success. `PROBLEM` names the cause; the usual ones:

• `no internet connection`: say so, nothing is lost, the next session retries.
• `GitHub refused the upload` with `Authentication` or `403` in it: the login expired. Run `~/.makers-backup/gh/bin/gh auth login --web --clipboard --git-protocol https` in the background (on Windows the file is `gh.exe`), give the owner the code from its output and https://github.com/login/device, wait for `Logged in`, and back up again.
• `GitHub refused the upload` with `rejected` or `fetch first`: GitHub has snapshots this computer does not, almost always because the backup was also connected on another computer. Never force. Say that one backup can only come from one computer, and ask which computer is the main one.

## Files kept out on purpose

`status` lists them. A file with something that looks like a token or key inside is kept out so the secret never reaches GitHub. The fix is to move the secret out, into `.env`, which is never backed up; the next backup sees the file is clean and brings it back in by itself. A password written in plain words in a note is not recognised and does go up, so passwords belong in a password manager. A separate git project inside the folder is stored as a pointer only; its files are not in the backup. A file over 49 MB stays out: GitHub refuses files over 100 MB and warns from 50, so the backup stops before that. Videos, audio and zip files are never backed up, by the list in `exclude-base`.

## Bring back a file from the backup

First back up now, so what exists today is saved before anything is replaced. Then find the versions:

```bash
git log --format='%h %ad' --date=format:'%d.%m.%Y %H:%M' refs/makers/backup -- "<path>"
```

Show the owner the dates, and after they pick one, write that version beside the current file, never over it:

```bash
git show <hash>:"<path>" > "<path without .md>.restored.md"
```

Say which file you wrote, and let them decide whether it replaces the current one. A file deleted on the computer is restored the same way, from the last snapshot that still has it. Going back on something from this session is Rick's, from the Archivist's restore points; this backup is for what is gone from the computer.

## A new computer

The whole system comes back from GitHub. The full steps are in the gift's `RESTORE.md`, written for a fresh Claude Code in an empty folder: https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/backup/RESTORE.md

## Switch it off

Remove the two backup hooks from `.claude/settings.json`. The GitHub copy stays until the owner deletes the repository on github.com, under Settings of `makers-backup`. Update the backup row in `tools.md`.
