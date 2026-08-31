-- Instagram keyword→DM automation, 4 טבלאות.
-- כל הטבלאות server-only (service_role בלבד): RLS מופעל, אפס policies, אפס
-- grants, ו-REVOKE כהגנת-עומק, כלומר רק service_role ניגש אליהן; הן לעולם לא נחשפות לדפדפן.

-- ── ig_automation_rules: חוקי מילת-מפתח → DM ─────────────────────────────
-- media_id NULL = חוק גלובלי (כל פוסט/סטורי); אחרת חוק ספציפי למדיה.
-- dm_templates: מערך JSON של נוסחי DM (נבחר אחד אקראית); {{link}} מוחלף
-- ב-link_url. comment_reply_templates: אופציונלי, תגובה פומבית מתחת לתגובה.
create table ig_automation_rules (
  id uuid primary key default gen_random_uuid(),
  name text,
  media_id text,
  keyword text not null,
  match_mode text not null default 'exact' check (match_mode in ('exact', 'contains')),
  dm_templates jsonb not null,
  comment_reply_templates jsonb,
  link_url text,
  active boolean not null default true,
  priority int not null default 0,
  created_at timestamptz default now()
);

alter table ig_automation_rules enable row level security;
revoke all on table ig_automation_rules from anon, authenticated;

-- ── ig_events: יומן אירועים + מנעול idempotency ──────────────────────────
-- event_key ייחודי (comment_id לתגובות, dm:<sender>:<mid> לריפליי-סטורי):
-- ה-claim-INSERT עם on_conflict=event_key הוא מה שמונע DM כפול על retry של מטא.
-- action: claimed → dm_sent / no_match / rate_limited / dm_failed / self_comment.
create table ig_events (
  id bigint generated always as identity primary key,
  event_key text unique not null,
  media_id text,
  ig_user_id text,
  ig_username text,
  comment_text text,
  matched_rule_id uuid references ig_automation_rules(id),
  action text not null default 'claimed',
  dm_template_index int,
  error text,
  created_at timestamptz default now()
);

alter table ig_events enable row level security;
revoke all on table ig_events from anon, authenticated;

-- שאילתת ה-rate-limit: dm_sent לאותו משתמש *ולאותו חוק* ב-24 שעות אחרונות.
create index ig_events_rate_limit_idx on ig_events (ig_user_id, matched_rule_id, action, created_at desc);

-- ── ig_conversations: מצב שיחה פר משתמש+חוק (חלון 24 שעות, ספירת DM) ────
-- שמורה לשלב הבא (follow-up בתוך חלון ההודעות); ה-webhook הנוכחי עוד לא כותב אליה.
create table ig_conversations (
  id bigint generated always as identity primary key,
  ig_user_id text not null,
  rule_id uuid references ig_automation_rules(id),
  last_dm_at timestamptz,
  dm_count int not null default 1,
  window_opened_at timestamptz,
  unique (ig_user_id, rule_id)
);

alter table ig_conversations enable row level security;
revoke all on table ig_conversations from anon, authenticated;

-- ── ig_tokens: טוקן ה-Graph החי, שורה יחידה (id=1) ─────────────────────
-- נקרא ע"י ה-webhook, מרוענן ע"י scripts/refresh-ig-token.sh (launchd) כשנשארו
-- פחות מ-10 ימים לתפוגה.
create table ig_tokens (
  id int primary key default 1 check (id = 1),
  access_token text not null,
  ig_user_id text,
  expires_at timestamptz not null,
  refreshed_at timestamptz default now()
);

alter table ig_tokens enable row level security;
revoke all on table ig_tokens from anon, authenticated;
