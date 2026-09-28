התקן לי את הסקיל "style-maker" (בונה הסגנון לרילס). אל תפעיל אותו עכשיו, רק התקנה.

1. צור את התיקייה ~/.claude/skills/style-maker (בווינדוס ב-PowerShell: $env:USERPROFILE\.claude\skills\style-maker). לפני שאתה כותב, אמור לי בשורה אחת שייתכן שאתבקש לאשר כתיבה לתיקיית ההגדרות, ושזה רגיל.
2. הורד לתוכה את שלושת הקבצים האלה, בדיוק בשמות האלה:
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/SKILL.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/axes.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/kit.py
   במק: curl -fsSL --create-dirs -o ~/.claude/skills/style-maker/<שם הקובץ> <הכתובת>. בווינדוס ב-PowerShell: curl.exe -fsSL --create-dirs -o "$env:USERPROFILE\.claude\skills\style-maker\<שם הקובץ>" <הכתובת>, וב-Git Bash כמו במק, עם curl.exe.
3. בדוק שההורדה הצליחה: שלושת הקבצים נמצאים בתיקייה מסעיף 1 (הצג את הנתיב המלא של SKILL.md), SKILL.md מתחיל בשורה --- , ואף קובץ לא ריק ולא מכיל "404".
4. אמור לי בעברית, בשלוש שורות: איפה הסקיל נשמר, שצריך לסגור ולפתוח מחדש את Claude Code כדי שייטען, ושאחרי זה אני כותב "תבנה לי סגנון לרילס".
