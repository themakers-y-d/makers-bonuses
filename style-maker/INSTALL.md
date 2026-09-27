התקן לי את הסקיל "style-maker" (בונה הסגנון לרילס). אל תפעיל אותו עכשיו, רק התקנה.

1. צור את התיקייה ~/.claude/skills/style-maker (בווינדוס: %USERPROFILE%\.claude\skills\style-maker). לפני שאתה כותב, אמור לי בשורה אחת שייתכן שאתבקש לאשר כתיבה לתיקיית ההגדרות, ושזה רגיל.
2. הורד לתוכה את שלושת הקבצים האלה, בדיוק בשמות האלה:
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/SKILL.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/axes.md
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/style-maker/kit.py
   במק: curl -fsSL -o <שם הקובץ> <הכתובת>. בווינדוס: Invoke-WebRequest -Uri <הכתובת> -OutFile <שם הקובץ>.
3. בדוק שההורדה הצליחה: SKILL.md מתחיל בשורה --- , ואף קובץ לא ריק ולא מכיל "404".
4. אמור לי בעברית, בשלוש שורות: איפה הסקיל נשמר, שצריך לסגור ולפתוח מחדש את Claude Code כדי שייטען, ושאחרי זה אני כותב "תבנה לי סגנון לרילס".
