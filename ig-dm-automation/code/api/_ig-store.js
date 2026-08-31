// שכבת ה-DB המשותפת ל-webhook ולסורק (poller): claim, finalize, rate-limit,
// בחירת נוסח ורינדור. קובץ underscore, לא נחשף כ-endpoint.

const RATE_LIMIT_WINDOW_MS = 24 * 3600 * 1000; // DM אחד למשתמש *לכל חוק* ביממה

export function sbHeaders(key, extra) {
  return Object.assign(
    { apikey: key, Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' },
    extra || {}
  );
}

// claim-INSERT: מחזיר את השורה שנוצרה, או null אם ה-event_key כבר קיים (כפילות).
// כשל HTTP זורק, המתקשר מחליט אם זה 500 (webhook) או דילוג (poller).
export async function claimEvent(sb, row) {
  const r = await fetch(sb.url + '/rest/v1/ig_events?on_conflict=event_key', {
    method: 'POST',
    headers: sbHeaders(sb.key, { Prefer: 'resolution=ignore-duplicates,return=representation' }),
    body: JSON.stringify(row),
  });
  if (!r.ok) {
    const t = await r.text().catch(() => '');
    throw new Error('ig_events claim failed ' + r.status + ' ' + t.slice(0, 200));
  }
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

// עדכון סופי של שורת האירוע, best-effort, כשל לא מפיל את הזרימה.
export async function finalizeEvent(sb, id, patch) {
  try {
    const r = await fetch(sb.url + '/rest/v1/ig_events?id=eq.' + encodeURIComponent(id), {
      method: 'PATCH',
      headers: sbHeaders(sb.key, { Prefer: 'return=minimal' }),
      body: JSON.stringify(patch),
    });
    if (!r.ok) console.error('ig_events finalize failed', r.status, id);
  } catch (e) {
    console.error('ig_events finalize exception', e && e.message);
  }
}

export async function loadActiveRules(sb) {
  const r = await fetch(
    sb.url + '/rest/v1/ig_automation_rules?select=*&active=eq.true&order=priority.desc',
    { headers: sbHeaders(sb.key) }
  );
  if (!r.ok) throw new Error('rules load failed ' + r.status);
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) ? rows : [];
}

// המשתמש כבר קיבל DM *עבור החוק הזה* ב-24 השעות האחרונות? החסימה היא פר (משתמש,
// חוק): שני רילז עם שתי מילות-מפתח ושני לינקים = שני DM נשלחים; אותה מילה פעמיים =
// עדיין נחסם. ruleId ריק = fallback לחסימה גלובלית לאותו משתמש (fail-safe). ספק
// (שגיאת רשת) = לא חוסמים, כי ה-claim הוא מה שמגן מכפילות אמיתית.
export async function isRateLimited(sb, igUserId, ruleId) {
  const since = new Date(Date.now() - RATE_LIMIT_WINDOW_MS).toISOString();
  let q =
    '/rest/v1/ig_events?select=id&action=eq.dm_sent&ig_user_id=eq.' +
    encodeURIComponent(igUserId) +
    '&created_at=gte.' + encodeURIComponent(since) + '&limit=1';
  if (ruleId) q += '&matched_rule_id=eq.' + encodeURIComponent(ruleId);
  const r = await fetch(sb.url + q, { headers: sbHeaders(sb.key) });
  if (!r.ok) return false;
  const rows = await r.json().catch(() => []);
  return Array.isArray(rows) && rows.length > 0;
}

export function pickTemplate(templates) {
  if (!Array.isArray(templates) || templates.length === 0) return null;
  const idx = Math.floor(Math.random() * templates.length);
  const text = templates[idx];
  return typeof text === 'string' && text.trim() ? { idx, text } : null;
}

export function renderTemplate(text, rule) {
  // פונקציה ולא מחרוזת-החלפה: מחרוזת מפרשת $& ודומיו בתוך link_url (בטיחות תווים מיוחדים)
  return text.replace(/\{\{\s*link\s*\}\}/g, () => rule.link_url || '');
}
