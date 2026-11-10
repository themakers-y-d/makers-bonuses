---
name: share-with-makers
description: Prepares something the owner built (a skill, a maker, a system, a template, a guide) for the MAKERS participants' wall, cleans every personal and business detail out of a copy, checks it against the standard, and writes the one file the owner drops on themakers.co.il/bonus/share. Use when the owner says "אני רוצה לשתף עם המייקרז", "לשתף את הסקיל", "תכין את זה לקיר", "להעלות לקיר של המייקרז", "share this with the makers", "put it on the wall", or pastes back notes the wall returned about a share file. Always use this instead of zipping or copying files by hand, because the wall rejects any file this skill did not build. Not for backing up the system, and not for sending work to a client.
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

## ההתקנה
<numbered steps you would follow yourself; which maker owns it; which questions to ask the owner, word for word>

## איך יודעים שזה עבד
<one observable thing>

## איך משתמשים
אומרים לך: "<the use sentence>"
```

Every `SKILL.md` in the share keeps the house standard: `name` equal to its folder, a `description` that says what it does, real Hebrew and English phrases, a push ("Always use this instead of…") and a boundary, **and never colon-space inside the description**, which breaks the skill silently. Under 500 lines.

The use sentence on the card must be one of the phrases in that description. A card that promises a sentence the skill does not answer is a broken promise to a stranger.

Anything that needed something only this system has (a row in `tools.md`, a connected account, another maker's file) is either included, or named in the README under "מה צריך".

### 6. The stranger read

If you can start a fresh subagent, give it only the folder `$S/files/` and this brief: "You are Morty in a MAKERS system that has never seen this owner. Read README.md and walk the install in your head. List every word, path, name or assumption you could not resolve, and anything that looks personal or like a real business detail." Fix everything it lists, then run it once more.

If you cannot start one, do it yourself: reread every file as if you had never met this owner. A name you recognise is a leak.

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
checked: share-with-makers v1
```

`topic`: `start` the system itself, `marketing` content, leads, sales, `design` pages and visuals, `infra` connections, data, automation, `other` anything else.

Show the owner the card as it will appear, and wait:

```
ככה זה ייראה על הקיר:
<title>
מאת <author>
<problem>
<result>
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

## When the owner wants to update or remove a share

To update: change the copy in `3-work/now/share-<id>/`, or start again from the original if it changed, and rebuild with the same id. To remove: the owner presses "להוריד מהקיר" on their own card. You cannot do it from here.

## The signal you see

The move line in step 1, the card shown in step 8 before anything is built, and a folder opened with one `.makers-share.md` file selected. No card shown, no share.
