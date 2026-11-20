התקן לי את הסקיל "guide-maker" (סקיל המדריכים). כל התוכן שלו נמצא בהודעה הזו, בין השורות BEGIN ו-END. אין צורך להוריד שום דבר מהאינטרנט.

1. בדוק שההודעה הגיעה שלמה: יש בה שורה שהיא בדיוק =====BEGIN SKILL.md=====, שורה שהיא בדיוק =====END SKILL.md=====, ובאמצע שורה שהיא בדיוק ```html . אם אחת מהן חסרה, עצור ואמור לי בעברית: "ההעתקה נשברה. חזור לקובץ בגיטהאב והעתק רק בכפתור ההעתקה שבפינה העליונה, לא בסימון עם העכבר."
2. בדוק באיזה כלי אתה רץ.
   - אם אתה Claude Code, צור את הקובץ: ~/.claude/skills/guide-maker/SKILL.md
   - אם אתה Codex, צור שני קבצים זהים: ~/.agents/skills/guide-maker/SKILL.md וגם ~/.codex/skills/guide-maker/SKILL.md
   לפני שאתה כותב, אמור לי בשורה אחת: "עכשיו ייתכן שתתבקש לאשר כתיבה לתיקיית ההגדרות של הכלי. זה רגיל, אשר."
3. כתוב לתוכו את כל מה שבין BEGIN ל-END, בדיוק כמו שהוא, בלי לשנות מילה ובלי לכלול את שורות ה-BEGIN וה-END עצמן. אם התיקייה לא קיימת, צור אותה. אם כבר יש קובץ כזה, החלף אותו.
4. בדוק שהקובץ נשמר שלם: קרא את כל הקובץ. חייבות להיות בו בדיוק 280 שורות, הראשונה --- והאחרונה ``` . אם לא, כתוב אותו שוב פעם אחת, ואם עדיין לא, אמור לי.
5. אמור לי בעברית, בארבע שורות: איפה הקובץ נשמר; שצריך לסגור ולפתוח מחדש את הכלי כדי שהסקיל ייטען; שאחרי זה כותבים "תכין לי מדריך", והמדריך יישמר בתיקייה שבה הכלי פתוח; ושבזמן העבודה הוא יבקש אישור לשמור את המדריך ולפתוח אותו בדפדפן, וזה רגיל.

אל תפעיל את הסקיל עכשיו ואל תכתוב מדריך. רק התקנה.

=====BEGIN SKILL.md=====
---
name: guide-maker
description: Writes a finished guide or lead magnet for the owner's business, in the owner's own brand, and saves it as one designed HTML file that can be sent to leads today, plus a phone-sized PDF for WhatsApp. Use whenever the owner says things like "תכין לי מדריך", "תכתוב מדריך ל...", "מגנט לידים", "צריך מדריך ללקוחות שלי", "רעיון למדריך", "make me a guide", "lead magnet", "write a guide for my clients". Always use this instead of writing a guide freehand in the chat, because it collects what is needed to send it today, adds the idea step, a stranger-editor that rejects weak drafts, and the designed file. Not for editing an existing long document, and not for social posts.
---

# סקיל המדריכים

אתה כותב מדריך אחד גמור לעסק של הבעלים, שהבעלים יכול לשלוח ללקוחות שלו עוד היום. הקורא מסיים אותו עם תוצאה ביד ועם סיבה טובה לפנות לעסק. התוצר הוא קובץ HTML אחד, בצבעים ובשם של העסק, שנראה טוב בטלפון ונשמר כ-PDF.

כתוב לבעלים בשפה שבה הוא כתב אליך. אם הוא כתב בעברית, גם המדריך בעברית ומימין לשמאל.

עבוד לפי השלבים הממוספרים, לפי הסדר. אל תדלג על שלב 5.

## שלב 1. מה צריך כדי לשלוח היום

בדוק מה הבעלים כבר סיפר. שאל רק את מה שחסר, הכל בהודעה אחת, ואז חכה לתשובה. זו העצירה היחידה לפני שהמדריך מוכן (חוץ מבחירת רעיון, אם אין נושא).

על העסק, רק מה שלא נאמר:

1. מה העסק עושה, בשני משפטים, ולמי הוא מוכר?
2. מה הכי מעסיק את הלקוח לפני שהוא קונה?
3. מה הקורא צריך לעשות אחרי שסיים? (לקבוע שיחה, לבוא לשיעור ניסיון, לשלוח הודעה)
4. יש נושא למדריך, או שאציע רעיונות?

כדי שהקובץ ייצא מוכן לשליחה, תמיד, חוץ ממה שכבר נמסר:

5. השם של העסק כמו שהלקוחות מכירים אותו, והשם שלך.
6. מספר וואטסאפ או טלפון לפניות, וקישור אם יש (תורים, אתר, אינסטגרם).
7. שניים או שלושה משפטים עליך: כמה זמן אתה בתחום, ולמי אתה עוזר.
8. צבע ראשי של העסק, אם יש. ואם יש תמונה שלך או לוגו, שים את הקובץ בתיקייה הזו ותכתוב לי את השם שלו.

הוסף בסוף השאלות: "מה שאין, תכתוב 'אין' ונמשיך. מה שחסר יסומן בצהוב בקובץ, ואמלא אותו בעצמי כשתשלח לי."

אם אין נושא, שלב 2 נכנס לאותה הודעה: קודם הרעיונות, אחריהם השאלות. אם הבעלים אומר "תחליט אתה", הנח הנחה סבירה, כתוב אותה במשפט, והמשך.

## שלב 2. חמישה רעיונות (רק אם אין נושא)

לכל רעיון ארבע שורות קצרות: השם כמו על השער, למי בדיוק, מה הקורא יעשה בסוף שלא יכול היה קודם, ולמה זה יביא לקוחות לעסק הזה דווקא.

רעיון טוב פותר בעיה אחת קטנה, עם תוצאה שהקורא משיג לבד היום או השבוע. הוא ספציפי מספיק שאין לו תשובה של שורה בגוגל, והוא מוביל לשירות של העסק בלי להרגיש כמו פרסומת. פסול "10 טיפים ל..." ו"המדריך המלא ל...". העדף "הצ'קליסט לפני ש...", "תוכנית 7 ימים ל...", "איך לעשות X בלי Y".

סמן את המומלץ ונמק במשפט.

## שלב 3. המסע, לפני שכותבים

תכנן לעצמך, בלי להציג:

1. משפט ההבטחה: "בסוף המדריך הזה ___". משהו שהקורא עושה או מחזיק, לא "תבין".
2. מי הקורא, מה הוא כבר יודע, ואיפה הוא קורא. ברוב המקרים בטלפון, בהפסקה, מתוך וואטסאפ.
3. ארבעה עד שישה שלבים. כל שלב נגמר בדבר שהקורא עשה, ראה, או מחזיק ביד.
4. הרווח הראשון מגיע במסך הראשון: קופסת "מה יהיה לך ביד בסוף" ופתיחה שאומרת מה עושים בחמש הדקות הקרובות.
5. איפה הקורא עלול להיבהל או לחשוב "זה לא בשבילי". שם משפט הרגעה.
6. הצעד הבא: פעולה אחת, שנובעת ממה שהקורא השיג.
7. הסגנון. המדריך נראה כמו העסק, לא כמו התבנית. בחר אחד: `mood-calm` לבריאות, תנועה, טיפול, הורות ויופי; `mood-trust` לכסף, משפט, ביטוח, נדל"ן ושירותים לעסקים; `mood-editorial` לצילום, עיצוב, אוכל, אירועים ויצירה. הצבע של העסק נכתב ב-`style` של `body` (`style="--brand: #..."`); בלי צבע מהבעלים, בחר גוון שמתאים לתחום. על `--brand` יושב טקסט לבן, ולכן הוא חייב להיות כהה מספיק: אם הצבע של העסק בהיר (צהוב, ורוד או תכלת פסטל), שים ב-`--brand` גוון כהה שלו, ואת הבהיר עצמו ב-`--accent`.

הצג לבעלים שתי שורות: "המדריך יבטיח: ___" ו"הסגנון: ___, כי ___". המשך בלי לחכות.

## שלב 4. הטיוטה, ישר לקובץ

לפני השמירה אמור לבעלים בשורה: "עכשיו אשמור את המדריך. אם תתבקש לאשר, בחר באפשרות שמאשרת את כל העריכות בשיחה הזו, ולא תישאל שוב." אחר כך כתוב את המדריך המלא לתוך התבנית שבסוף הקובץ הזה, ושמור אותו בתיקייה הנוכחית בשם `guide-<שם-קצר-באנגלית>.html`. זו הטיוטה, והעורך יקרא אותה מהקובץ.

התבנית היא השלד: מותר לשכפל רכיבים (שלבים, `say`, `tick`, `note`), להשמיט רכיב שלא צריך, לשנות את ה-class ואת ה-`style` של `body`, ולסמן ב-`<em>` מילה אחת או שתיים בכותרת. אל תמציא עיצוב חדש ואל תוסיף קבצים חיצוניים.

כללי כתיבה:

- ספציפי ולא עקרוני: מספרים, דוגמאות, משפטים שאפשר להגיד מילה במילה, זמנים וכמויות.
- כל שלב: מה עושים, איך בדיוק, ואיך יודעים שזה עבד.
- טלפון: פסקה של שניים או שלושה משפטים לכל היותר, רשימה של עד חמישה פריטים. אורך כולל שנקרא ב-5 עד 7 דקות.
- גוף שני, חם וישיר. בלי "במדריך זה נלמד", בלי "חשוב לזכור", ובלי קו מפריד ארוך (—) באף מקום. במקומו פסיק, נקודה או נקודתיים.
- אל תפתח באזהרות. בתחומי בריאות, תזונה, כושר, מס, משפט, כסף ובעלי חיים: הסתייגות אחת בקופסת `note`, במקום שבו היא רלוונטית, וכל אזהרה באה עם מה עושים במקום. אל תכתוב מספר, סף או מועד שאינך בטוח שהוא עדכני.
- אל תמציא פרטים על העסק: מחיר, כתובת, ותק, הסמכות, המלצות. "נעים להכיר" נכתב רק ממה שהבעלים מסר. לא מסר כלום עליו? מחק את הבלוק.
- כל פרט שחסר נכתב כ-`<mark class="fill">[הטלפון שלך]</mark>`, כדי שיבלוט בצהוב ולא ייעלם.
- תמונה: אם הבעלים שם קובץ בתיקייה, החלף את ה-`span` של ראשי התיבות ב-`<img class="avatar" src="<שם הקובץ>" alt="<השם>">`. אחרת השאר ראשי תיבות של השם. לעולם לא תמונה מהאינטרנט.
- הכפתור בסוף הוא קישור וואטסאפ: `https://wa.me/972` ואחריו המספר בלי האפס הראשון ובלי מקפים (050-1234567 הופך ל-972501234567), ואז `?text=` והודעה קצרה שהקורא שולח, שממשיכה את מה שהשיג. רווחים בהודעה נכתבים `%20`. אין וואטסאפ? קישור `tel:` או הקישור שנמסר. מתחת לכפתור כתוב גם את המספר עצמו, למי שקורא מודפס.
- עדכן את `title` ואת `og:title` ו-`og:description`, כי זה מה שמופיע כשהקישור נשלח בוואטסאפ.

הצעד הבא הוא הזמנה ולא לחץ: "עכשיו שיש לך ___, השלב הבא הוא ___".

## שלב 5. העורך הזר

קרא את הקובץ ששמרת מהדיסק, לא מהזיכרון, והחלף תפקיד. אתה עורך קשוח שלא מכיר את העסק.

הצג לבעלים תחת הכותרת "העורך קרא את הטיוטה":

1. שורה אחת: מי הקורא ואיפה הוא קורא. למשל "אישה בת 42, גב תפוס, קוראת בטלפון בתור לגן".
2. הבעיות שמצאת, מהחמורה לקלה. לכל אחת: ציטוט מדויק מהקובץ, מילה במילה; מה יקרה לקורא הזה בדיוק שם; והתיקון.
3. פסק דין: "נפסל, חוזר לתיקון".

מה מחפשים: הבטחה שהמדריך לא מקיים, שלב שנגמר בהבנה ולא בפעולה, ידע או כלי שחסר לקורא, משפט שמתאים לכל עסק, מקום שבו הוא ייבהל או ישתעמם, מה אפשר למחוק, סיום שמרגיש כמו פרסומת, ומה ימנע מהבעלים לשלוח היום.

שלושה איסורים, כי הם הופכים את העורך לטקס: אל תעבור על הרשימה הזו סעיף אחרי סעיף, דווח רק מה שמצאת. אל תצטט משפט שאינו בקובץ, ואל תמציא גרסה גרועה כדי לבקר אותה. ואל תכתוב בעיה שאין לה תיקון מוחשי.

טיוטה ראשונה תמיד נפסלת, ויש בה לפחות שלוש בעיות אמיתיות. אם החמורות פחות משלוש, גם פסקה ארוכה מדי לטלפון או משפט כללי נחשבים.

## שלב 6. התיקון

תקן בקובץ את כל הממצאים, וקרא אותו שוב מהדיסק. רשום לעצמך את שני התיקונים החשובים, "לפני" בציטוט מהטיוטה ו"אחרי" בציטוט מהקובץ, ופסק דין "עובר" או "עוד תיקון". הם נכנסים לסעיף הראשון בהודעת המסירה. לכל היותר שני סבבים; מה שנשאר, אמור לבעלים במשפט.

## שלב 7. בדיקה, פתיחה ומסירה

בדוק בקריאת הקובץ, או ב-grep פשוט על הקובץ, פקודה אחת בכל פעם, בלי `|`, בלי `;` ובלי `&&`. פקודה משורשרת מבקשת מהבעלים אישור, ואין סיבה להטריד אותו:

- `dir="rtl"` ו-`lang="he"` (באנגלית `ltr` ו-`en`).
- אפס קווים מפרידים ארוכים (—).
- לא נשאר טקסט מהתבנית: "שם העסק", "שם המדריך", "___", "מאת השם", "אני השם", `initials">דנ<`, "050-0000000", "972500000000". חפש את המחרוזות האלה בדיוק, לא חלקים מהן.
- אין `href="#"`. כל סוגריים מרובעים נמצאים בתוך `mark class="fill"`.
- שלב, `check` בכל שלב, ו-`next` אחד בסוף.

אמור "עכשיו אפתח את המדריך בדפדפן. אם תתבקש לאשר, אשר", ופתח: `open <קובץ>` במק, `start <קובץ>` בווינדוס. אם הפתיחה נחסמה, אמור ללחוץ על הקובץ פעמיים.

ואז אמור לבעלים, בקצרה ובסדר הזה:

1. "קריאה שנייה": שני התיקונים החשובים, כל אחד כ"לפני" ו"אחרי", ופסק הדין.
2. איפה הקובץ.
3. מה מסומן בצהוב, אם יש: "תכתוב לי את הפרטים האלה ואכניס אותם. לא צריך לגעת בקוד."
4. איך שולחים. בוואטסאפ: שומרים כ-PDF (בדפדפן, הדפסה ואז "שמור כ-PDF"). הקובץ יוצא בגודל מסך טלפון, ונוח לקרוא אותו בלי הגדלה. ואם יש לך אתר, אפשר להעלות את קובץ ה-HTML כמו שהוא ולשלוח קישור.
5. שאלה אחת: "רוצה לשנות משהו לפני ששולחים? צבע, ניסוח או שלב."

כשהבעלים שולח פרטים או תיקון, עדכן את אותו קובץ ושמור באותו שם.

## התבנית

```html
<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>שם המדריך | שם העסק</title>
<meta property="og:title" content="שם המדריך">
<meta property="og:description" content="משפט ההבטחה">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700;800&family=Rubik:wght@500;700;800&family=Frank+Ruhl+Libre:wght@500;700;900&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #1d1d1b; --muted: #5b5b57; --card: #ffffff; --line: #e8e5de; --fill: #fff1a8;
    --body: "Heebo", "Arial Hebrew", Arial, sans-serif;
  }
  /* שלושה סגנונות. הצבע של העסק נכתב ב-style של body ומנצח את ברירת המחדל */
  .mood-calm { --brand: #2f6f62; --accent: #e9a46a; --paper: #f7f3ec; --head: "Heebo", Arial, sans-serif; --r: 24px; }
  .mood-trust { --brand: #1d3a5f; --accent: #c9a24a; --paper: #f4f6f9; --head: "Rubik", "Heebo", Arial, sans-serif; --r: 12px; }
  .mood-editorial { --brand: #2b2622; --accent: #b5552f; --paper: #fbf8f3; --head: "Frank Ruhl Libre", "Times New Roman", serif; --r: 4px; }
  * { box-sizing: border-box; }
  body { --soft: color-mix(in srgb, var(--brand) 10%, #ffffff); margin: 0; background: var(--paper); color: var(--ink); font-family: var(--body); font-size: 18px; line-height: 1.75; }
  .wrap { max-width: 700px; margin: 0 auto; padding: 0 20px 64px; }
  h1, h2, h3 { font-family: var(--head); }
  .cover { background: var(--brand); color: #fff; padding: 56px 20px 84px; position: relative; overflow: hidden; }
  .cover::before, .cover::after { content: ""; position: absolute; border-radius: 50%; }
  .cover::before { width: 340px; height: 340px; inset-inline-start: -120px; top: -140px; background: rgba(255,255,255,.07); }
  .cover::after { width: 180px; height: 180px; inset-inline-start: 40px; bottom: -70px; background: var(--accent); opacity: .35; }
  .mood-trust .cover::before { border-radius: 40px; transform: rotate(18deg); }
  .mood-editorial .cover { background: var(--paper); color: var(--brand); border-bottom: 6px solid var(--accent); padding-bottom: 64px; }
  .mood-editorial .cover::before, .mood-editorial .cover::after { display: none; }
  .cover .inner { max-width: 700px; margin: 0 auto; position: relative; z-index: 1; }
  .kicker { display: inline-block; font-size: 14px; font-weight: 700; margin: 0 0 18px; padding: 4px 14px; border-radius: 999px; background: rgba(255,255,255,.16); }
  .mood-editorial .kicker { background: none; padding: 0; color: var(--accent); letter-spacing: .04em; }
  h1 { font-size: clamp(32px, 7vw, 52px); line-height: 1.12; font-weight: 800; margin: 0 0 18px; }
  .mood-editorial h1 { font-weight: 900; font-size: clamp(36px, 8vw, 60px); }
  h1 em { font-style: normal; color: var(--accent); }
  .mood-calm h1 em { color: #ffd9b3; }
  .promise { font-size: 20px; margin: 0; max-width: 32em; opacity: .95; }
  .by { display: flex; align-items: center; gap: 12px; margin-top: 26px; font-size: 15px; }
  .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; flex: none; border: 2px solid rgba(255,255,255,.7); }
  .initials { display: inline-flex; align-items: center; justify-content: center; background: var(--accent); color: #fff; font-weight: 800; }
  .get { background: var(--card); border-radius: var(--r); margin: -48px 0 36px; padding: 22px 24px; position: relative; z-index: 2; box-shadow: 0 14px 34px rgba(0,0,0,.08); }
  .mood-editorial .get { margin-top: 28px; box-shadow: none; border: 1px solid var(--line); }
  .get strong { display: block; color: var(--brand); font-family: var(--head); font-size: 19px; margin-bottom: 8px; }
  .get ol { margin: 0; padding: 0; list-style: none; counter-reset: g; }
  .get li { counter-increment: g; position: relative; padding-inline-start: 38px; margin-bottom: 8px; }
  .get li::before { content: counter(g); position: absolute; inset-inline-start: 0; top: 2px; width: 26px; height: 26px; border-radius: 50%; background: var(--soft); color: var(--brand); font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center; }
  .intro { font-size: 19px; margin: 0 0 34px; }
  .step { background: var(--card); border-radius: var(--r); padding: 30px 24px 26px; margin: 0 0 24px; box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 8px 22px rgba(0,0,0,.04); }
  .mood-editorial .step { box-shadow: none; background: none; border-top: 2px solid var(--brand); border-radius: 0; padding-inline: 0; }
  .step-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  .step-num { width: 44px; height: 44px; border-radius: 50%; background: var(--brand); color: #fff; font-family: var(--head); font-weight: 800; font-size: 20px; display: flex; align-items: center; justify-content: center; flex: none; }
  .mood-editorial .step-num { background: none; color: var(--accent); font-size: 44px; width: auto; }
  .of { color: var(--muted); font-size: 14px; font-weight: 500; }
  h2 { font-size: 26px; line-height: 1.3; margin: 0 0 12px; font-weight: 800; }
  h3 { font-size: 19px; margin: 22px 0 6px; }
  p { margin: 0 0 14px; }
  ul, ol { padding-inline-start: 1.3em; margin: 0 0 14px; }
  li { margin-bottom: 6px; }
  .say { background: var(--soft); border-radius: 18px; border-start-start-radius: 4px; padding: 14px 18px; margin: 16px 0; font-weight: 500; max-width: 94%; }
  .calm { color: var(--muted); font-size: 17px; border-inline-start: 3px solid var(--accent); padding-inline-start: 12px; }
  .note { background: #fff5dc; border-radius: 12px; padding: 12px 16px; font-size: 16px; margin: 14px 0; }
  .tick { list-style: none; padding: 0; }
  .tick li { position: relative; padding-inline-start: 34px; margin-bottom: 10px; }
  .tick li::before { content: ""; position: absolute; inset-inline-start: 0; top: 5px; width: 20px; height: 20px; border: 2px solid var(--brand); border-radius: 6px; background: #fff; }
  .check { background: var(--soft); border-radius: 14px; padding: 14px 18px 14px 18px; padding-inline-start: 52px; margin-top: 20px; position: relative; }
  .check::before { content: ""; position: absolute; inset-inline-start: 16px; top: 17px; width: 22px; height: 22px; border-radius: 50%; background: var(--brand); }
  .check::after { content: ""; position: absolute; inset-inline-start: 23px; top: 21px; width: 6px; height: 11px; border: solid #fff; border-width: 0 2.5px 2.5px 0; transform: rotate(45deg); }
  .check strong { color: var(--brand); display: block; }
  .about { display: flex; gap: 18px; align-items: center; margin: 44px 0 0; background: var(--card); border-radius: var(--r); padding: 22px; }
  .about .avatar { width: 96px; height: 96px; border: 0; font-size: 28px; }
  .about h2 { font-size: 22px; margin-bottom: 6px; }
  .about p { margin: 0; }
  .next { background: var(--brand); color: #fff; border-radius: var(--r); padding: 34px 26px; margin-top: 28px; position: relative; overflow: hidden; }
  .next::after { content: ""; position: absolute; width: 160px; height: 160px; border-radius: 50%; background: var(--accent); opacity: .3; inset-inline-end: -50px; top: -60px; }
  .next > * { position: relative; z-index: 1; }
  .next h2 { color: #fff; }
  .btn { display: inline-block; background: #fff; color: var(--brand); font-weight: 800; font-size: 18px; text-decoration: none; padding: 15px 30px; border-radius: 999px; margin-top: 6px; box-shadow: 0 6px 16px rgba(0,0,0,.15); }
  .next .small { font-size: 15px; opacity: .9; margin: 14px 0 0; }
  .next .small a { color: #fff; }
  mark.fill { background: var(--fill); color: #1d1d1b; padding: 0 4px; border-radius: 4px; }
  footer { color: var(--muted); font-size: 14px; text-align: center; margin-top: 40px; }
  @media (max-width: 520px) {
    body { font-size: 17px; }
    .wrap { padding: 0 16px 48px; }
    .cover { padding: 40px 18px 76px; }
    .step { padding: 24px 18px 20px; }
    .about { flex-direction: column; align-items: flex-start; }
  }
  /* PDF בגודל מסך טלפון, כי שולחים אותו בוואטסאפ */
  @media print {
    @page { size: 100mm 178mm; margin: 7mm; }
    body { background: #fff; font-size: 11.5pt; line-height: 1.6; }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .cover { padding: 18px 16px 22px; border-radius: 8px; }
    .cover::before, .cover::after, .next::after { display: none; }
    h1 { font-size: 22pt; } h2 { font-size: 16pt; } .promise { font-size: 12.5pt; }
    .get { margin: 12px 0 14px; box-shadow: none; border: 1px solid var(--line); padding: 12px 14px; }
    .wrap { padding: 0; max-width: none; }
    .intro { font-size: 12pt; margin-bottom: 14px; }
    .step { break-inside: auto; box-shadow: none; border: 0; border-top: 2px solid var(--soft); border-radius: 0; padding: 12px 0 4px; margin: 0 0 8px; }
    h2, h3, .step-head { break-after: avoid; }
    .say, .check, .note, .about, .next, .tick li { break-inside: avoid; }
    .about { flex-direction: column; align-items: flex-start; gap: 8px; margin-top: 18px; padding: 0; }
    .next { padding: 16px; }
  }
</style>
</head>
<body class="mood-calm" style="--brand: #2f6f62">
  <header class="cover">
    <div class="inner">
      <p class="kicker">שם העסק · מדריך חינמי</p>
      <h1>שם המדריך עם <em>מילה אחת מודגשת</em></h1>
      <p class="promise">בסוף המדריך הזה ___.</p>
      <div class="by"><span class="avatar initials">דנ</span><span>מאת השם, התפקיד · כ-6 דקות קריאה</span></div>
    </div>
  </header>

  <main class="wrap">
    <div class="get">
      <strong>מה יהיה לך ביד בסוף</strong>
      <ol><li>תוצאה מוחשית אחת</li><li>תוצאה מוחשית שנייה</li></ol>
    </div>

    <p class="intro">שניים או שלושה משפטים: למי זה, ומה עושים כבר ב-5 הדקות הקרובות.</p>

    <section class="step">
      <div class="step-head"><span class="step-num">1</span><span class="of">מתוך 5</span></div>
      <h2>כותרת השלב, כפעולה</h2>
      <p>מה עושים ואיך בדיוק.</p>
      <div class="say">משפט שאפשר להגיד או להעתיק מילה במילה.</div>
      <ul class="tick"><li>פריט שמסמנים כשהוא מוכן</li></ul>
      <p class="calm">משפט הרגעה, רק איפה שהקורא עלול להיבהל.</p>
      <div class="check"><strong>איך יודעים שזה עבד</strong>מה רואים או מחזיקים עכשיו.</div>
    </section>

    <section class="about">
      <span class="avatar initials">דנ</span>
      <div>
        <h2>נעים להכיר, אני השם</h2>
        <p>שניים או שלושה משפטים שהבעלים מסר: מה הוא עושה, כמה זמן, ולמי.</p>
      </div>
    </section>

    <div class="next">
      <h2>הצעד הבא</h2>
      <p>עכשיו שיש לך ___, השלב הבא הוא ___.</p>
      <a class="btn" href="https://wa.me/972500000000?text=היי,%20סיימתי%20את%20המדריך">הפעולה האחת</a>
      <p class="small">או בטלפון 050-0000000</p>
    </div>

    <footer>שם העסק · כתובת או אתר</footer>
  </main>
</body>
</html>
```
=====END SKILL.md=====
