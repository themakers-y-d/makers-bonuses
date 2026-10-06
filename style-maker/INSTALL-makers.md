# Morty, this one is for you

The owner brought a MAKERS gift to install: the reel style builder (style-maker). This file is written to you so you do not have to work out what to do. The owner does not need to read it. If you saved this file inside the system folder to read it, delete it when the install is done; it is not part of their vault. Speak to the owner in Hebrew, as always; the lines in quotation blocks below are theirs word for word.

## What it is, in one line

A skill that asks the owner how their animation should look and sound, writes their own style as a skill, and applies it to a vertical video in which they talk to camera. At the end there is an MP4 with animation and sound beside the original video.

Inside a MAKERS system it does one more thing. It reads what the system already knows about the owner in `1-me/` and their design brief if they have one, so it asks only the style questions it cannot answer itself, once, in one message. That is the one deliberate exception to the three-question cap: the answers become a style the owner reuses on every later video without being asked again. The layer file `makers.md`, installed with the skill, does that.

## Decisions already made for you

Do not spend questions on them.

**Who does the work: the Designer, in the main conversation, from step 2 to the end, install included, and on every run after it.** The job is how a video looks, and the skill is a conversation that stops for the owner several times. The install commands run in this same conversation: there is no worker in a window of its own to hand them to. You open the Designer's file in step 1 and it takes it from there. Nothing here touches a live system or money. No chain.

**The project:** `3-work/now/reels/`. If it exists, work inside it.

**Skills:** `style-maker`, and `/final-pass` at the end of every run. No `/connect-a-tool` and no `/ship-it-live`: nothing connects to an account and nothing goes live. The video stays on their computer.

**Your questions:** none. The skill asks about the design brief and the style itself, at the moment it matters.

**What is kept at the end:** their personal style as a skill, the video beside the original, and a dated record in `3-work/now/reels/` pointing at both.

## Two rules not to work around

**The skill goes into the user's skill folder, `~/.claude/skills/style-maker`, not the system's `.claude/skills`.** It is written with that path, and the personal style it writes is saved beside it. Anywhere else it cannot find its own files. A skill in that folder loads inside the system too.

**Downloading about 2 GB and running commands is the owner's decision.** The skill asks before it installs its tools, and nobody approves in their place.

## Order of work

### שלב 1. The move line, and what is about to happen

If this is the owner's first session and your own file asks for a first-session line, say it first, in one line, then continue here.

Then send this:

```
זו עבודה של המעצב שלך. הוא מתקין לך את בונה הסגנון לרילס, כאן בשיחה הזו. זה לוקח כמה דקות: ארבעה קבצים שיורדים מגיטהאב לתיקיית הסקילים שלך, וכפתור אחד בתפריט. זה לא נוגע בשום דבר חי.
תוך כדי יופיעו כמה בקשות לאשר כתיבה לתיקיית ההגדרות של Claude Code ולהריץ פקודות. זה רגיל, אשר. אם תרצה להסיר את זה אחר כך, אגיד לך איך בסוף.
```

Then open `2-makers/designer/designer.md`, become the Designer for the rest of this file, and continue at step 2.

### שלב 2. What is already installed

Step 1 has already told the owner in one paragraph what is about to happen and that nothing live is touched, and step 5 gives them the undo. Pasting the install message was the owner's yes. Do not stop to ask again; go through steps 2 to 4 without a message to the owner in between.

```bash
ls ~/.claude/skills/style-maker 2>/dev/null; find ~/.claude/skills -maxdepth 1 -name 'reel-style-*' 2>/dev/null
```

Nothing printed is a fresh install, the usual case. An existing `style-maker` means the owner once installed the free version: step 3 downloads over its four files, which is the update. Personal styles, `reel-style-...`, belong to the owner and are never touched.

### שלב 3. The install

Create the skill folder and enter it. Download straight into it: moving or deleting folders inside `~/.claude/skills` is blocked by Claude Code's own protection of its settings folder, so this install never does either.

```bash
mkdir -p ~/.claude/skills/style-maker && cd ~/.claude/skills/style-maker
```

(On Windows in Git Bash the same line works. Without Git Bash, in PowerShell: `New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\style-maker"; Set-Location "$env:USERPROFILE\.claude\skills\style-maker"`.) Then download four files into it, with exactly these names:

```
SKILL.md   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/SKILL.md
axes.md    https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/axes.md
kit.py     https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/kit.py
makers.md  https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/style-maker/RUNBOOK-makers.md
```

Chain each download to the `cd`, so the files land in the skill folder even if the working folder was reset. On Mac, and on Windows in Git Bash: `cd ~/.claude/skills/style-maker && curl -fsSL -o <file name> <url>`. On Windows in PowerShell: `curl.exe -fsSL -o "$env:USERPROFILE\.claude\skills\style-maker\<file name>" <url>`.

The fourth file is saved as `makers.md`, not under the name in its URL. That is the name the skill looks for.

### שלב 4. Check the download

Run each line on its own, so one failing does not hide the others:

```bash
cd ~/.claude/skills/style-maker && head -1 SKILL.md; head -1 makers.md
cd ~/.claude/skills/style-maker && grep -c 'makers.md' SKILL.md
cd ~/.claude/skills/style-maker && wc -c SKILL.md axes.md kit.py makers.md
cd ~/.claude/skills/style-maker && grep -l '^404' SKILL.md axes.md kit.py makers.md
```

Expected: the line `---`, then `# MAKERS layer for style-maker`, then a number of at least 2 (the skill knows about the layer), then a size for each of the four files and a total, none of them zero, and the last line printing nothing.

Anything wrong: download the bad file once more. If it fails again, tell the owner in one line that the download from GitHub does not go through, and stop. Nothing is deleted: pasting the install message again later finishes the job, and an older working version keeps working until then except for the file that failed.

All as expected: continue to step 5 without a message; the owner does not need the numbers.

### שלב 5. The button, and what you tell the owner

After step 4 passed, and only then, write the button: `.claude/commands/reel-style.md` in the system folder, with exactly this content:

```
---
description: בונה לך סגנון אנימציה משלך לרילס, או מלביש את הסגנון שלך על סרטון חדש
---

Open `2-makers/designer/designer.md` and become that agent for this request, in this conversation. Do not hand it to a worker in a window of its own: it cannot hold the back-and-forth this needs.

Then open `~/.claude/skills/style-maker/SKILL.md` and follow it from step 1. It sends you to the MAKERS layer in `makers.md` beside it.

$ARGUMENTS
```

Then say this:

```
בונה הסגנון לרילס מותקן אצלך.
עכשיו צא מ-Claude Code לגמרי ופתח אותו מחדש, כדי שהוא ייטען. במק: Cmd+Q, לא רק סגירת החלון. בווינדוס: Alt+F4 או סגירת כל החלונות של התוכנה, ובטרמינל כותבים /exit או לוחצים Ctrl+C פעמיים.
אחר כך לחץ /reel-style, או כתוב "תבנה לי סגנון לרילס", וגרור לכאן סרטון אנכי שבו אתה מדבר למצלמה. אם יש לך בריף עיצוב, הוא ימצא אותו לבד.
להסרה: מוחקים את התיקייה style-maker שבתיקיית הסקילים, את הקובץ reel-style.md שבתיקיית הפקודות של המערכת, ואת reel-studio שבתיקיית הבית אם כבר נוצרה. הסגנונות האישיים שלך, reel-style-<השם>, נשארים עד שתמחק גם אותם.
```

`/final-pass` still adds its closing line after this, as it does everywhere.

Anything learned during the install goes to the Archivist as a proposed line, never written directly.

## When something does not work

The skill itself says what to do at every failure of tool installation, transcription and rendering. Do not try to fix its code in chat.

If after reopening, `/reel-style` is not in the menu, check that step 4 passed and that the owner really quit Claude Code (Cmd+Q on Mac, Alt+F4 or closing every window on Windows) and did not only close one window.

A real break in the system itself belongs to Rick, not to live debugging in chat.
