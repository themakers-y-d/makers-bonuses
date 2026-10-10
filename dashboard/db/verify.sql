-- ============================================================
-- שער האבטחה. מריצים אחרי schema.sql ומראים את הפלט לבעלים.
--
-- שאילתה אחת בכוונה: עורך ה-SQL של סופאבייס מציג רק את תוצאת
-- השאילתה האחרונה, ולכן קובץ עם שלוש שאילתות נפרדות היה מציג
-- שליש מהשער ונקרא כאילו כולו ירוק.
--
-- כל תשע השורות חייבות להתחיל ב"ירוק". שורה אדומה אחת = עוצרים.
-- הבדיקה סורקת את סכמת public. אם נחשפה סכמה נוספת ב-Data API,
-- צריך להרחיב אותה, וזו מגבלה מודעת ולא חור.
-- ============================================================

with t as (select to_regclass('public.entries') as rel),
checks as (
  select 1 as n, 'הטבלה קיימת' as what,
         (select rel is not null from t) as ok
  union all
  select 2, 'הרשאות ברמת השורה דלוקות וכפויות',
         (select coalesce(c.relrowsecurity and c.relforcerowsecurity, false)
          from t left join pg_class c on c.oid = t.rel)
  union all
  select 3, 'לאורח לא מזוהה אין שום הרשאה',
         (select case when t.rel is null then false else not (
            has_table_privilege('anon', t.rel, 'select') or
            has_table_privilege('anon', t.rel, 'insert') or
            has_table_privilege('anon', t.rel, 'update') or
            has_table_privilege('anon', t.rel, 'delete')) end from t)
  union all
  select 4, 'למשתמש מזוהה יש קריאה',
         (select case when t.rel is null then false
                 else has_table_privilege('authenticated', t.rel, 'select') end from t)
  union all
  select 5, 'יש מדיניות, וכולן למשתמש מזוהה בלבד',
         (select count(*) > 0 and bool_and(p.roles = '{authenticated}'::name[])
          from pg_policies p where p.schemaname = 'public' and p.tablename = 'entries')
  union all
  select 6, 'אין מדיניות פתוחה לרווחה',
         (select count(*) > 0 and bool_and(
            coalesce(p.qual, '') <> 'true' and coalesce(p.with_check, '') <> 'true')
          from pg_policies p where p.schemaname = 'public' and p.tablename = 'entries')
  union all
  -- הבדיקה שתופסת את הדליפה הנפוצה ביותר. שלוש משפחות:
  -- View שרץ בהרשאות היוצר שלו ולכן עוקף את ההרשאות ברמת השורה,
  -- View מוחומר שאין לו מנגנון כזה בכלל ולכן הוא תמיד עוקף,
  -- וטבלה שנולדה בלי הרשאות ברמת שורה.
  -- ההמרה ל-boolean ולא השוואת מחרוזת: פוסטגרס שומר את הערך כפי
  -- שנכתב, ולכן security_invoker = on נשמר כ-on ולא כ-true.
  select 7, 'אין View, View מוחומר או טבלה שעוקפים את ההרשאות',
         (select not exists (
            select 1 from pg_class c join pg_namespace ns on ns.oid = c.relnamespace
            where ns.nspname = 'public' and c.relkind in ('r','v','m')
              and (
                has_table_privilege('anon', c.oid, 'select')
                or (c.relkind = 'v'
                    and coalesce((select option_value::boolean
                                  from pg_options_to_table(c.reloptions)
                                  where option_name = 'security_invoker'), false) is not true
                    and has_table_privilege('authenticated', c.oid, 'select'))
                or (c.relkind = 'm' and has_table_privilege('authenticated', c.oid, 'select'))
                or (c.relkind = 'r' and not c.relrowsecurity
                    and has_table_privilege('authenticated', c.oid, 'select'))
              )))
  union all
  -- טבלה שנייה עם מדיניות פתוחה לרווחה היא דרך לקרוא את הכל
  -- שלא עוברת דרך entries, ולכן אף בדיקה שמסוננת לטבלה אחת לא רואה אותה.
  select 8, 'אין מדיניות פתוחה לרווחה בשום טבלה',
         (select not exists (
            select 1 from pg_policies p
            where p.schemaname = 'public'
              and (coalesce(p.qual, '') = 'true' or coalesce(p.with_check, '') = 'true')))
  union all
  -- פונקציית security definer רצה בהרשאות היוצר, וכל פונקציה חדשה
  -- נולדת עם הרשאת הרצה לכולם. זו דלת אחורית שנייה לנתונים.
  -- ההבחנה חשובה: פונקציית עזר שמחזירה בוליאני למדיניות חייבת
  -- להישאר מורשית למשתמש מזוהה, אחרת המדיניות עצמה נשברת. מה
  -- שאסור הוא פונקציה שאורח יכול להריץ, או שמחזירה שורות.
  select 9, 'אין פונקציית security definer פתוחה לאורח או שמחזירה שורות',
         (select not exists (
            select 1 from pg_proc pr
            join pg_namespace n on n.oid = pr.pronamespace
            join pg_type rt on rt.oid = pr.prorettype
            where n.nspname = 'public' and pr.prosecdef
              and rt.typname <> 'trigger'
              and (
                has_function_privilege('anon', pr.oid, 'execute')
                or (has_function_privilege('authenticated', pr.oid, 'execute')
                    and (pr.proretset or rt.typtype = 'c'
                         or rt.typname in ('json','jsonb','record')))
              )))
)
select n as "בדיקה",
       case when ok then 'ירוק: ' else 'אדום: ' end || what as "תוצאה"
from checks order by n;


-- ============================================================
-- הבלוק הבא מוער בכוונה, ואסור להסיר את ההערה לפני שהשער רץ.
--
-- הסיבה: העורך מציג תוצאה אחת בלבד. אם שאילתת האשם מחזירה שורות,
-- היא דורסת את תשע השורות של השער, וכך דווקא ברגע שבו השער נכשל
-- הוא נעלם מהמסך ולא נשארת הוכחה להראות לבעלים.
--
-- רק אם בדיקה 7, 8 או 9 חזרו אדומות: סמנו את הבלוק, הסירו את
-- ההערה, והריצו אותו לבד בהרצה נפרדת. הוא אומר מי בדיוק האשם.
-- ============================================================
/*
select c.relname as "אובייקט חשוד", c.relkind as "סוג",
       has_table_privilege('anon', c.oid, 'select') as "אורח קורא",
       has_table_privilege('authenticated', c.oid, 'select') as "מזוהה קורא",
       coalesce((select option_value from pg_options_to_table(c.reloptions)
                 where option_name = 'security_invoker'), 'לא מוגדר') as "security_invoker"
from pg_class c join pg_namespace ns on ns.oid = c.relnamespace
where ns.nspname = 'public' and c.relkind in ('r','v','m')
  and ( has_table_privilege('anon', c.oid, 'select')
     or (c.relkind = 'v'
         and coalesce((select option_value::boolean from pg_options_to_table(c.reloptions)
                       where option_name = 'security_invoker'), false) is not true
         and has_table_privilege('authenticated', c.oid, 'select'))
     or (c.relkind = 'm' and has_table_privilege('authenticated', c.oid, 'select'))
     or (c.relkind = 'r' and not c.relrowsecurity
         and has_table_privilege('authenticated', c.oid, 'select')) )
union all
select pr.proname, 'f',
       has_function_privilege('anon', pr.oid, 'execute'),
       has_function_privilege('authenticated', pr.oid, 'execute'),
       'security definer'
from pg_proc pr join pg_namespace n on n.oid = pr.pronamespace
                join pg_type rt on rt.oid = pr.prorettype
where n.nspname = 'public' and pr.prosecdef and rt.typname <> 'trigger'
  and ( has_function_privilege('anon', pr.oid, 'execute')
     or (has_function_privilege('authenticated', pr.oid, 'execute')
         and (pr.proretset or rt.typtype = 'c'
              or rt.typname in ('json','jsonb','record'))) )
order by 1;
*/
