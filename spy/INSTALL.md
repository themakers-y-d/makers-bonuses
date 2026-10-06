התקן לי את הסקיל "spy" (המרגל). אל תפעיל אותו עכשיו, רק התקנה.

1. צור את התיקייה ~/.claude/skills/spy. במק: mkdir -p ~/.claude/skills/spy. בווינדוס ב-PowerShell: New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\spy", וב-Git Bash כמו במק. לפני שאתה כותב, אמור לי בשורה אחת שייתכן שאתבקש לאשר כתיבה לתיקיית ההגדרות, ושזה רגיל.
2. הורד לתוכה את הקובץ הזה, בדיוק בשם SKILL.md:
   https://raw.githubusercontent.com/themakers-y-d/makers-bonuses/main/skills/spy/SKILL.md
   במק: curl -fsSL -o ~/.claude/skills/spy/SKILL.md <הכתובת>. בווינדוס ב-PowerShell: curl.exe -fsSL -o "$env:USERPROFILE\.claude\skills\spy\SKILL.md" <הכתובת>. ב-Git Bash: cd ~/.claude/skills/spy && curl -fsSL -o SKILL.md <הכתובת>.
3. בדוק שההורדה הצליחה: הקובץ נמצא בתיקייה מסעיף 1 (הצג את הנתיב המלא שלו), הוא מתחיל בשורה --- , הוא לא ריק, ולא מכיל "404".
4. אמור לי בעברית, בשלוש שורות: איפה הסקיל נשמר, שצריך לסגור ולפתוח מחדש את Claude Code כדי שייטען (בטרמינל כותבים /exit ואז claude, וב-VS Code סוגרים את החלון ופותחים אותו מחדש), ושאחרי זה אני כותב /spy עם שלוש כתובות של מתחרים.
