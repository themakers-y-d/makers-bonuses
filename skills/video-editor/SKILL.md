---
name: video-editor
description: Edits a video the owner filmed into a finished cut, by message and not by seconds. Reads the Hebrew transcript, proposes which lines to keep and why, cuts dead air and filler sounds, adds Hebrew captions and music under the voice, and saves numbered versions beside the original without ever touching it. Use whenever the owner says things like "תערוך לי את הסרטון", "צילמתי סרטון", "תוריד את השתיקות", "תוריד את האה והאמ", "תקצר את הסרטון", "תשאיר רק את העיקר", "תוסיף כתוביות בעברית", "תוסיף מוזיקה ברקע", "תחתוך מ 1:20 עד 1:35", "תהפוך את ההרצאה לרילים", "edit my video", "cut the silences", "add Hebrew captions", "make this a reel", or drags a video file into the chat. Always use this instead of editing a video freehand or sending the owner to CapCut, because it reads what was said before it cuts, gets one approval on the cut list, checks frames before the full render, and never overwrites the source. The Designer runs it in the main conversation. Not for animation and sound design over a talking head (that is /reel-style from the reel style gift), not for writing a script or new words on screen (the Writer), and not for publishing or ads (the Campaigner).
---

# Video editor

Owner: the Designer, in the main conversation. Never hand it to a worker in its own window: the cut list stops for the owner's approval, and only the main conversation can hold that.

You take a raw video the owner filmed and hand back a finished cut: the message kept, everything around it removed, Hebrew captions that sit on the words, music under the voice if they want it, in the shape of the platform it is going to. The source file is never overwritten. Every render is a new numbered file beside it.

`craft.md` in this folder is the trade: platform sizes, safe zones, loudness, hook and pacing, Hebrew caption rules, when not to cut, and the failure modes. Open it in step 1 and reason from it.

Talk to the owner in Hebrew, about their video and what they said in it, never about the tool. The lines in code blocks marked as messages are theirs word for word, filled where there are angle brackets.

**How every command runs.** Step 1 writes a small launcher, `~/reel-studio/editor`, that runs the studio's own Python on `edit.py` in this folder. Every command below is `bash ~/reel-studio/editor <command>`. Put the video path in double quotes, written in full, never with `~` inside the quotes. On Windows a path like `C:\Users\dana\Videos\reel.mp4` is written `/c/Users/dana/Videos/reel.mp4`.

## Steps

### Step 1. Become the Designer, and check the tools

Open `2-makers/designer/designer.md` and work as that agent, with its hard rule and its `/final-pass`. Its hard rule is satisfied here in step 5: the message exists, it is what the owner says in the video, and you state it in one line before any cut. Then open `craft.md` in this folder.

On Windows, first check that your command tool is bash: `echo $BASH_VERSION` prints a version number in bash and an empty line in PowerShell. In PowerShell, stop and say: "כדי לערוך אני צריך את Git for Windows, כלי חינמי שדרכו Claude Code מריץ פקודות. הוא מותקן כחלק מההתקנה של העורך: הדבק למורטי שוב את הודעת ההתקנה מדף המתנה, והוא ישלים אותו."

Then, from the system folder (the one holding `1-me/` and `2-makers/`), write the launcher and run the check. This is safe to run every time and keeps the launcher pointing at this folder even if the system moved:

```bash
SK="$(pwd)/.claude/skills/video-editor"; [ -f "$SK/edit.py" ] || { echo "NOT IN THE SYSTEM FOLDER"; exit 1; }; mkdir -p ~/reel-studio && printf '#!/bin/bash\nPY="$HOME/reel-studio/.venv/bin/python"; [ -x "$PY" ] || PY="$HOME/reel-studio/.venv/Scripts/python.exe"\nexport PYTHONIOENCODING=utf-8 PYTHONUTF8=1\nexec "$PY" %q "$@"\n' "$SK/edit.py" > ~/reel-studio/editor && bash ~/reel-studio/editor doctor
```

• `NOT IN THE SYSTEM FOLDER`: you are working in another folder. Ask the owner in one line to open Claude Code in the folder of their system, the one they open every day, and stop.
• The last line is `ALL GOOD`: continue.
• Anything else (the Python is missing, a `MISSING` line, `NOT READY`): say "הכלים של העורך לא שלמים במחשב הזה. הדבק למורטי שוב את הודעת ההתקנה מדף המתנה, והוא ישלים רק את מה שחסר, בלי למחוק כלום." and stop. Do not install anything from inside this skill.

Then look, without opening anything else yet, at `3-work/now/video/`: does `caption-style.json` exist there, and what is the newest record. Both are used later. On the first video ever neither exists, and that is the normal state.

### Step 2. The video

If the owner did not give a video, ask: "גרור לכאן את קובץ הסרטון (בתוך VS Code מחזיקים Shift בזמן הגרירה), או הדבק את הנתיב שלו. להעתיק נתיב: במק לחיצה ימנית על הקובץ, מחזיקים Option ובוחרים Copy as Pathname. בווינדוס לחיצה ימנית על הקובץ ו'העתק כנתיב'." and wait.

Before you touch the file, on Mac say: "אם יופיע חלון שמבקש גישה לתיקייה של הסרטון, לחץ Allow." On Windows, a video in a OneDrive folder that shows a cloud icon is not on the computer yet: tell the owner to right-click it, choose Always keep on this device, and wait for the green mark. On Mac the same goes for iCloud Drive: they open the file once in Finder so it downloads.

Run:

```bash
bash ~/reel-studio/editor info "<video>"
```

It prints the length, the size, the frame rate, whether it is vertical, and the `JOB FOLDER` where this video's working files live. Remember that folder; below it is `<job>`. On Windows it prints as `C:\Users\...`: write it with forward slashes, `C:/Users/...`, in every command below. If `info` fails on a path with Hebrew letters, spaces or symbols, copy the file to a plain English name and use the copy, remembering the original path. The new versions are then made beside the copy, in `~/reel-studio/in`; in step 10, after `FILE OK`, copy each one beside the original with `cp -n` and report that path:

```bash
N="video-$(date +%Y%m%d-%H%M)"; mkdir -p ~/reel-studio/in && cp "<video>" ~/reel-studio/in/$N.mp4 && echo ~/reel-studio/in/$N.mp4
```

Two things from `info` go into the first message of step 3 when they apply: a landscape video going to a vertical platform (craft.md, "Landscape into vertical"), and a video longer than about five minutes (the long-form mode in step 5).

### Step 3. One wave, at most three questions

**When the request is mechanical and complete, ask nothing.** "תוריד את השתיקות", "תוריד את האה והאמ", "תחתוך מ 1:20 עד 1:35", "תשאיר שורות 3 עד 7" say exactly what to do: skip to step 4 (the transcript is still needed for captions and to check nothing whole was lost), then step 6. "רק תוסיף כתוביות" is mechanical too: no `edl` at all, and `--no-edl` on the sheet and the render, so an edit list left from an earlier session on the same video is not applied.

Otherwise, read what you already know before asking anything: what the owner wrote in their request, what `info` showed, `caption-style.json` from step 1, and in `1-me/` where they publish and how they speak (`summary.md` is already loaded, open `voice.md` and `audience.md`). Every question that is already answered is dropped. Send one message:

```
מה כבר ידוע לי. אם משהו לא נכון, תקן:
• הסרטון: <אורך>, <אנכי / רחב / מרובע>
• <one line for every other thing already known, for example: הכתוביות: בסגנון ששמרנו בפעם הקודמת>

ועכשיו רק מה שחסר:
1) לאן זה הולך, ובאיזה אורך בערך? למשל ריל של עד דקה, יוטיוב רחב, פוסט מרובע, או כמו שצולם.
2) כתוביות ומוזיקה? כתוביות בעברית צרובות בתוך הסרטון (מתאים לרילס), כתוביות שאפשר לכבות (מתאים ליוטיוב), או בלי. ומוזיקה: גרור קובץ שהוא שלך או ברישיון לפלטפורמה הזו, או כתוב "בלי".
3) יש משהו שחייב להישאר, או משהו שבטוח יורד?

אפשר לענות בקיצור, למשל: 1 ריל עד דקה / 2 צרובות, בלי מוזיקה / 3 הסיפור על הלקוחה נשאר
```

Keep the original numbers of the questions you do ask, and build the short example only from them. Never more than these three, and never a question about who the owner is: that is in `1-me/`.

When the owner says "לא יודע": a vertical video goes to a reel of up to about a minute, burned captions, no music. Say which you chose in one line and continue.

### Step 4. The transcript

Say before: "מתמלל עכשיו. זה לוקח בערך חצי מאורך הסרטון במחשב חדש, ועד פי שלושה במחשב ישן. בדקה הראשונה יש שקט בזמן שהמודל נטען, וזה תקין."

A video of up to half a minute, run directly. Anything longer, in the background (your tool's background option, or `nohup ... &` as here), and wait:

```bash
nohup bash ~/reel-studio/editor transcribe "<video>" --model ivrit > "<job>/transcribe.log" 2>&1 &
bash ~/reel-studio/editor wait "<job>/transcribe.log" TRANSCRIBED
```

`--model` is whichever `doctor` listed: `ivrit` if present, otherwise `medium` or `small`. `wait` returns within about a minute and a half with the latest line: `STILL RUNNING`, tell the owner in one line how far it got and run it again. `READY`, done. A line `still working` is a heartbeat, printed every minute while the model works in silence; it is normal. `STUCK` (five minutes without any line) or `FAILED`, show the owner the last lines in one sentence and run `transcribe` once more; if it fails again, stop and say so.

The result is `transcript.txt` in `<job>`, one numbered line per sentence with its start and end time, and `words.json` with every word's time. **Read `transcript.txt` in full before you decide anything.** Fix words the model misheard, usually English names written in Hebrew letters ("וורד פרס" is WordPress), in `words.json` and `transcript.txt`, without touching any time. Captions are built from these words, so a misheard brand name ends up burned into the video.

### Step 5. The cut list, by line numbers, with a reason for every cut

This is the job. A cut by seconds removes noise; a cut by message removes everything that is not the point. Work from craft.md, "Message-level editing", and from `voice.md`: a phrase the owner always says is their voice, not filler, and stays.

First run the two mechanical reports, each under a minute:

```bash
bash ~/reel-studio/editor silences "<video>"
bash ~/reel-studio/editor fillers "<video>"
```

`silences` lists the dead-air cuts. `fillers` lists numbered items, each marked `cut` or `ask`. `cut` are the safe ones: hesitation sounds (אה, אמ), a stuttered short word, a phrase said twice in a row. `ask` are words that are sometimes filler and sometimes part of the sentence (כאילו, יעני, רגע, בעצם), a doubled word that may be on purpose (לאט לאט, מאוד מאוד), and a word that may have been started twice. An `ask` item is never cut without the owner: read each one inside its line, and put in the message below only the ones you would cut, with their numbers. The rest stay.

Then, from the whole transcript:

1) Say the message in one sentence. If you cannot, there is no message yet: tell the owner so in one line and ask what the one point of this video is, before cutting anything.
2) Choose the opening line: the first line that stops a scroll on its own, within the first one to three seconds of the cut. It is usually not line 1.
3) Mark every cut and give it a reason: warm-up before the message, a repeated take (keep the cleaner one, usually the last), a tangent, a false start, a tail that fades out, a line that repeats the hook. A cut that removes a whole idea is always listed on its own line, never folded into "and some small cuts".
4) Keep the order unless moving one line to the front makes the hook. A move is listed as a move.
5) Respect what the owner said must stay in step 3, even when you would cut it.

Send:

```
המסר של הסרטון, במשפט: <משפט>
פותחים ב: שורה <מספר>, "<תחילת השורה>". <למה, בחצי משפט>

מה יורד:
• <שורות 1 עד 3>: <סיבה>
• <שורה 9>: <סיבה>
וגם <מספר> שתיקות ארוכות ו<מספר> "אה" ו"אמ", בלי לגעת בהפסקות שמדגישות משהו.
מילים שאני לא מוריד בלי אישור שלך, כי לפעמים הן חלק מהמשפט:
• <מספר מהדוח>) "<המילה>" בשורה <מספר>: <למה להוריד, בחצי משפט>

יוצא בערך <שניות> שניות מתוך <שניות>.
יאללה, או שתשנה? אפשר לכתוב למשל "תחזיר את 9" או "תוריד גם את 12".
```

Drop the two lines of words to approve when you propose none. Wait. Each change: update the list, send it again, wait. **Nothing is cut before this list is approved.** An approval of the list ("יאללה", "מאשר") approves the words in it too.

**Long-form mode.** A lecture, a live or a recorded call longer than about five minutes, when the owner wants reels out of it: do not trim the whole thing. Propose three to six reels instead, each 30 to 90 seconds, each a set of line ranges that may come from different places. Every candidate must pass three tests, judged as a stranger who sees only that reel: complete (no "as I said before", nothing pointing at something missing), hook (the first one or two sentences stop a scroll on their own), close (the last sentence lands on an insight, a punch or an invitation, never mid-breath). Send them as a numbered list, one line each: the opening words, the line ranges, the length, and why it works. Each approved reel then goes through steps 6 to 12 as its own version. For a full long-form edit (a lecture for YouTube), follow craft.md, "Long-form is not a long reel".

### Step 6. Build the edit

```bash
bash ~/reel-studio/editor edl "<video>" --keep "<approved line numbers, in play order>" --use silence,fillers
```

When the owner approved `ask` words, add `--fillers "<numbers>"`. That list replaces the default choice, so it holds every number the report marked `cut` plus the approved `ask` numbers. `--fillers none` keeps every word, `--fillers all` cuts every item.

**Lines and times are written differently, and a mistake here cuts the wrong thing.** In `--keep` and `--remove` a bare number or range ("5", "3-7", "7,1-6,8-12") is a line number from `transcript.txt`. A time has a colon, a decimal point or an `s`: "1:20-1:35", "40.5-42", "40s-42s". So "תחתוך מ 40 עד 42 שניות" is `--remove "40s-42s"`, never `"40-42"`, which would remove lines 40 to 42.

A mechanical request uses only what was asked: `--use silence`, `--use fillers`, `--remove "1:20-1:35"`, or `--keep "3-7"`. Every `edl` run builds the whole edit from the source again, so a later change repeats everything already approved (`--keep`, `--use`, `--fillers`) and adds the new part. The command prints the length the edit will have. If it differs from what you promised the owner by more than about ten percent, find out why before going on.

If `silences` cut into the start of words or left long gaps, follow craft.md, "Silence thresholds": run the report again with the adjusted values before building the edit, for example `silences "<video>" --db -35 --pad 0.25` (the defaults are `--db -30 --min 0.6 --pad 0.15`). Note any value that differed from the default: it goes into the record in step 11.

### Step 7. The look

**The format first,** from step 3: `reel` (1080x1920), `wide` (1920x1080), `square`, or `source` (the shape it was filmed in). From here every `style`, `sheet`, `frames` and `render` gets the same `--format`. A landscape video going to `reel` also gets `--fit` (craft.md, "Landscape into vertical"): `auto`, the default, crops around one steady face and otherwise keeps the whole picture on a dark band; `band` keeps the whole picture on a dark band; `blur` keeps it whole over a blurred copy of itself; `crop` always crops. A vertical video into `reel` needs no `--fit`.

Captions and music, from the step 3 answers. The caption style comes from the first that exists:

1) `3-work/now/video/caption-style.json`, the style saved from an earlier video: `bash ~/reel-studio/editor style "<video>" --format <format> --style "3-work/now/video/caption-style.json"`, which takes it as it is.
2) The owner's design brief. Look for it:

```bash
grep -rl ':root' --include='*.css' --exclude-dir=.claude --exclude-dir=done --exclude-dir=node_modules . 2>/dev/null; ls 5-library/design-brief 2>/dev/null
```

A CSS file with `:root` and `--` colour variables is the brief's colour file. One found: `bash ~/reel-studio/editor style "<video>" --format <format> --from-css "<that file>"`, and say in one line: "מצאתי את בריף העיצוב שלך. הכתוביות ייקחו ממנו את הצבעים." More than one: ask in one line which, with the paths.
3) Nothing: `bash ~/reel-studio/editor style "<video>" --format <format>`, the safe default, white letters with a dark outline. Say in one line: "אין לך עדיין בריף עיצוב, אז הכתוביות בסגנון הבטוח, לבן עם קו כהה. כשיהיה בריף, אבנה את הסגנון ממנו."

`style` prints `STYLE <job>/style.json`, the style file from now on, and `PREVIEW`, an image with a frame and five test lines; open it and check every test line reads right to left. Pass that `STYLE` path as `--style` to every `sheet`, `frames` and `render` below, always together with the same `--format`. Copy it to `3-work/now/video/caption-style.json` only when that file does not exist yet (`mkdir -p` the folder, then `cp -n`), so the next video starts from the same look without asking. A brief's fonts are not taken for burned captions unless they have Hebrew letters; the engine's Hebrew font is the safe one.

Music: only a file the owner gave. Before using it, say once which platform it is licensed for if they did not say (craft.md, "Music under speech"), and never download music yourself.

### Step 8. Frames before the full render

```bash
bash ~/reel-studio/editor sheet "<video>" --format <format> --style "<job>/style.json"
```

Give it exactly the `--format`, `--fit` and `--style` that the render in step 9 will get (and `--no-edl` when there is no cut); a sheet drawn with other values previews a different video. Its first line says the format, the fit and the style it used: check them. It draws one frame from every kept part of the edit, with the captions in place, on one image, and prints its path. Open it with your image tool and go through craft.md, "Check before the full render". In short: the opening frame is the hook line; captions sit inside the safe area and never on the face; at most two lines; Hebrew reads right to left with punctuation, English words and numbers in the right place; the crop keeps the face; the contrast holds. For a closer look at a moment, `bash ~/reel-studio/editor frames "<video>" <t1> <t2> ... --format <format> --style "<job>/style.json"` gives full-size stills at those seconds of the edit; add `--safe` to shade what the app covers.

A problem: fix the style or the edit and draw the sheet again, up to three rounds. Still wrong after three: tell the owner in one sentence and continue.

Show it: `bash ~/reel-studio/editor open "<the sheet>"`, and write: "זו תצוגה מקדימה, פריים מכל קטע שנשאר, עם הכתוביות במקום. ממשיך לרינדור המלא, והערות אפשר לתת בסוף." Do not wait for an answer.

### Step 9. The full render

Say before: "מרנדר עכשיו את הסרטון המלא. זה לוקח בין דקה לעשר דקות לפי האורך והמחשב, ובזמן הזה יש שקט. אכתוב לך אחוזים. עדיף לא לסגור את החלון עד שאגיד שהסרטון מוכן."

```bash
nohup bash ~/reel-studio/editor render "<video>" --format <reel|wide|square|source> --captions <burn|soft|none> --style "<job>/style.json" > "<job>/render.log" 2>&1 &
bash ~/reel-studio/editor wait "<job>/render.log" DONE
```

The same `--format`, `--fit` and `--style` as the sheet. With music, add `--music "<file>" --duck`. With no cut at all, add `--no-edl`. Loudness is -14 LUFS for up to five minutes and -16 for longer, by itself; `--lufs` changes it only when the owner asks. Run `wait` again after every `STILL RUNNING`, and tell the owner the percent each time. `STUCK` or `FAILED`: show the last lines in one sentence, fix, render again. The `DONE` line prints the path of the new numbered version beside the source; that path is the one used from here on. Never pass `--out` over an existing file.

### Step 10. Check the delivered file

Do not trust the render. Check the file itself:

```bash
bash ~/reel-studio/editor verify "<the new mp4>"
```

It checks that the file opens, its length against the edit, the video and audio streams, the loudness and the peak, and pulls frames from the delivered file. Open them. Then look at three moments right after a cut: add up the lengths of the pieces `edl` printed to get the second of each cut, and run `bash ~/reel-studio/editor frames "<the new mp4>" <t1> <t2> <t3> --safe` on the delivered file. The caption on screen must be the word being said. A caption that leads or lags after each cut is drift (craft.md, "Failure modes"), and the version is not delivered.

`FILE HAS PROBLEMS`, a length that does not match, or frames that do not match step 8: go back to the step that made it. Only after `FILE OK`: `bash ~/reel-studio/editor open "<the new mp4>"`.

### Step 11. Record it, and the final pass

In a MAKERS system finished work is recorded in the project folder, and the project here is `3-work/now/video/`. Create it if it does not exist. The video itself stays where the render put it, beside the source: a video weighs tens of megabytes and does not belong inside the system.

Copy the working material, the corrected `transcript.txt` and the approved cut list, into `3-work/now/video/_process/<YYYY-MM-DD>-<video name>/`. Then write the record, `3-work/now/video/<YYYY-MM-DD>-<video name>.md`, plain text with no markup around it. If the name is taken, add `-2`. A record is never overwritten.

```
סרטון: <שם הסרטון>
המקור: <הנתיב>. לא נגעתי בו.
הגרסה: <הנתיב של הקובץ החדש>, גרסה <מספר>
המסר: <המשפט מהשלב של רשימת החיתוכים>
פותח ב: <תחילת שורת הפתיחה>
מה ירד ולמה: <שתיים עד חמש שורות>
לאן: <פלטפורמה>. <אורך המקור> שניות, אחרי העריכה <אורך> שניות
כתוביות: <צרובות / לכיבוי / בלי>, סגנון מ<הפרויקט / הבריף / ברירת המחדל>
מוזיקה: <הקובץ ולאיזו פלטפורמה הוא ברישיון, או בלי>
ספים: <רק ערכים ששונו מברירת המחדל ומה עבד, או "ברירת מחדל">

<one plain Hebrew sentence: the Designer edited it, what came out, and that the final check ran>
```

Run `/final-pass` on the video and the record together. Question 2 there, "does this sound like the owner", is answered by the cut: does the edit keep how they actually talk, or did it sand them into someone tidier.

### Step 12. The report

```
הסרטון מוכן: <הנתיב>

עכשיו הוא <אורך> שניות, במקום <אורך המקור>. הוא נפתח ב"<תחילת שורת הפתיחה>".
מה ירד: <משפט אחד>.
מה בדקתי: הכתוביות יושבות על המילים גם אחרי החיתוכים, שום דבר לא נמצא בשוליים שהאפליקציה מכסה, והקול ברור ובעוצמה של רשתות. המקור נשאר כמו שהיה.
רשמתי את זה אצלך בתיקיית הפרויקט, `3-work/now/video`.

מה היית משנה?
```

Then the one closing line of `/final-pass`, and one short line naming the files you opened (for example "פתחתי את הקול שלך, את מלאכת המעצב ואת בריף העיצוב").

### Step 13. Notes, versions, and the next time

Every note makes a new version from the source, never from the previous cut, so nothing degrades and nothing is lost:

• Content ("תחזיר את 9", "תוריד את ההתחלה"): update the line list, `edl` again, steps 8 to 11.
• A time window ("תחתוך 1:20 עד 1:35"): `edl ... --remove "1:20-1:35"` on top of the approved list, steps 8 to 11.
• The look ("הכתוביות קטנות מדי", "תזיז אותן למעלה"): `bash ~/reel-studio/editor style "<video>" --format <format> --style "<job>/style.json"` with the change, for example `--size 90` (78 is the default), `--position 62` (the bottom edge of the captions in percent of the height, smaller is higher; 75 is the default on a reel), `--color`, `--outline`, `--box` or `--font`. Then copy `<job>/style.json` over `3-work/now/video/caption-style.json` (now the owner asked for it, so overwrite is right) and say "נשמר בסגנון שלך, גם לסרטונים הבאים." Steps 8 to 11.
• Music level, format, captions on or off: the render flags, steps 9 to 11.

Every new version gets its own record, with `-2`, `-3`. The earlier version stays on disk; say its path if the owner wants to compare.

When a threshold that differed from the default worked (a quiet speaker, a noisy room), propose it to the Archivist in one line at the end, and do not write it yourself: "craft.md של המעצב: לסרטונים של <הבעלים> <הערך> עבד בחיתוך השתיקות, כי <הסיבה>." Same for a correction the owner gave twice.

When the owner is happy, finish with: "בפעם הבאה פשוט כתוב 'תערוך לי את הסרטון' וגרור אותו לכאן. הסגנון שלך שמור, ואני מגיע ישר לרשימת החיתוכים."

## Handoffs

**New words are the Writer's.** A script before filming, a title on screen, the caption text of the post, a hook line the owner did not say. Every caption you burn is the owner's own spoken words from the transcript; anything else is copy, and you say so and hand it over.

**Animation and sound design over a talking head is `/reel-style`**, from the reel style gift. If `.claude/commands/reel-style.md` or `~/.claude/skills/style-maker` exists, offer it once after a finished vertical cut: "רוצה להלביש על הגרסה הזו את סגנון האנימציה שלך? זה /reel-style." If neither exists, mention it once, ever, after the first finished reel: "אם תרצה גם אנימציה וסאונד על הסרטונים, יש מתנה נוספת, בונה הסגנון לרילס: https://themakers.co.il/bonus/animation" and do not raise it again.

**Publishing, boosting and ads are the Campaigner's.** You hand over the finished file and its path. You never upload anything.

## The one hard rule

Never overwrite or delete the source, and never cut a whole idea the owner did not approve.

Every render is a new numbered file, and every content cut passes through the list in step 5 first. That is what makes it safe to cut hard: whatever went wrong, the source and the record bring it back.

## The signal you see

A cut list by line numbers, with a reason beside every cut, before anything renders. Then a numbered file beside an untouched source, a dated record in `3-work/now/video/`, and the `/final-pass` line.

A finished video that arrives without the list before it means the message-level step was skipped.

## Where it breaks

It breaks when it cuts by seconds instead of by message: every silence gone, and the warm-up and the repeated take still in.

It breaks when it reports success from a command that exited cleanly on a file that did not change: same length, no captions, no music. Step 10 measures the delivered file for exactly this.

It breaks when captions are timed to the original and drift after the cuts, or sit under the platform's buttons.

It breaks when it treats a breath before the important sentence, or the pause after a punchline, as dead air.

And it breaks when it puts music under the voice that the owner has no licence for on that platform. The video gets muted or taken down after it is published, which is the worst moment to find out.
