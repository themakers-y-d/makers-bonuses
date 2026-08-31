// רענון הטוקן בענן: טוקן ה-Graph חי 60 יום, וכאן הוא מתחדש לבד בלי שום תלות
// במחשב מקומי דלוק. GitHub Actions (workflows/refresh.yml) קורא לכאן פעם ביום
// עם אותו סוד של הסורק; אם נשארו פחות מ-10 ימים לתפוגה, הטוקן מוחלף בטבלת
// ig_tokens. שאר הזמן הקריאה חוזרת מיד עם ספירת הימים, וגם זו ריצה מוצלחת.
//
// עקרונות: אותו אימות header כמו הסורק (השוואה בזמן קבוע), אפס טוקנים בלוגים
// ובתשובות, וכשל אמיתי חוזר עם ok:false כדי שהג'וב בענן ייצבע אדום ויהיה נראה.
import crypto from 'node:crypto';
import { sbHeaders } from './_ig-store.js';

const REFRESH_THRESHOLD_DAYS = 10;

function timingSafeEq(a, b) {
  const ba = Buffer.from(String(a || ''));
  const bb = Buffer.from(String(b || ''));
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}

export default async function handler(req, res) {
  const secret = process.env.IG_POLL_SECRET;
  const sbUrl = process.env.SUPABASE_URL;
  const sbKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!secret || !sbUrl || !sbKey) {
    // אבחון בטוח: שמות חסרים בלבד, אף פעם לא ערכים
    res.status(500).json({
      error: 'not configured',
      missing: { IG_POLL_SECRET: !secret, SUPABASE_URL: !sbUrl, SUPABASE_SERVICE_ROLE_KEY: !sbKey },
    });
    return;
  }
  if (!timingSafeEq(req.headers['x-poll-secret'], secret)) {
    res.status(403).json({ error: 'forbidden' });
    return;
  }

  const sb = { url: sbUrl.replace(/\/$/, ''), key: sbKey };

  // שורת הטוקן היחידה (id=1)
  let row;
  try {
    const r = await fetch(sb.url + '/rest/v1/ig_tokens?select=access_token,expires_at&id=eq.1', {
      headers: sbHeaders(sb.key),
    });
    const rows = await r.json().catch(() => []);
    row = Array.isArray(rows) && rows[0] ? rows[0] : null;
  } catch (e) {
    res.status(200).json({ ok: false, error: 'token row read failed' });
    return;
  }
  if (!row || !row.access_token) {
    res.status(200).json({ ok: false, error: 'no token row in ig_tokens (id=1)' });
    return;
  }

  const expMs = row.expires_at ? Date.parse(row.expires_at) : NaN;
  const daysLeft = Number.isFinite(expMs) ? Math.floor((expMs - Date.now()) / 86400000) : -1;

  if (daysLeft >= REFRESH_THRESHOLD_DAYS) {
    res.status(200).json({ ok: true, refreshed: false, daysLeft });
    return;
  }

  // רענון מול מטא: הטוקן חייב להיות בן 24 שעות לפחות ולא פג; מחזיר 60 יום חדשים.
  let refreshed;
  try {
    const r = await fetch(
      'https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=' +
        encodeURIComponent(row.access_token)
    );
    refreshed = await r.json().catch(() => ({}));
    if (!r.ok || !refreshed.access_token || !refreshed.expires_in) {
      const err = (refreshed && refreshed.error && refreshed.error.message) || 'refresh call failed';
      res.status(200).json({ ok: false, error: String(err).slice(0, 200), daysLeft });
      return;
    }
  } catch (e) {
    res.status(200).json({ ok: false, error: 'refresh network failure', daysLeft });
    return;
  }

  const newExpires = new Date(Date.now() + Number(refreshed.expires_in) * 1000).toISOString();
  try {
    const r = await fetch(sb.url + '/rest/v1/ig_tokens?id=eq.1', {
      method: 'PATCH',
      headers: sbHeaders(sb.key, { Prefer: 'return=minimal' }),
      body: JSON.stringify({
        access_token: refreshed.access_token,
        expires_at: newExpires,
        refreshed_at: new Date().toISOString(),
      }),
    });
    if (!r.ok) {
      res.status(200).json({ ok: false, error: 'token row write failed ' + r.status });
      return;
    }
  } catch (e) {
    res.status(200).json({ ok: false, error: 'token row write failure' });
    return;
  }

  console.log('ig-refresh done', JSON.stringify({ refreshed: true, newExpires }));
  res.status(200).json({ ok: true, refreshed: true, expiresAt: newExpires });
}
