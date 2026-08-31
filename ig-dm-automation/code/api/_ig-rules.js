// נרמול טקסט + התאמת חוקי מילות-מפתח.
// קובץ שמתחיל ב-underscore בתוך api/ לא נחשף כ-endpoint על-ידי Vercel.

// נרמול לפני השוואה: המגיב כותב "לינק!!" / "לִינְק" / "לינק 🙏", כולם צריכים
// לפגוש את הכלל "לינק". סדר הפעולות:
// 1) הסרת ניקוד וטעמים (U+0591–U+05C7)
// 2) הסרת אימוג'י (Extended_Pictographic), variation selectors ו-ZWJ
// 3) פיסוק/גרשיים/סימנים → רווח (נשארים רק אותיות, ספרות ורווחים)
// 4) כיווץ רווחים + trim + lowercase (רלוונטי למילות-מפתח באנגלית)
export function normalize(text) {
  return String(text || '')
    .replace(/[֑-ׇ]/g, '')
    .replace(/[\p{Extended_Pictographic}\u{FE00}-\u{FE0F}\u{200D}\u{20E3}]/gu, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

// מוצא את החוק המתאים לטקסט: חוקים ספציפיים ל-media_id קודמים לגלובליים,
// בתוך כל קבוצה לפי priority יורד. match_mode: 'exact' (ברירת מחדל) = הטקסט
// המנורמל כולו שווה למילת-המפתח; 'contains' = מכיל אותה.
export function matchRule(text, rules, mediaId) {
  const t = normalize(text);
  if (!t) return null;
  const active = (Array.isArray(rules) ? rules : []).filter((r) => r && r.active !== false);
  const specific = active.filter((r) => r.media_id && mediaId && String(r.media_id) === String(mediaId));
  const global = active.filter((r) => !r.media_id);
  for (const group of [specific, global]) {
    group.sort((a, b) => (Number(b.priority) || 0) - (Number(a.priority) || 0));
    for (const r of group) {
      const k = normalize(r.keyword);
      if (!k) continue;
      const hit = r.match_mode === 'contains' ? t.includes(k) : t === k;
      if (hit) return r;
    }
  }
  return null;
}
