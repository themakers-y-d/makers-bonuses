# MAKERS layer for style-maker

This file is read only when style-maker runs inside a MAKERS system. It does not replace SKILL.md. It says two things: how to use what the system already knows about the owner and their design brief so that fewer questions are asked, and where to record the result so the rest of the team can find it.

Every path here is relative to the system folder, the folder you are working in. The skill itself and the personal style stay in `~/.claude/skills`, because that is where SKILL.md looks for them. "SKILL.md" means `~/.claude/skills/style-maker/SKILL.md`.

**Who runs this: the Designer, in the main conversation.** Open `2-makers/designer/designer.md` and work as that agent, with its hard rule and its `/final-pass`. The job is how a video looks, and the skill is a conversation that stops for the owner several times. The Vibecoder works in its own window and cannot hold that conversation, and nothing here touches a live system or money, which is the only reason that agent is isolated.

Two things the Designer's own file would otherwise stop on. **The message exists:** it is what the owner says in the video, and step 10 of SKILL.md states it in words, scene by scene, before anything is drawn. **No copy is written here:** every word on screen is either the owner's own spoken words from the transcript or a line the owner saw and approved in this conversation (the ending in step 5, the closing in the twelve lines). Nothing on screen is new copy, so it does not belong to the Writer. If the owner asks for new wording, that is the Writer's, and you say so.

Messages to the owner below are in Hebrew, word for word. Everything else is instruction. Work through the numbered steps in order.

## שלב 1. Confirm this is a MAKERS system

Check that `1-me/summary.md` exists in the folder you are working in. If it does not, this is not a MAKERS system: stop reading this file and follow SKILL.md as it is.

If it does, first run the search of step 2 and the reading of step 3 silently, without sending anything, so you know whether a brief exists and whether `1-me/` answers anything. Then run step 1 of SKILL.md (the check, asking for the video, and the "ככה זה ילך" message), with one change to item 1 of that message's numbered list. Replace it with:
• When a brief was found or `1-me/` answers at least one question: "1) עד שלוש שאלות קצרות על הסגנון. חלק מהתשובות כבר אצלי, מהמערכת שלך."
• Otherwise: "1) עד שלוש שאלות קצרות על הסגנון."

Then continue with step 2, sending its message if it has one.

If a style already exists and the owner asked to apply it to a video, go straight to step 7 here.

## שלב 2. The design brief

Run:

```bash
find . -maxdepth 6 -name '*.css' -not -path './.claude/*' -not -path './3-work/done/*' -not -path '*/node_modules/*' -exec grep -l ':root' {} + 2>/dev/null; ls 5-library/design-brief 2>/dev/null
```

A CSS file with `:root` and `--` variables is a design brief's colour file. The brief itself is the `.md` file in the same folder whose name contains `brief` and that holds at least one hex colour (`#` and six characters), if there is one. A `5-library/design-brief/` folder holding only such a `.md`, with no CSS, is also a brief. When the same brief shows up in `5-library/design-brief/` and somewhere else, use the one in `5-library/design-brief/` and do not ask.

• One found: read it and the brief beside it. Say in one line: "מצאתי את בריף העיצוב שלך, ב-<התיקייה>. הצבעים והצורות של האנימציה ייבנו ממנו."
• More than one: ask in one line which to use, with the paths, and wait.
• None: send this message exactly, and wait:

```
לפני שמתחילים: יצרת כבר בריף עיצוב, במדריך של הסדנה? אלה שני קבצים קצרים, בריף וקובץ צבעים.

אם כן, גרור אותם לכאן, והאנימציה תיבנה מהצבעים ומהצורות שלך.

אם לא, זה לא חובה, ואפשר להמשיך עכשיו. אבל אם יש לך שעה וחצי, כדאי למלא אותו קודם. הוא נותן לכל הצוות שלך צבעים וצורות קבועים במקום ניחוש, לא רק לאנימציה. המדריך כאן: https://themakers.co.il/bonus/design-brief-guide

מה עדיף, להמשיך בלי או לעצור ולמלא קודם?
```

Then, by the answer:
• Gave files (dragged, or a path): read them. A brief with only the `.md` and no CSS file is still a brief; take the hex values written in it.
• Continue without: go to step 3 with no brief.
• Stop and fill it first: send "מעולה. כשתסיים, שמור את הבריף ואת קובץ הצבעים במערכת, בתיקייה 5-library/design-brief (אם יש לך רק אחד מהם, גם זה מספיק), ולחץ שוב /reel-style. שם אמצא אותם לבד." and stop.

Whenever the brief in use sits anywhere other than `5-library/design-brief/` (outside the system, or inside a project folder that will later move to `done/`), the wave in step 5 ends with one extra line: "ואגב: להעתיק את הבריף ל-5-library/design-brief, כדי שכל הצוות ימצא אותו גם בפעם הבאה? (כן / לא)". On yes, `mkdir -p` and `cp -n`, never overwriting, and add the Designer line to the Archivist proposals in step 10. On no, use it where it is.

## שלב 3. What the system already knows

Read `1-me/summary.md`, `1-me/me.md`, `1-me/audience.md`, `1-me/offers.md` and `1-me/voice.md`. A section that still holds only the template's bracketed prompt (for example "[Describe it...]") is unfilled. A section with real content and leftover bracket text is filled: use the owner's own sentences and ignore the bracket text. A fresh system looks unfilled everywhere, and that is normal.

What is filled becomes a proposal, not a decision:
• Field and topic area, from whichever of these files states it. This decides axis 9 by the derivation rules in axes.md.
• Who the videos speak to: one short line from `audience.md`.
• What the viewer does at the end: the natural next step from `offers.md` (send a message, comment a word, open a link), written as the words the viewer would read. Never a price.
• How they speak on camera: one of the four options of question 2 in SKILL.md, from the rhythm and sentences in `voice.md`.

## שלב 4. From the brief to colours and shapes

Only when there is a brief. From its colour file and the brief:

• Background: the brief's background colour.
• Ink: the colour the brief says all text is written in. If it does not say, the darkest colour at 4.5:1 or more against the background.
• Primary: the colour the brief gives to surfaces and large areas. Accent: the colour it gives to dots and small details. Warm: by "ברירות מחדל לטוקנים" in axes.md, and when the brief's only warm colour is already the accent, the warm token is that same colour. Never add a colour the brief does not hold.
• A contrast rule in the brief ("this colour is never text", "never a word") carries over as it is.
• Radius: the brief's radius replaces the radius token, which governs corners of cards, tags, fields and windows. It never touches circles: the iris, dots and diagram nodes keep their sizes from axes.md.
• Logo: a logo or mark file the brief names is the logo token only after you open it with your image-reading tool and see an actual image. A missing, empty or unreadable file means no logo, and step 6's brief line says so. A mark the brief defines as small keeps the brief's size and appears once, never scaled up to fill the closing.
• Fonts: the animation writes Hebrew only in Assistant (and Playpen Sans Hebrew for handwriting), because those were checked to render Hebrew correctly. The brief's fonts do not enter the video.

**The brief outranks a derived choice.** When a brief rule rules out the option a default or a derivation would pick (a ban on bouncing motion against 5ב, a "never a word" colour against the coloured caption word of 8ב, radius 0 against round shapes of 2א), take the nearest option that respects the brief, and name it in step 6's brief line. A ban on bouncing or oscillating motion also sets the gentle breathing of 5א to zero. When a brief rule rules out an option the owner chose explicitly, do not override them: name the clash in that line and offer the nearest option. When no option keeps the defining feature of what they chose (for example no colour in the brief may carry the coloured caption word), say so plainly and offer the closest option without that feature.

**A fixed rule outranks the brief.** A brief line that contradicts the 14 grammar rules in axes.md (for example "no text over an image", when captions sit on the video) does not enter the style. Caption legibility over video (white fill, dark outline) is one of those fixed rules, not a colour choice. Name what did not enter in the same line.

**The brief's "stop and ask me" line is honoured by step 6's brief line.** Everything you chose because the brief did not define it (for example which colour the closing card sits on) is listed there, where the owner can change it.

Question 3 is answered: colour codes, axis 4 option ג, with these colours.

## שלב 5. One wave, at most three questions

The system allows at most three questions per request, in one wave. Build the wave:

1) Drop every question that steps 3 and 4 answered.
2) From the rest, in this order, keep the first three: 1, 4, 5, 3, 6, 7, 2. Copy each one word for word from step 2 of SKILL.md, keeping its original number, so the derivation rules in axes.md still apply. When step 3 found the field, the audience and the ending, question 1 shrinks to "1) על מה הסרטון הזה, במשפט?" and moves to the end of the order.
3) Every question left out takes the safe option from "לא יודע" in axes.md.

The top block holds one line for every question that is not in the wave, and only those. A line answered from the system reads as below. A line left out by the cap reads "<הנושא>: בחרתי <האפשרות, במילים> כברירת מחדל. אפשר לשנות בהמשך." For colours without a brief: "צבעים: אין לי בריף שלך, אז בחרתי פלטה בהירה ונקייה. אפשר לשנות, או לכתוב לי קודי צבע." Nothing is chosen for the owner without a line.

When no line came from the system, the block opens with: "המערכת שלך עוד לא מכירה אותך מספיק כדי לענות במקומך. כשתמלא את הפרופיל שלך, בפעם הבאה אשאל פחות." That line is what tells the owner that filling `1-me/` saves them questions, so it is never dropped.

Send:

```
מה כבר ידוע לי, ומה בחרתי. אם משהו לא נכון, תקן:
• התחום: <מ-1-me>
• הסרטונים מדברים אל: <מ-audience.md>
• בסוף הצופה: <המילים שהצופה יקרא, מ-offers.md>
• הטון בסרטונים: <האפשרות, מ-voice.md>
• צבעים: מהבריף שלך. רקע <hex>, טקסט <hex>, ראשי <hex>, מבטא <hex>
<a line for each question left out by the cap>

ועכשיו רק מה שחסר לי:

<the questions kept, word for word>

אפשר לענות בקיצור, למשל: <an example built only from the questions kept: a letter for each multiple-choice one, a few words for question 1 if it was kept, never an answer the top block already gave>
על כל שאלה אפשר לכתוב "לא יודע", ואבחר את האפשרות הבטוחה.
```

Do not send the extra-tuning line from SKILL.md step 2 in a MAKERS system. Tuning happens through notes after the first video. If the owner answers tuning questions anyway, or changes a line that was not asked, take it: an explicit answer always wins over a default.

## שלב 6. Derive, confirm, write the style

Run steps 3, 4 and 5 of SKILL.md, with these changes, the ones marked "with a brief" only when there is one:

1) Step 3 there, with a brief: question 3 is answered. Do not run `palette` and do not offer palettes, not in step 3 and not in item 6 of step 6 there.
2) Step 4 there: write each of the twelve lines in plain words the owner uses ("איך אתה מופיע", "איך הדברים זזים"), not the axis names. After them and before the question about changes, one short paragraph. With a brief: "מהבריף שלך: <הצבעים, הרדיוס, ומה מהכללים נכנס>. לא נכנס: הגופן, כי האנימציה כותבת ב-Assistant שנבדק לעברית<, ועוד מה שלא נכנס ולמה>. בחרתי לבד, כי הבריף לא הגדיר: <רשימה, או 'כלום'>." Without a brief: "את הצבעים בחרתי בלי בריף. כשיהיה לך, אפשר לבנות את הסגנון מחדש ממנו."
3) Step 5 there, with a brief: in the style's "נבנה ב-" line add "מהבריף שב-<הנתיב>". This replaces SKILL.md's instruction that "הערות שנשמרו" stays empty: after its explanation line, add one line per brief rule that entered the style, both "אסור" lines and "never text / never a word" rules, and only rules about colour, shape, motion or the mark: `• <תאריך> מהבריף: "<הכלל כלשונו>"`. Inside the quoted rule, a long dash becomes a comma, double quotes become single quotes, and `<` or `>` become words, because step 5's check counts all of them.

## שלב 7. From installation to the file

Run steps 6 through 15 of SKILL.md as they are. Installation asks the owner before it downloads anything, and the video is saved beside the original.

## שלב 8. Record it in the project folder

In a MAKERS system finished work is recorded in `3-work/now/<project>/`. The project here is `reels`. Create the folder if it does not exist.

The video itself stays where step 15 put it. A video weighs tens of megabytes, and a system that keeps restore points would copy it into every one of them.

Run `/final-pass` once, on the video and this record together. Then write `3-work/now/reels/<YYYY-MM-DD>-<video name>.md`, plain text with no wrapper of any kind. If the name is taken, add `-2`. An earlier record is never overwritten.

```
סרטון: <שם הסרטון>
הקובץ: <הנתיב של ה-MP4 ליד המקור>
הסגנון: reel-style-<שם>. הוא שמור ב-~/.claude/skills/reel-style-<שם>, מחוץ לתיקיית המערכת, כי שם הכלי מחפש אותו.
מה הוא מספר:
<3 עד 5 שורות, רגע לכל שורה, כמו בדיווח של שלב 16>

<one plain Hebrew sentence naming the Designer, what it produced, and that /final-pass ran>
```

## שלב 9. The report

Run step 16 of SKILL.md. Step 8 above is already done for this run, so skip the line at the top of step 16 that points back to it. After the line "הסרטון מוכן" add: "ורשמתי אותו אצלך בתיקיית הפרויקט, ב-3-work/now/reels."

## שלב 10. Notes, and the next time

Run step 17 of SKILL.md as it is. Every time a note produces a new file with a new path, write a new record beside the old one, as in step 8, with `-2`, `-3` and so on.

At the end, proposals for the Archivist at the session debrief, and do not write them yourself: "אנימציה לסרטון עוברת למעצב, בשיחה הראשית, עם הסגנון reel-style-<שם> והכפתור /reel-style." And when the brief was copied to `5-library/design-brief/` in this run: "craft.md של המעצב: בריף העיצוב של הבעלים ב-5-library/design-brief, לפתוח אותו לכל עבודה ויזואלית."

Next time the owner presses `/reel-style`, or writes "תלביש את הסגנון שלי על" with a video path. The personal style runs steps 6 to 17 of SKILL.md, and step 16 there sends it back to step 8 here, so the next video is recorded in the project too.
