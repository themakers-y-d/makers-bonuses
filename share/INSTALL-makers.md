# Morty, this one is for you

The owner wants the skill that shares their work on the MAKERS participants' market (שוק של מייקרז) (themakers.co.il/bonus/share). This file installs it. The owner does not need to read it. If you saved this file inside the system folder to read it, delete it when the install is done. Speak to the owner in Hebrew, as always; the lines in code blocks marked as messages are theirs word for word.

## What gets installed

One skill, `share-with-makers`, into `.claude/skills/share-with-makers/SKILL.md`. Nothing else changes: no hooks, no settings, no row in `tools.md`, nothing connected. The skill itself never uploads anything; it builds one file and the owner drags it to the page.

## Order of work

### 1. The move line

```
מתקין את סקיל השיתוף. זה קובץ אחד, ולוקח דקה.
```

### 2. This is a MAKERS system

```bash
pwd; ls -d .claude/skills 1-me 2-makers 2>/dev/null
```

`.claude/skills` and at least one of the other two printed: continue. Otherwise say in one sentence that this is not their MAKERS folder, ask them to open Claude Code in the folder they open every day and paste the message again, and stop without touching anything.

### 3. Download the skill

On Windows use `curl.exe` if `curl` is not found.

```bash
mkdir -p .claude/skills/share-with-makers
curl -fsSL -o .claude/skills/share-with-makers/SKILL.md https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/share-with-makers/SKILL.md
head -3 .claude/skills/share-with-makers/SKILL.md
```

The first printed line must be `---` and the second `name: share-with-makers`. Anything else (an error page, an empty file): delete the folder, say the download failed and ask the owner to try again in a minute.

If the folder already existed, this was an update, and the new file replaced the old one. Say so in the last message.

### 4. Final pass, then the last message

Run `/final-pass`. Then:

```
סקיל השיתוף מותקן. כדי שהוא ייטען, צריך לסגור את Claude Code לגמרי ולפתוח אותו מחדש באותה תיקייה.
אחרי הפתיחה, אומרים לי: "אני רוצה לשתף עם המייקרז את" ומה שבנית, ואני מכין את זה.
```
