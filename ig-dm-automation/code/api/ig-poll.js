// הסורק (poller): המסלול העוקף לרילז כל עוד ה-App Review של webhook התגובות
// לא אושר. במקום שמטא תדחוף אלינו אירועי comments (דורש Advanced Access),
// אנחנו מושכים יזומות את התגובות האחרונות מהמדיה של החשבון ומריצים את אותו
// מנוע: claim -> match -> rate-limit -> private reply + public reply -> log.
//
// אותה טבלת ig_events ואותו event_key (comment id) כמו ה-webhook: כשה-Review
// יאושר וה-webhook יתחיל לירות, ה-claim ימנע כפילות בין שני המסלולים.
//
// הגנת עבר: תגובות שנוצרו לפני POLL_LOOKBACK_MS (ברירת מחדל: שעתיים) נרשמות
// כ-'expired_backlog' בלי שליחה, כדי שהפעלה ראשונה לא תשלח DM לכל
// היסטוריית התגובות של החשבון.
import crypto from 'node:crypto';
import { getToken, sendPrivateReply, sendCommentReply } from './_ig-graph.js';
import { matchRule } from './_ig-rules.js';
import {
  claimEvent, finalizeEvent, loadActiveRules, isRateLimited,
  pickTemplate, renderTemplate,
} from './_ig-store.js';

const GRAPH_BASE = 'https://graph.instagram.com/v23.0';
const MEDIA_LIMIT = 10;          // כמה פריטי מדיה אחרונים נסרקים בכל סבב
const COMMENTS_LIMIT = 25;       // כמה תגובות פר עמוד (Graph מחזיר newest-first)
const MAX_COMMENT_PAGES = 8;     // תקרת עימוד פר מדיה (8x25 = עד 200 תגובות/מדיה/סבב)
// עימוד (נוסף אחרי ביקורת "עודף אבד"): 25 האחרונות הן החדשות ביותר, אבל אם סבב
// התעכב שעות (GitHub Actions נדחה, או ריפו הושהה) וריל התפוצץ עם יותר מ-25 תגובות
// חדשות בין סבבים, ה-25 לבד מפספסות את העודף. לכן ממשיכים לעמודים ישנים יותר כל
// עוד התגובה הישנה-ביותר בעמוד עדיין בתוך חלון ההסתכלות, עד MAX_COMMENT_PAGES או
// תקציב הזמן. ה-claim על event_key מבטיח שאין DM כפול גם בסריקה חופפת.
const POLL_LOOKBACK_MS = 2 * 3600 * 1000; // תגובה ישנה מזה = backlog, בלי שליחה
// שומר תקציב-זמן (הגנת תקציב זמן): נבדק לפני כל claim. הריגה ב-60s אחרי claim הייתה
// משאירה שורת claimed בלי DM שהסבב הבא מדלג עליה, לכן עוצרים נקי ב-45s,
// והסבב הבא ממשיך בדיוק מאיפה שנעצרנו (הכל עדיין לא-claimed).
const TIME_BUDGET_MS = 45000;

async function graphGet(path, token) {
  // path יכול להיות נתיב יחסי, או URL מוחלט (paging.next של Graph מגיע כ-URL מלא)
  const url = path.startsWith('http') ? path : GRAPH_BASE + path;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 10000);
  try {
    const r = await fetch(url, {
      headers: { Authorization: 'Bearer ' + token },
      signal: ctrl.signal,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) {
      const err = data.error || {};
      return { ok: false, error: 'graph ' + r.status + ' ' + (err.message || '') };
    }
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e && e.name === 'AbortError' ? 'graph timeout' : 'graph exception ' + (e && e.message) };
  } finally {
    clearTimeout(timer);
  }
}

function timingSafeEq(a, b) {
  const ba = Buffer.from(String(a || ''));
  const bb = Buffer.from(String(b || ''));
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}

export default async function handler(req, res) {
  const secret = process.env.IG_POLL_SECRET;
  const sbUrl = process.env.SUPABASE_URL;
  const sbKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const selfId = process.env.IG_SELF_USER_ID;
  if (!secret || !sbUrl || !sbKey || !selfId) {
    // אבחון בטוח: שמות חסרים בלבד, אף פעם לא ערכים
    res.status(500).json({
      error: 'not configured',
      missing: { IG_POLL_SECRET: !secret, SUPABASE_URL: !sbUrl, SUPABASE_SERVICE_ROLE_KEY: !sbKey, IG_SELF_USER_ID: !selfId },
    });
    return;
  }
  // אימות קורא: header בלבד, השוואה בזמן קבוע. בלי סוד = 403, בלי חריגים.
  if (!timingSafeEq(req.headers['x-poll-secret'], secret)) {
    res.status(403).json({ error: 'forbidden' });
    return;
  }

  const sb = { url: sbUrl.replace(/\/$/, ''), key: sbKey };
  const token = await getToken(sb);
  if (!token) {
    res.status(200).json({ ok: false, error: 'no token' });
    return;
  }

  let rules;
  try {
    rules = await loadActiveRules(sb);
  } catch (e) {
    res.status(200).json({ ok: false, error: 'rules load failed' });
    return;
  }
  if (rules.length === 0) {
    res.status(200).json({ ok: true, scanned: 0, note: 'no active rules' });
    return;
  }

  // מצב יבש: מאשר שהכל מוגדר ומחובר, ועוצר לפני שנוגעים בתגובות.
  // קיים כדי שכלי אבחון יוכל לבדוק את הבריאות בלי להריץ מחזור אמיתי
  // ובלי לשלוח הודעה לאדם אמיתי. בדיקה שיש לה תופעת לוואי אינה בדיקה.
  if (String(req.headers['x-poll-dry-run'] || '') === '1') {
    res.status(200).json({ ok: true, dryRun: true, activeRules: rules.length, tokenPresent: true });
    return;
  }

  const media = await graphGet('/me/media?fields=id,media_product_type,comments_count&limit=' + MEDIA_LIMIT, token);
  if (!media.ok) {
    res.status(200).json({ ok: false, error: media.error });
    return;
  }

  const counters = { scanned: 0, sent: 0, no_match: 0, duplicate: 0, rate_limited: 0, backlog: 0, failed: 0, truncated: false };
  const startedAt = Date.now();
  const cutoff = startedAt - POLL_LOOKBACK_MS;

  outer:
  for (const m of media.data.data || []) {
    if (!m.id || !m.comments_count) continue;
    let nextPath = '/' + m.id + '/comments?fields=id,text,username,from,timestamp&limit=' + COMMENTS_LIMIT;
    let pages = 0;

    // עימוד: כל עוד יש עמוד הבא, לא עברנו את תקרת העמודים, והתגובה הישנה-ביותר
    // בעמוד עדיין בתוך החלון. break outer על תקציב הזמן משאיר את השאר לסבב הבא.
    while (nextPath && pages < MAX_COMMENT_PAGES) {
      if (Date.now() - startedAt > TIME_BUDGET_MS) { counters.truncated = true; break outer; }
      const c = await graphGet(nextPath, token);
      if (!c.ok) { counters.failed++; break; }
      pages++;
      const list = c.data.data || [];

      for (const cm of list) {
        if (!cm.id) continue;
        // שומר תקציב-זמן לפני ה-claim (הגנת תקציב זמן): עצירה נקייה, בלי שורות יתומות
        if (Date.now() - startedAt > TIME_BUDGET_MS) { counters.truncated = true; break outer; }
        counters.scanned++;
        const from = cm.from || {};
        const isSelf = from.id && String(from.id) === String(selfId);
        // fail-closed: timestamp חסר או לא-נפרס = מתייחסים כישן (backlog), לא שולחים
        const ts = cm.timestamp ? Date.parse(cm.timestamp) : NaN;
        const tooOld = !(ts > cutoff);

        // claim לפני כל דבר, תגובה שכבר טופלה (מכל מסלול) נופלת כאן כ-duplicate
        let claimed;
        try {
          claimed = await claimEvent(sb, {
            event_key: String(cm.id),
            media_id: String(m.id),
            ig_user_id: from.id ? String(from.id) : null,
            ig_username: from.username || cm.username || null,
            comment_text: String(cm.text || '').slice(0, 2000),
            action: isSelf ? 'self_comment' : tooOld ? 'expired_backlog' : 'claimed',
          });
        } catch (e) {
          counters.failed++;
          continue; // הסבב הבא ינסה שוב, האירוע לא נתפס
        }
        if (!claimed) { counters.duplicate++; continue; }
        if (isSelf || tooOld) { if (tooOld && !isSelf) counters.backlog++; continue; }

        const rule = matchRule(cm.text, rules, m.id);
        if (!rule) {
          await finalizeEvent(sb, claimed.id, { action: 'no_match' });
          counters.no_match++;
          continue;
        }
        if (from.id && (await isRateLimited(sb, String(from.id), rule.id))) {
          await finalizeEvent(sb, claimed.id, { action: 'rate_limited', matched_rule_id: rule.id });
          counters.rate_limited++;
          continue;
        }

        const tpl = pickTemplate(rule.dm_templates);
        if (!tpl) {
          await finalizeEvent(sb, claimed.id, { action: 'dm_failed', matched_rule_id: rule.id, error: 'rule has no usable dm_templates' });
          counters.failed++;
          continue;
        }
        const sent = await sendPrivateReply(token, String(cm.id), renderTemplate(tpl.text, rule));
        if (!sent.ok) {
          await finalizeEvent(sb, claimed.id, {
            action: 'dm_failed', matched_rule_id: rule.id, dm_template_index: tpl.idx,
            error: String(sent.error || 'unknown').slice(0, 500),
          });
          counters.failed++;
          continue;
        }
        const pub = pickTemplate(rule.comment_reply_templates);
        if (pub) {
          const pr = await sendCommentReply(token, String(cm.id), renderTemplate(pub.text, rule));
          if (!pr.ok) console.error('comment reply failed', cm.id, String(pr.error || '').slice(0, 200));
        }
        await finalizeEvent(sb, claimed.id, { action: 'dm_sent', matched_rule_id: rule.id, dm_template_index: tpl.idx });
        counters.sent++;
      }

      // האם להמשיך לעמוד הבא? רק אם התגובה הישנה-ביותר בעמוד (האחרונה, newest-first)
      // עדיין בתוך החלון, כלומר ייתכן שיש עוד תגובות טריות מעבר לעמוד הזה.
      const oldest = list.length ? list[list.length - 1] : null;
      const oldestTs = oldest && oldest.timestamp ? Date.parse(oldest.timestamp) : NaN;
      const moreWithinWindow = !!(oldest && oldestTs > cutoff);
      if (!moreWithinWindow) break;
      // עוקבים אחרי paging.next רק אם הוא באמת כתובת Graph. הטוקן נשלח כ-header
      // בכל graphGet, אז URL זר בתשובה משובשת = דליפת טוקן. הגנה זולה.
      const nx = c.data.paging && c.data.paging.next;
      nextPath = (typeof nx === 'string' && nx.startsWith('https://graph.instagram.com/')) ? nx : null;
      // הגענו לתקרת העמודים אבל עדיין בתוך החלון = ייתכן שנשאר עודף שלא נסרק
      if (nextPath && pages >= MAX_COMMENT_PAGES) counters.truncated = true;
    }
  }

  console.log('ig-poll done', JSON.stringify(counters));
  res.status(200).json(Object.assign({ ok: true }, counters));
}
