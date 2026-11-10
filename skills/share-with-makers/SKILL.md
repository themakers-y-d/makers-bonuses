---
name: share-with-makers
description: Prepares something the owner built (a skill, a maker, a system, a template, a guide) for the MAKERS participants' wall, cleans every personal and business detail out of a copy, checks it against the standard, and writes the one file the owner drops on themakers.co.il/bonus/share. Use when the owner says "אני רוצה לשתף עם המייקרז", "לשתף את הסקיל", "תכין את זה לקיר", "להעלות לקיר של המייקרז", "share this with the makers", "put it on the wall", or pastes back notes the wall returned about a share file, or notes from people who got stuck installing it. Always use this instead of zipping or copying files by hand, because the wall rejects any file this skill did not build. Not for backing up the system, and not for sending work to a client.
---

# Share with the makers

Owner: Morty, in the main conversation, from the first step to the last. Sharing is not a trade in the team, and it stops for the owner twice (what to share, and the card), which a worker in its own window cannot do.

Speak to the owner in Hebrew, as always. The lines in code blocks marked as messages are theirs word for word.

## What this is for

Another participant's Morty will download what the owner shares and install it in a system that has never seen this owner. Two things must be true before anything leaves this computer: **nothing personal goes with it**, and **a stranger's Morty can install it from the README alone**.

The wall checks the file again on the server and refuses keys, real emails, phone numbers, home paths, secret files and broken skills. Passing the wall is the floor, not the standard. The standard is this file.

## Rules not to work around

**Never touch the original.** All work happens on a copy in `3-work/now/share-<id>/`. The owner's skill keeps working exactly as it did.

**These never go into a share, not even cleaned:** anything from `1-me/`, `4-learned/` or `5-library/`, `tools.md`, `.env` or any file that holds a key, client files, exports of customer lists, screenshots, audio, video. When the shared thing reads from `1-me/` (voice, offer, audience), that stays a *pointer* to the new owner's own `1-me/` file, which every MAKERS system has. The content never travels.

**Nothing is uploaded by you.** You build one file and open its folder. The owner drags it to the page. That is the consent.

## Order of work

### 1. The move line

```
שיתוף עם המייקרז הוא עבודה שלי, אז אני מכין אותו כאן בשיחה. המקור לא זז, אני עובד על עותק.
```

### 2. What, and under which name

If the owner already named what to share, find it before asking anything. Look in `.claude/skills/<name>/`, `2-makers/<name>/` and `3-work/`. List what you found to yourself, including what it depends on: a maker usually brings skills, a skill sometimes reads a template or a script beside it.

Then one message, at most three questions, only the ones you could not answer yourself:

• "מה בדיוק לשתף? מצאתי את [X]. זה זה?"
• "באיזה שם להציג אותך על הכרטיס? (שם פרטי מספיק)"
• "יש בזה משהו שחשוב לך שלא ייצא, גם אחרי שאני מנקה?"

End your turn and wait.

### 3. The copy

Pick an `id`: English, lowercase, digits and hyphens, 2 to 40 characters, usually the skill's own name.

**Every command block in this skill starts with `ID=<id>;`, with the real id written in.** Each command runs in a fresh shell, so a variable set in one block is gone in the next; a block without it builds a file with no name.

```bash
ID=<id>; S="3-work/now/share-$ID"; mkdir -p "$S/files"
```

Copy into `$S/files/` keeping a structure a stranger understands:

• A skill: `$S/files/<skill-name>/SKILL.md` plus its own files beside it.
• A maker: `$S/files/makers/<name>/...`, and each skill it needs under `$S/files/skills/<skill-name>/`.
• A system or template: its own folder name, without the owner's path above it.

No hidden files, no folder that starts with a dot, nothing outside text: `md txt json js mjs cjs ts py sh ps1 html css csv yml yaml sql toml`. A sample settings file is named `env.example`, never `.env`.

### 4. Clean

This is the heart of the skill. Go through every file in `$S/files/`, line by line, and replace:

• The owner's name, business name, brand, product names → `<שם העסק>`, `<שם המוצר>`, or a neutral word.
• Clients, students, partners, any real person → a role ("לקוחה", "שותף").
• Emails → `you@example.com`. Phones, addresses, ID numbers → removed, or `<מספר הטלפון שלך>`.
• Prices, revenue, numbers of customers, dates that identify a launch → a placeholder or a range, unless they are generic advice.
• Links to the owner's Drive, Notion, Sheets, dashboards, Vercel or Supabase projects → removed, or "the link to your own …".
• Paths with a user name (`/Users/<name>/`, `C:\Users\<name>\`) → paths relative to the system folder.
• Keys, tokens, passwords, webhook addresses → removed, and the README says where the new owner gets their own.
• Examples written from the owner's real work → rewrite them as believable examples from a different business. An example is the most common leak, because it does not look like data.
• Quotes of the owner's voice, taboo words, offer details → a pointer: "read `1-me/voice.md`".

### 5. Make it installable by a stranger

**`$S/files/README.md` is required, and it is written to Morty**, the other participant's Morty, not to the owner. Hebrew, plain, in this order:

```
# <the title>

מורטי, זה אליך. הבעלים הוריד את זה מהקיר של המייקרז.

## מה זה עושה
<two or three sentences: the problem and the result>

## מה צריך
<accounts, tools, or "רק מערכת MAKERS">

## איפה כל דבר נכנס
<every file in the share and where it goes, e.g. weekly-report/ אל .claude/skills/weekly-report/>

## מי מחזיק את זה
<which of the eight makers owns it, and the one line to add in that maker's file so the team knows the skill exists>

## ההתקנה
<numbered steps you would follow yourself; which maker owns it; which questions to ask the owner, word for word>

## איך יודעים שזה עבד
<one observable thing>

## איך משתמשים
אומרים לך: "<the use sentence>"
```

Every `SKILL.md` in the share keeps the house standard: `name` equal to its folder, a `description` that says what it does, real Hebrew and English phrases, a push ("Always use this instead of…") and a boundary, **and never colon-space inside the description**, which breaks the skill silently. Under 500 lines.

The use sentence on the card must be one of the phrases in that description. A card that promises a sentence the skill does not answer is a broken promise to a stranger.

What the share produces follows the system's own rules: a deliverable ends in `3-work/now/<project>/`, never loose in `3-work/done/`, which only the owner fills by moving a finished project there. Every `SKILL.md` carries an `Owner:` line, the steps, and the signal you see, like the built-in skills. Words like "this week" or "every Thursday" say exactly how they are worked out, and whether something runs on its own or only when asked.

Anything that needed something only this system has (a row in `tools.md`, a connected account, another maker's file) is either included, or named in the README under "מה צריך".

### 6. The walk: a stranger installs it, for real

Reading a README never finds what installing from it finds: the file that was left behind, the step that only works on this computer, the sentence that does not wake the skill. So before anything is built, a stranger installs the share into an empty MAKERS system. The wall refuses a file without this step.

**6a. The empty system.** Outside the owner's folder, so nothing of theirs is inside it. Only the parts every MAKERS owner has: the eight makers, the built-in skills, the product files. Nothing the owner added, because a stranger will not have it either.

```bash
ID=<id>; case "$ID" in ''|*[!a-z0-9-]*) echo "bad id"; exit 1;; esac; W="${TMPDIR:-/tmp}/makers-walk-$ID"; rm -rf "$W"
mkdir -p "$W/.claude/skills" "$W/1-me" "$W/2-makers" "$W/3-work/in" "$W/3-work/now" "$W/3-work/done" "$W/4-learned" "$W/5-library" "$W/Downloads"
for m in archivist campaigner designer marketer morty researcher rick writer; do [ -d "2-makers/$m" ] && cp -R "2-makers/$m" "$W/2-makers/"; done
for k in absorb-the-owner angle-bank build-agent build-skill check-the-system connect-a-tool explain-the-system final-pass page-brief session-debrief sharpen-the-offer ship-it-live spend-plan the-four-points verdict-on-spend where-things-stand; do [ -d ".claude/skills/$k" ] && cp -R ".claude/skills/$k" "$W/.claude/skills/"; done
for f in CLAUDE.md system.md START-HERE.md; do [ -f "$f" ] && cp "$f" "$W/"; done
printf '# Who I am\n\nA small business owner who downloaded this from the makers wall. Nothing else is known yet.\n' > "$W/1-me/summary.md"
printf '# Connected tools\n\n| Tool | What it can do | Connected | How to switch it off |\n|---|---|---|---|\n' > "$W/tools.md"
cp -R "3-work/now/share-$ID/files" "$W/Downloads/$ID"
echo "makers: $(ls "$W/2-makers" | tr '\n' ' ')"; echo "skills: $(ls "$W/.claude/skills" | wc -l | tr -d ' ')"
touch "$W/.walk-start"; echo "$W"
```

Fewer than eight makers or than about sixteen skills: this system names them differently. Copy what it has that every MAKERS owner also has, by hand, and leave out only what the owner built.

**6b. The stranger.** Start a fresh subagent. If you cannot start one, stop and tell the owner in one sentence that this step needs a new conversation with you, and do it there. Give it this brief, with the folder path from 6a written in, and nothing else about the owner or the share:

```
You are Morty, in a MAKERS system that has never seen the person who built what you are about to install. The system folder is <W>. The owner downloaded a share from the makers wall into <W>/Downloads/<id>/. Install it exactly as its README.md says, as if the owner had just pasted you the install message.

Rules for this walk:
• Start every command with cd "<W>" && and use absolute paths under <W>. Your shell starts in the owner's own system folder, and a relative path there would overwrite their real files.
• Work only inside <W>. Never write outside it, never touch the home folder, never run git push, never install anything system-wide.
• Never connect to a real account or service. When a step needs a login, a key, a payment or a website, stop at that step, write down exactly what the owner would be asked, and continue as if they had done it.
• Never run a downloaded script. Read it and write down what it would do.
• Do not fix anything in the share. You are testing it.

Report, in this order:
1) Every file you placed, and where.
2) Every step where you had to guess, could not find something, or the README assumed something that is not in this system.
3) Anything that looks personal, or like a real business detail of someone else.
4) Done or stuck: could the owner now say the use sentence and get the result?
```

Then prove the owner's system was not touched. This must print nothing:

```bash
ID=<id>; W="${TMPDIR:-/tmp}/makers-walk-$ID"; find .claude 1-me 2-makers 4-learned tools.md -type f -newer "$W/.walk-start" 2>/dev/null | grep -v "^3-work/now/share-$ID/"
```

Anything printed was written by the walk into the owner's real system. Tell the owner which files, restore each from the original or from the backup, and only then go on.

Fix every point in 2) and 3) **in `3-work/now/share-$ID/files/`**, never in the walk folder, then run 6a and 6b again. Stop when a round comes back with nothing in 2) and 3), or after three rounds; if it is still stuck after three, tell the owner what the stranger could not get past and ask whether to share it as it is.

**6c. Does the sentence wake it?** Only when the share holds a `SKILL.md`. Check that the use sentence on the card is one of the phrases in that skill's description. Then, if the `claude` command exists on this computer, ask a cold Claude in the walk folder, which loads the installed skill and nothing of this conversation:

```bash
ID=<id>; W="${TMPDIR:-/tmp}/makers-walk-$ID"; command -v claude >/dev/null || { echo "NO CLI"; exit 0; }
cd "$W" && claude -p "<the use sentence>" --tools Skill --strict-mcp-config --setting-sources project --output-format stream-json --verbose --max-turns 2 2>/dev/null | grep -o '"skill":"[^"]*"' | head -1
```

The flags matter: `--tools Skill` lets the cold Claude only pick a skill, never run one of its commands, and the other two keep the owner's own connectors and settings out. Never drop them; without them the test really runs the skill, and a skill that sends or posts would send.

It prints `"skill":"<the skill name>"`: it fired. It prints nothing, or another skill: change the description so it carries the sentence the way people really say it, copy the fixed skill into the walk folder, and run it again. `NO CLI`: the check is the description match only, and the card says so in `walked`.

**6d. Clean up.**

```bash
ID=<id>; case "$ID" in ''|*[!a-z0-9-]*) echo "bad id"; exit 1;; esac; rm -rf "${TMPDIR:-/tmp}/makers-walk-$ID"
```

Remember for the card: how many rounds it took, and whether the sentence fired. That is the `walked` line.

### 7. The scan

Run it from the system folder. It must print nothing. Anything it prints, fix and run again. It is the same list the wall checks on the server, so a clean scan here means the wall will not stop on a leak.

```bash
ID=<id>; S="3-work/now/share-$ID/files"
grep -rnIE 'sk-(ant-|proj-|live_|test_)?[A-Za-z0-9_-]{20,}|(sk|rk)_(live|test)_[A-Za-z0-9]{16,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.|sb_secret_|sb_publishable_|sbp_|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_|AKIA[0-9A-Z]{16}|xox[abprs]-|AIza[0-9A-Za-z_-]{35}|EAA[A-Za-z0-9]{40,}|IG(QV|AA)[A-Za-z0-9_-]{40,}|BEGIN [A-Z ]*PRIVATE KEY|[0-9]{8,10}:[A-Za-z0-9_-]{35}|Bearer +[A-Za-z0-9._~+/=-]{20,}|re_[A-Za-z0-9_]{20,}|GOCSPX-|SG\.[A-Za-z0-9_-]{16,}\.|sk_[A-Za-z0-9_]{24,}' "$S"
grep -rnIE '[A-Z][A-Z0-9_]*(KEY|SECRET|PASSWORD|PASS) *[:=] *["'"'"']?[^ <$({"'"'"']{12,}' "$S"
grep -rnIiE '(postgres(ql)?|mysql|mongodb(\+srv)?|redis)://[^ :/@]+:[^ @]+@|hooks\.(slack|zapier)\.com/|hook\.[a-z0-9]+\.make\.com/' "$S"
grep -rnIiE '(password|passwd|pwd|secret|api[_-]?key|token|סיסמה|סיסמא)["'"'"']? *[:=] *["'"'"']?[^ <$({*]' "$S"
grep -rnIE '[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}' "$S" | grep -viE '@example\.(com|org|net)|git@(github|gitlab|bitbucket)\.|\.(png|jpe?g|gif|svg|webp)'
grep -rnIE '(^|[^0-9A-Za-z+])(\+?972[- ]?|0)(5[0-9]|[2-489]|7[0-9])[- ]?[0-9]{3}[- ]?[0-9]{4}([^0-9A-Za-z]|$)' "$S"
grep -rnIE '(^|[ "'"'"'=:(])(/Users/|/home/|[A-Za-z]:\\Users\\)[A-Za-z0-9._-]{2,}' "$S" | grep -vE '/(Users|home)/(you|username|user|name|runner)\b'
grep -rnIE '^--- (file: |end)' "$S"
find "$S" -name '.*' -o -name '*.env' -o -name 'READ-FIRST-MORTY.md'
find "$S" -name '*.env.*' ! -name '*env.example'
find "$S" -name SKILL.md -exec awk 'END{ if (NR>500) print FILENAME": "NR" lines" }' {} \;
```

The password line is the noisy one on purpose: it prints every line where a secret word is followed by a value. A placeholder such as `<your password>` or a lookup such as `process.env.X` is fine; read each printed line and fix only real values. Every other line must print nothing. The `--- ` line catches a file that would break the share format, the two `find` lines catch hidden and secret files, and the last catches a skill over 500 lines.

### 8. The card

Write `3-work/now/share-$ID/card.txt`, one field per line, no line breaks inside a value, Hebrew except `id`, `kind`, `topic` and `checked`:

```
id: <id>
title: <up to 60 characters, what it is in plain words>
author: <the name the owner chose>
kind: <skill | agent | system | template | guide>
topic: <start | marketing | design | infra | other>
problem: <one sentence, the pain, the way the owner said it, up to 220>
result: <one sentence, what changes after it is installed, up to 220>
use: <the exact sentence to say to Morty, one of the triggers>
time: <how long the install takes, e.g. 10 דקות>
needs: <accounts or tools needed, or "רק מערכת MAKERS">
example: <what the owner gets, as a short real looking sample of the output, cleaned like everything else, one line, 20 to 400 characters>
walked: <from step 6, e.g. "הותקן במערכת ריקה בסבב השני, המשפט הפעיל את הסקיל">
checked: share-with-makers v2
```

`topic`: `start` the system itself, `marketing` content, leads, sales, `design` pages and visuals, `infra` connections, data, automation, `other` anything else.

Show the owner the card as it will appear, and wait:

```
ככה זה ייראה על הקיר:
<title>
מאת <author>
<problem>
<result>
ככה זה נראה: <example>
אומרים למורטי: "<use>" · הקמה: <time> · צריך: <needs>

לשנות משהו, או שאני סוגר?
```

### 9. Build the file

Build it with this command, never by retyping the files: a copy made by hand drifts from what you cleaned.

```bash
ID=<id>; S="3-work/now/share-$ID"; OUT="3-work/done/$(date +%Y-%m-%d)-$ID.makers-share.md"; mkdir -p 3-work/done
{ printf '<!-- makers-share v1 -->\n'; cat "$S/card.txt"
  (cd "$S/files" && find . -type f | sed 's|^\./||' | LC_ALL=C sort | while IFS= read -r f; do
     printf -- '--- file: %s\n' "$f"; cat "$f"; printf '\n\n'; done)
  printf -- '--- end\n'; } > "$OUT"
wc -c "$OUT"
```

Over 400000 bytes: the wall refuses it. Leave out data files and long examples, and build again.

### 10. Final pass

Run `/final-pass` on the file. Question 3 here means: would the owner be glad to see this with their name on it, in front of everyone from the workshop?

### 11. Hand it over

Open the folder with the file selected:

```bash
ID=<id>; OUT="$(ls -t 3-work/done/*-$ID.makers-share.md | head -1)"
case "$(uname -s)" in Darwin) open -R "$OUT" ;; *) explorer.exe "/select,$(cygpath -w "$OUT")" ;; esac
```

Then:

```
הקובץ מוכן ומסומן בתיקייה שנפתחה. נכנסים ל-themakers.co.il/bonus/share, גוללים לצעד 3 וגוררים אותו לשם.
אם הקיר מחזיר הערות, מדביקים לי אותן ואני מתקן.
```

## When the wall sends notes back

The owner pastes them. Fix each one **in `3-work/now/share-<id>/`**, never in the original, run the scan of step 7 again, rebuild with step 9 **with the same `id`**, and open the folder again. The same id updates the card in place; a new id would put a second card on the wall.

## When people get stuck on it

Participants who installed the share mark it "עבד לי" or "נתקעתי" on the wall, and the owner sees the notes of whoever got stuck on their own card, with a button that copies them to you. Treat them exactly like notes from the wall: fix in `3-work/now/share-<id>/`, walk it again (step 6), rebuild with the same id.

## When the owner wants to update or remove a share

To update: change the copy in `3-work/now/share-<id>/`, or start again from the original if it changed, and rebuild with the same id. To remove: the owner presses "להוריד מהקיר" on their own card. You cannot do it from here.

## The signal you see

The move line in step 1, the stranger's report from step 6 with nothing left in it, the card shown in step 8 before anything is built, and a folder opened with one `.makers-share.md` file selected. No walk, no card, no share.
