// עוזר Graph API של אינסטגרם: טוקן + שלוש פעולות שליחה.
// קובץ שמתחיל ב-underscore בתוך api/ לא נחשף כ-endpoint על-ידי Vercel.
//
// כללים: הטוקן עובר ב-Authorization header (לא ב-URL, לא מודלף ללוגים של
// proxies), timeout של 10 שניות על כל קריאה, ואף פונקציה לא זורקת —
// תמיד { ok, error? }.

const GRAPH_BASE = 'https://graph.instagram.com/v23.0';
const TIMEOUT_MS = 10000;

function sbHeaders(key) {
  return { apikey: key, Authorization: 'Bearer ' + key, 'Content-Type': 'application/json' };
}

// הטוקן החי: שורה יחידה (id=1) ב-ig_tokens, מתוחזקת ע"י scripts/refresh-ig-token.sh.
// fallback ל-env IG_ACCESS_TOKEN (הטוקן הראשוני, לפני שהריענון האוטומטי חי).
export async function getToken(sb) {
  try {
    const r = await fetch(sb.url + '/rest/v1/ig_tokens?select=access_token&id=eq.1', {
      headers: sbHeaders(sb.key),
    });
    if (r.ok) {
      const rows = await r.json().catch(() => []);
      const t = Array.isArray(rows) && rows[0] && rows[0].access_token;
      if (t) return t;
    }
  } catch (e) {
    console.error('ig_tokens read failed', e && e.message);
  }
  return process.env.IG_ACCESS_TOKEN || null;
}

async function graphPost(path, token, payload) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(GRAPH_BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) {
      const err = data.error || {};
      // הודעת השגיאה של מטא לא מכילה את הטוקן, בטוח לרשום אותה
      return { ok: false, error: 'graph ' + r.status + ' ' + (err.message || '') + (err.code ? ' (code ' + err.code + (err.error_subcode ? '/' + err.error_subcode : '') + ')' : '') };
    }
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e && e.name === 'AbortError' ? 'graph timeout after ' + TIMEOUT_MS + 'ms' : 'graph exception ' + (e && e.message) };
  } finally {
    clearTimeout(timer);
  }
}

// Private Reply: ‏DM למגיב על תגובה (חלון 7 ימים מרגע התגובה, שליחה אחת לתגובה).
export function sendPrivateReply(token, commentId, text) {
  return graphPost('/me/messages', token, {
    recipient: { comment_id: commentId },
    message: { text },
  });
}

// DM רגיל לפי user id, למשיבי-סטורי (הריפליי שלהם פותח חלון הודעות של 24 שעות).
export function sendDm(token, igUserId, text) {
  return graphPost('/me/messages', token, {
    recipient: { id: igUserId },
    message: { text },
  });
}

// תגובה פומבית מתחת לתגובה של הגולש.
export function sendCommentReply(token, commentId, text) {
  return graphPost('/' + encodeURIComponent(commentId) + '/replies', token, {
    message: text,
  });
}
