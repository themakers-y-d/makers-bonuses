-- ============================================================
-- הדאשבורד של הבעלים. טבלה אחת, והרשאות נעולות לבעלים בלבד.
--
-- מריצים פעם אחת ב-SQL Editor של פרויקט הסופאבייס של הבעלים,
-- ומיד אחרי זה מריצים את db/verify.sql ומראים לו את הפלט.
-- בלי האימות הזה הפריסה לא נחשבת גמורה.
--
-- הקובץ בטוח להרצה חוזרת: כל מדיניות נמחקת לפני שהיא נוצרת,
-- כי ל-CREATE POLICY אין IF NOT EXISTS והרצה שנייה הייתה נופלת.
-- ============================================================

create table if not exists public.entries (
  id          uuid primary key default gen_random_uuid(),
  -- אין כאן default auth.uid(). בכל מסלול שבו הסוכן באמת כותב,
  -- כלומר עורך ה-SQL או מפתח מאובטח, auth.uid() הוא NULL וההכנסה
  -- הייתה נופלת. מזהה הבעלים נשלף מ-auth.users לפי המייל ונכתב מפורש.
  owner_id    uuid not null references auth.users(id) on delete cascade,
  date        date not null,
  type        text not null check (type in ('lead','sale')),
  source      text,
  name        text,
  amount      numeric(12,2) not null default 0,
  status      text not null default 'חדש'
              check (status in ('חדש','בשיחה','נסגר','לא רלוונטי')),
  note        text,
  created_at  timestamptz not null default now()
);

create index if not exists entries_owner_date_idx
  on public.entries (owner_id, date desc);

-- ============================================================
-- ההרשאות. זה החלק שאסור לדלג עליו.
--
-- בלי RLS, כל מי שמחזיק את המפתח הציבורי של הפרויקט, והוא באמת
-- ציבורי כי הוא יושב בקוד של הדף, יכול לקרוא את כל הטבלה. כלומר
-- את רשימת הלקוחות של הבעלים ואת הסכומים שלהם.
-- ============================================================

alter table public.entries enable row level security;
alter table public.entries force row level security;

drop policy if exists "owner reads own rows"   on public.entries;
drop policy if exists "owner writes own rows"  on public.entries;
drop policy if exists "owner updates own rows" on public.entries;
drop policy if exists "owner deletes own rows" on public.entries;

create policy "owner reads own rows"
  on public.entries for select
  to authenticated
  using (auth.uid() = owner_id);

create policy "owner writes own rows"
  on public.entries for insert
  to authenticated
  with check (auth.uid() = owner_id);

create policy "owner updates own rows"
  on public.entries for update
  to authenticated
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

create policy "owner deletes own rows"
  on public.entries for delete
  to authenticated
  using (auth.uid() = owner_id);

-- חגורה שנייה. סופאבייס מעניקה ל-anon הרשאות טבלה כברירת מחדל,
-- וזה הדבר היחיד ששורד מישהו שיכבה RLS בטעות מתישהו.
revoke all on public.entries from anon;

-- והדף חייב לקרוא כמשתמש מזוהה, אחרת הבעלים רואה מסך ריק
-- ומחפש את הבעיה במקום הלא נכון.
grant select on public.entries to authenticated;
