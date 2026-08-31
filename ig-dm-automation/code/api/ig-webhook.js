// Webhook מאינסטגרם (Meta): תגובה על פוסט/רילס או ריפליי לסטורי עם מילת-מפתח
// גוררת DM אוטומטי עם לינק, לפי חוקים בטבלת ig_automation_rules.
//
// עקרונות אבטחה שאסור לוותר עליהם:
// (א) אימות חתימה, X-Hub-Signature-256 = HMAC-SHA256 על ה-raw body עם
//     META_APP_SECRET, השוואה בזמן-קבוע (timingSafeEqual). חתימה שגויה = 403.
// (ב) idempotency, claim-INSERT ל-ig_events עם event_key ייחודי *לפני* שליחת
//     ה-DM (on_conflict=event_key + ignore-duplicates): retry של מטא לעולם לא
//     שולח DM כפול.
// (ג) rate-limit, DM אחד לכל משתמש *לכל חוק* ב-24 שעות (נבדק מול ig_events).
// (ד) always-200, אחרי עיבוד תמיד 200 (מטא לא עושה retry-storm); 500 רק על
//     כשל DB בשלב ה-claim (אז retry של מטא בטוח בזכות ב'). חתימה = 403.
// (ה) אפס סודות בקוד ואפס לוגים של טוקנים.
import crypto from 'node:crypto';
import { getToken, sendPrivateReply, sendDm, sendCommentReply } from './_ig-graph.js';
import { matchRule } from './_ig-rules.js';
// שכבת ה-DB המשותפת עם הסורק (ig-poll), אותו claim, אותו rate-limit, אותו רינדור.
import {
  claimEvent, finalizeEvent, loadActiveRules, isRateLimited,
  pickTemplate, renderTemplate,
} from './_ig-store.js';

// הערה: config.api.bodyParser היא קונבנציית Next.js, ראנטיים
// Vercel רגיל מתעלם ממנה. הקוד בטוח בלעדיה: req.body הוא getter עצל שאיש לא
// קורא, ו-readRawBody קורא את ה-stream הגולמי ישירות. הושארה כתיעוד-כוונה
// בלבד; אין להסתמך עליה ואין להגדיר NODEJS_HELPERS=0 (ימחק את res.status/json).
export const config = { api: { bodyParser: false } };

async function readRawBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(typeof c === 'string' ? Buffer.from(c) : c);
  return Buffer.concat(chunks);
}

// השוואת-חתימה בזמן-קבוע; בדיקת האורך קודם כי timingSafeEqual זורק על אורכים שונים.
function validSignature(raw, header, secret) {
  const expected = 'sha256=' + crypto.createHmac('sha256', secret).update(raw).digest('hex');
  const a = Buffer.from(String(header || ''));
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// שטוח: הופך את מבנה ה-entry של מטא לרשימת אירועים אחידה לעיבוד.
function collectEvents(body, selfId) {
  const events = [];
  for (const entry of Array.isArray(body.entry) ? body.entry : []) {
    // (א) תגובות על פוסט/רילס
    for (const ch of Array.isArray(entry.changes) ? entry.changes : []) {
      if (!ch || ch.field !== 'comments') continue;
      const v = ch.value || {};
      if (!v.id) continue;
      const from = v.from || {};
      events.push({
        kind: 'comment',
        eventKey: String(v.id),
        commentId: String(v.id),
        text: String(v.text || ''),
        userId: from.id ? String(from.id) : null,
        username: from.username ? String(from.username) : null,
        mediaId: v.media && v.media.id ? String(v.media.id) : null,
        isSelf: !!(selfId && from.id && String(from.id) === selfId),
      });
    }
    // (ב) ריפליי לסטורי (מגיע כהודעת DM עם reply_to.story)
    for (const m of Array.isArray(entry.messaging) ? entry.messaging : []) {
      const msg = (m && m.message) || {};
      if (msg.is_echo) continue; // echo של DM שאנחנו שלחנו, לא אירוע
      const story = msg.reply_to && msg.reply_to.story;
      if (!story) continue; // DM רגיל שאינו ריפליי-לסטורי, מחוץ לסקופ
      const senderId = m.sender && m.sender.id ? String(m.sender.id) : null;
      if (!senderId || !msg.mid) continue;
      if (selfId && senderId === selfId) continue; // ריפליי של עצמנו, דילוג שקט
      events.push({
        kind: 'story',
        eventKey: 'dm:' + senderId + ':' + String(msg.mid),
        commentId: null,
        text: String(msg.text || ''),
        userId: senderId,
        username: null,
        mediaId: story.id ? String(story.id) : null,
        isSelf: false,
      });
    }
  }
  return events;
}

async function processEvent(sb, ev, rules) {
  // 1) claim לפני כל דבר אחר, תגובת-עצמי נרשמת ישר כ-self_comment
  const claimed = await claimEvent(sb, {
    event_key: ev.eventKey,
    media_id: ev.mediaId,
    ig_user_id: ev.userId,
    ig_username: ev.username,
    comment_text: ev.text.slice(0, 2000),
    action: ev.isSelf ? 'self_comment' : 'claimed',
  });
  if (!claimed) return 'duplicate';
  if (ev.isSelf) return 'self_comment';

  // 2+3) התאמת מילת-מפתח (החוקים נטענו לפני לולאת ה-claims)
  const rule = matchRule(ev.text, rules, ev.mediaId);
  if (!rule) {
    await finalizeEvent(sb, claimed.id, { action: 'no_match' });
    return 'no_match';
  }

  // 4) rate-limit פר (משתמש, חוק): לינק אחד לאותו אדם לכל מילת-מפתח ביממה
  if (ev.userId && (await isRateLimited(sb, ev.userId, rule.id))) {
    await finalizeEvent(sb, claimed.id, { action: 'rate_limited', matched_rule_id: rule.id });
    return 'rate_limited';
  }

  // 5) שליחה
  const token = await getToken(sb);
  if (!token) {
    await finalizeEvent(sb, claimed.id, { action: 'dm_failed', matched_rule_id: rule.id, error: 'no access token (ig_tokens empty and no IG_ACCESS_TOKEN)' });
    return 'dm_failed';
  }
  const tpl = pickTemplate(rule.dm_templates);
  if (!tpl) {
    await finalizeEvent(sb, claimed.id, { action: 'dm_failed', matched_rule_id: rule.id, error: 'rule has no usable dm_templates' });
    return 'dm_failed';
  }
  const dmText = renderTemplate(tpl.text, rule);
  const sent = ev.kind === 'comment'
    ? await sendPrivateReply(token, ev.commentId, dmText)
    : await sendDm(token, ev.userId, dmText);

  if (!sent.ok) {
    await finalizeEvent(sb, claimed.id, {
      action: 'dm_failed',
      matched_rule_id: rule.id,
      dm_template_index: tpl.idx,
      error: String(sent.error || 'unknown').slice(0, 500),
    });
    return 'dm_failed';
  }

  // תגובה פומבית על התגובה (אופציונלי, best-effort, כשל לא משנה את הסטטוס)
  if (ev.kind === 'comment') {
    const pub = pickTemplate(rule.comment_reply_templates);
    if (pub) {
      const pr = await sendCommentReply(token, ev.commentId, renderTemplate(pub.text, rule));
      if (!pr.ok) console.error('comment reply failed', ev.eventKey, String(pr.error || '').slice(0, 200));
    }
  }

  // 6) רישום סופי
  await finalizeEvent(sb, claimed.id, {
    action: 'dm_sent',
    matched_rule_id: rule.id,
    dm_template_index: tpl.idx,
  });
  return 'dm_sent';
}

export default async function handler(req, res) {
  // GET, לחיצת-יד של אימות ה-webhook מול מטא
  if (req.method === 'GET') {
    const u = new URL(req.url, 'https://localhost');
    const mode = u.searchParams.get('hub.mode');
    const token = u.searchParams.get('hub.verify_token');
    const challenge = u.searchParams.get('hub.challenge');
    const expected = process.env.IG_VERIFY_TOKEN;
    if (mode === 'subscribe' && expected && token === expected) {
      res.setHeader('Content-Type', 'text/plain');
      res.status(200).send(challenge || '');
      return;
    }
    res.status(403).json({ error: 'forbidden' });
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method not allowed' });
    return;
  }

  const secret = process.env.META_APP_SECRET;
  const sbUrl = process.env.SUPABASE_URL;
  const sbKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const selfIdEnv = process.env.IG_SELF_USER_ID;
  // IG_SELF_USER_ID חובה (הגנת תקציב זמן): בלעדיו תגובות-עצמי נכנסות כאירועים רגילים,
  // וחוק contains שמילת-המפתח שלו מופיעה בתגובה-הפומבית שלנו = לולאה עצמית.
  if (!secret || !sbUrl || !sbKey || !selfIdEnv) {
    res.status(500).json({ error: 'not configured' });
    return;
  }

  let raw;
  try {
    raw = await readRawBody(req);
  } catch (e) {
    res.status(400).json({ error: 'bad body' });
    return;
  }

  if (!validSignature(raw, req.headers['x-hub-signature-256'], secret)) {
    res.status(403).json({ error: 'invalid signature' });
    return;
  }

  let body = {};
  try {
    body = JSON.parse(raw.toString('utf8') || '{}');
  } catch (e) {
    // חתום אבל לא JSON, מאשרים כדי שמטא לא תעשה retry על גוף שלעולם לא ייפרס
    res.status(200).json({ ok: true, skipped: 'not-json' });
    return;
  }

  const sb = { url: sbUrl.replace(/\/$/, ''), key: sbKey };
  const selfId = String(selfIdEnv);
  const events = collectEvents(body, selfId);
  if (events.length === 0) {
    res.status(200).json({ ok: true, events: 0 });
    return;
  }

  // חוקים נטענים eager, לפני כל claim (טעינה מוקדמת): כשל טעינה כאן = 500 עם אפס
  // claims, כך שה-retry של מטא מעבד את האצווה מחדש באמת (ולא מדודפ כ-claimed).
  let rules;
  try {
    rules = await loadActiveRules(sb);
  } catch (e) {
    console.error('ig-webhook rules load failed', e && e.message);
    res.status(500).json({ error: 'rules load failed' });
    return;
  }

  const results = [];
  let dbFailure = false;
  for (const ev of events) {
    try {
      results.push(await processEvent(sb, ev, rules));
    } catch (e) {
      // כשל claim/rules (DB), נסמן 500 כדי שמטא תשלח שוב; ה-claim ידאג שלא יישלח כפול
      console.error('ig-webhook event exception', ev.eventKey, e && e.message);
      dbFailure = true;
      results.push('error');
    }
  }

  // לוג תפעולי בלי PII רגיש ובלי טוקנים
  console.log('ig-webhook processed', JSON.stringify({ events: events.length, results }));

  if (dbFailure) {
    res.status(500).json({ error: 'processing failed' });
    return;
  }
  res.status(200).json({ ok: true, results });
}
