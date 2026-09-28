התקן לי את הסקיל "style-maker" (בונה הסגנון לרילס). אל תפעיל אותו עכשיו, רק התקנה.

1. צור את התיקייה ~/.claude/skills/style-maker. במק: mkdir -p ~/.claude/skills/style-maker. בווינדוס ב-PowerShell: New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\style-maker", וב-Git Bash כמו במק. לפני שאתה כותב, אמור לי בשורה אחת שייתכן שאתבקש לאשר כתיבה לתיקיית ההגדרות, ושזה רגיל.
2. הורד לתוכה את שלושת הקבצים האלה, בדיוק בשמות האלה:
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/SKILL.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/axes.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/kit.py
   במק: curl -fsSL -o ~/.claude/skills/style-maker/<שם הקובץ> <הכתובת>. בווינדוס ב-PowerShell: curl.exe -fsSL -o "$env:USERPROFILE\.claude\skills\style-maker\<שם הקובץ>" <הכתובת>. ב-Git Bash: cd ~/.claude/skills/style-maker && curl -fsSL -o <שם הקובץ> <הכתובת>.
3. בדוק שההורדה הצליחה: שלושת הקבצים נמצאים בתיקייה מסעיף 1 (הצג את הנתיב המלא של SKILL.md), SKILL.md מתחיל בשורה --- , ואף קובץ לא ריק ולא מכיל "404".
4. אמור לי בעברית, בשלוש שורות: איפה הסקיל נשמר, שצריך לסגור ולפתוח מחדש את Claude Code כדי שייטען (בטרמינל כותבים /exit ואז claude, וב-VS Code סוגרים את החלון ופותחים אותו מחדש), ושאחרי זה אני כותב "תבנה לי סגנון לרילס".
