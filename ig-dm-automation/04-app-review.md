<div dir="rtl" style="direction:rtl;text-align:right;unicode-bidi:plaintext">

# שדרוג אופציונלי: Advanced Access ותגובה בזמן אמת

זהו שדרוג רשות ולא תנאי להפעלה. מסלול הסורק מספק בדיוק את אותה פונקציונליות, בהשהיה של דקה עד כמה דקות. מי שרוצה תגובה תוך שניות עובר את התהליך הזה, ומי שלא מדלג על הקובץ והמערכת עובדת.

## מה זה קונה

בלי Advanced Access, מטא לא דוחפת אירועי תגובה של גולשים, והמסלול היציב הוא סריקה מחזורית. ההשהיה האופיינית היא בין דקה לחמש דקות, לפי התדירות שהוגדרה.

עם האישור, מטא דוחפת את האירוע ברגע שהתגובה נכתבת. ההשהיה יורדת לשניות, וזה משנה את התחושה: המגיב עדיין נמצא בפוסט כשההודעה נכנסת, ולכן שיעור הפתיחה והמענה גבוה יותר.

יתרון שני, פחות גלוי: פחות קריאות API, פחות עומס, ופחות חשיפה למלכודת תקציב הזמן מקובץ 03.

החיסרון היחיד הוא התהליך: הכנת חומרים, בדיקה אנושית בצד של מטא, ולעיתים גם אימות עסק. הזמן עד תשובה נע בין ימים לשבועות, ויש סיכוי לסבב תיקונים.

## מה מטא דורשת

הרשימה הבאה צריכה להיות מוכנה לפני שלוחצים על בקשת גישה מתקדמת. חוסר באחד מהם הוא סיבת דחייה נפוצה.

1) הקלטת מסך של הזרימה האמיתית, לא הדגמה מדומה. הבודק צריך לראות אדם שמגיב על פוסט אמיתי בחשבון האמיתי, ואת ההודעה שמגיעה בפועל.

2) תיאור שימוש כתוב באנגלית. הנוסח המוכן להדבקה נמצא בהמשך.

3) עמוד מדיניות פרטיות ציבורי בכתובת יציבה, שנטען לגולש אנונימי.

4) כתובת למחיקת נתונים, כלומר עמוד שמסביר איך מבקשים מחיקה ואיך היא מטופלת. עוגן בתוך עמוד הפרטיות מספיק.

5) ייתכן שיידרש אימות עסק מול מטא עם מסמכים. זה תלוי בסוג ההרשאה ובהיסטוריה, ולא תמיד נדרש. אם נדרש, זה החלק הארוך.

6) האפליקציה חייבת להיות במצב Live עם כל השדות הבסיסיים מלאים: שם תצוגה, קטגוריה, מייל יצירת קשר, אייקון וכתובת מדיניות פרטיות.

## תיאור השימוש להדבקה

הטקסט הבא כתוב באנגלית וכללי בכוונה. מחליפים את מה שבסוגריים המשולשים ומדביקים כמו שהוא, בלי להוסיף הבטחות שיווקיות.

```
Use case

I am the owner of the Instagram account <IG_HANDLE>. This app is used only on my own
account, by me, and is not offered as a service to any third party.

What it does: when someone leaves a comment containing a specific keyword on one of my
own media items, the app sends that person a single private reply containing the
information they asked for, for example a link to a resource I mentioned in the post.
The app also posts one short public reply under the comment so the commenter knows a
message was sent.

Why the permission is needed: I need the comments webhook so the private reply is sent
while the person is still looking at the post. Without real-time delivery I have to poll
for new comments, which delays the reply by several minutes and significantly reduces
how many people actually see it.

Limits enforced in the code:
- One private reply per comment.
- At most one message per user per 24 hours, enforced in the database.
- Only comments on media owned by my own account are processed.
- Comments authored by my own account are ignored, so the app never replies to itself.
- Only comments newer than a fixed lookback window are answered.

Data handling: the app stores the commenter's Instagram user id, the comment id, the
comment text and a timestamp. This is the minimum required to avoid sending duplicate
messages. No email addresses, phone numbers or profile data are collected, and nothing
is shared with or sold to any third party. Data is deleted on request through the data
deletion URL published in the app settings.

Test instructions for the reviewer: open the post at <MEDIA_URL>, leave a comment
containing the word <KEYWORD>, and a private reply will arrive within a few seconds.
```

חשוב למלא כתובת פוסט ומילת מפתח אמיתיות, כי הבודק באמת ינסה אותן.

## תסריט הקלטת המסך בשישה ביטים

ההקלטה צריכה להיות רציפה, בלי חיתוכים, באורך של דקה עד שתיים. אם יש מעבר בין שני מכשירים, מצלמים אותם באותה הקלטה ולא מחברים בעריכה.

ביט 1, זהות: פותחים את הפרופיל ומראים את שם החשבון בבירור. זה מוכיח שההקלטה נעשתה על החשבון שמבקש את ההרשאה.

ביט 2, המדיה: נכנסים לפוסט שעליו הכלל פועל ומראים את הכיתוב שבו מוזכרת מילת המפתח. זה קושר בין ההנחיה הפומבית לבין מה שעומד לקרות.

ביט 3, התגובה: עוברים לחשבון אחר ומקלידים תגובה עם מילת המפתח. חשוב שרואים את ההקלדה ואת השליחה, לא תגובה שכבר קיימת.

ביט 4, התגובה הפומבית: מראים את התשובה הקצרה שהמערכת פרסמה. זה ממחיש שהמשתמש מקבל אינדיקציה גלויה ואינו מופתע מהודעה פרטית.

ביט 5, ההודעה: עוברים לתיבת ההודעות של החשבון המגיב ומראים את ההודעה שהגיעה, כולל הטקסט המלא. זה החלק שהבודק בעיקר מחפש.

ביט 6, הגבול: מגיבים שוב עם אותה מילת מפתח מאותו חשבון, ומראים שלא נשלחת הודעה שנייה. זה מדגים בפועל את המגבלה ומחליש חשד לכלי דיוור המוני.

אם אפשר, להוסיף בטופס תיאור קצר של כל ביט עם חותמות זמן. זה מקצר את הבדיקה ומוריד סיכוי לדחייה בנוסח "לא הצלחנו לשחזר".

## סיבות דחייה נפוצות

הקלטה שלא מראה את ההודעה מגיעה בפועל אלא רק את הממשק ששולח אותה, תידחה. הבודק צריך לראות את צד הנמען.

הקלטה שמצולמת על חשבון אחר מזה שמבקש את ההרשאה תידחה, גם אם התהליך זהה.

תיאור שמנוסח כמוצר לצד שלישי מזמין בדיקה מחמירה בהרבה מתיאור שאומר שהשימוש הוא על חשבון אחד של הבעלים. אם זה השימוש האמיתי, לא לנסח אותו כמוצר.

קישור פרטיות או מחיקת נתונים שמחזיר שגיאה ברגע הבדיקה גורר דחייה טכנית מיידית. לבדוק את שניהם בחלון פרטי ביום ההגשה.

## בזמן ההמתנה, ואם נדחים

בזמן ההמתנה המערכת ממשיכה לרוץ במסלול הסורק. אין צורך להשבית דבר ואין צורך לשנות קוד. מסלול ה-webhook כתוב כך שהוא פשוט לא מקבל אירועים עד לאישור, ולא כך שהיעדר אישור שובר משהו.

אם נדחים, הודעת הדחייה כמעט תמיד מציינת סיבה ספציפית. מתקנים בדיוק אותה ומגישים שוב, בלי לשכתב את כל החומרים. ריבוי הגשות שלא נוגעות בסיבה מאריך את התהליך.

אם נדחים פעמיים ואין רצון להיכנס לאימות עסק, זו החלטה לגיטימית להישאר על הסורק לצמיתות. ההפרש הוא בהשהיה בלבד, לא ביכולת.

</div>
