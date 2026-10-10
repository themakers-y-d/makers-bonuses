/* ============================================================
   המנוע המשותף של הדאשבורד.

   כאן יושבים החישובים והרכיבים, וכל עמוד משתמש בהם.
   הנתונים עצמם לא כאן, הם בטבלה entries בסופאבייס.

   להוסיף עמוד: יוצרים קובץ HTML ליד index.html,
   ומוסיפים לו שורה אחת ברשימה שמיד למטה. זה הכל.
   ============================================================ */

// העמודים של הבעלים. מגיע עמוד אחד בלבד, וזה שלד ולא ברירת מחדל:
// העמודים האמיתיים נקבעים בשלב 2 של INSTALL-makers ונבנים בשלב 12.
// הניווט מופיע מעצמו ברגע שיש כאן יותר משורה אחת.
var PAGES = [
  { file: 'index.html', title: 'סקירה' }
];

/* ---------- הנתונים ----------
   מגיעים מסופאבייס ומוזרקים לכאן על ידי app.js אחרי ההתחברות.
   המנוע עצמו לא יודע מאיפה הם באו, ולכן אפשר להחליף מקור בלי
   לגעת בחישובים. */
var DATA = { business: {}, rows: [] };
var ROWS = [];
var CUR  = '₪';

var BAD_DATES = 0, FUTURE_ROWS = 0;

function setData(rows, business){
  DATA = { business: business || {}, rows: rows || [] };
  CUR  = (business && business.currency) || '₪';
  BAD_DATES = 0; FUTURE_ROWS = 0;
  var t = today();
  ROWS = (rows || []).filter(function (r) {
    if (!r) return false;
    var d = parseDate(r.date);
    if (!d) { BAD_DATES++; return false; }          // שורה בלי תאריך תקין מרעילה כל חישוב
    if (d > t) { FUTURE_ROWS++; return false; }     // טעות הקלדה בשנה מחקה מכירה בשקט
    return true;
  });
}

var MONTHS_SHORT = ['ינו','פבר','מרץ','אפר','מאי','יונ','יול','אוג','ספט','אוק','נוב','דצמ'];

/* ---------- עזרים ---------- */

/* כל טקסט שמגיע מהנתונים עובר כאן לפני שהוא נכנס ל-HTML.
   בלי זה, שם לקוח עם תו מיוחד או הערה עם סוגר משולש מריצים
   קוד בדף שמחזיק סשן חי, או נבלעים בשקט ומזייפים את הפילוח. */
function esc(v){
  return String(v == null ? '' : v).replace(/[&<>"']/g, function(c){
    return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c];
  });
}
function parseDate(s){
  var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(s || ''));
  if (!m) return null;
  var d = new Date(+m[1], +m[2] - 1, +m[3]);
  return isNaN(d.getTime()) ? null : d;
}
function money(n){ return CUR + Math.round(n).toLocaleString('en-US'); }
function dayjs(d){ return d.getDate() + '.' + (d.getMonth() + 1); }

function today(){ var d = new Date(); d.setHours(0,0,0,0); return d; }
function daysAgo(n){ var d = today(); d.setDate(d.getDate()-n); return d; }
function inRange(r, from, to){ var d = parseDate(r.date); return d && d >= from && d <= to; }

function sum(list){ return list.reduce(function(a,r){ return a + (+r.amount || 0); }, 0); }
function sales(list){ return list.filter(function(r){ return r.type === 'sale'; }); }
function leads(list){ return list.filter(function(r){ return r.type === 'lead'; }); }

/* חלון מתגלגל של 30 יום, ולא חודש קלנדרי: כך המספר אמיתי בכל יום
   שפותחים את הדף, ולא רק באמצע החודש. */
function windowRows(days, offset){
  offset = offset || 0;
  var to = daysAgo(offset), from = daysAgo(offset + days);
  // גבול פתוח מלמטה וסגור מלמעלה, כדי ששני חלונות רצופים לא יספרו את אותו יום פעמיים
  return ROWS.filter(function(r){ var d = parseDate(r.date); return d > from && d <= to; });
}

function delta(now, prev, isPercent){
  if (!prev) return now > 0
    ? { cls:'up', text:'הראשון בתקופה הזאת' }
    : { cls:'flat', text:'אין מול מה להשוות' };
  // מדד שהוא בעצמו אחוז זז בנקודות ולא באחוזים. מעבר מ-43 ל-40 הוא שלוש
  // נקודות, ולא "ירידה של 7%", וזה מספר שנשמע מדויק ואינו קיים.
  if (isPercent){
    var pts = Math.round(now - prev);
    if (pts === 0) return { cls:'flat', text:'כמו בתקופה הקודמת' };
    // בלי תחילית, כי "ב-3" דורש מקף והמקף אסור בכל טקסט שפונה לקהל
    return { cls: pts > 0 ? 'up' : 'down',
             text: (pts > 0 ? 'עלה ' : 'ירד ') + Math.abs(pts) +
                   (Math.abs(pts) === 1 ? ' נקודה' : ' נקודות') + ' מול 30 הימים הקודמים' };
  }
  var pct = Math.round((now - prev) / prev * 100);
  if (pct === 0) return { cls:'flat', text:'כמו בתקופה הקודמת' };
  return { cls: pct > 0 ? 'up' : 'down',
           text: (pct > 0 ? 'עלייה של ' : 'ירידה של ') + Math.abs(pct) + '% מול 30 הימים הקודמים' };
}

/* ---------- ותק בימים, בעברית נכונה ----------
   floor ולא round: פנייה שנכנסה היום נשארת "היום" גם אחרי הצהריים. */
function daysSince(dateStr){
  var d = parseDate(dateStr);
  if (!d) return null;
  return Math.floor((today() - d) / 86400000);
}
function agoLabel(dateStr){
  var n = daysSince(dateStr);
  if (n === null) return 'תאריך לא תקין';
  if (n <= 0) return 'היום';
  if (n === 1) return 'אתמול';
  if (n === 2) return 'לפני יומיים';
  return 'לפני ' + n + ' ימים';
}

/* ---------- סטטוס ----------
   הערך נכתב בידי אדם או בידי סוכן, פעם באנגלית ופעם בעברית. בלי
   נירמול, "חדש" במקום "new" מעביר פנייה בשקט לעמודה הלא נכונה. */
/* ארבעה ערכים בלבד, וזה גם מה שאילוץ ה-CHECK במסד מאשר.
   ערך לא מוכר חוזר כלא ידוע ולא מתחפש לאחד מהם, אחרת פנייה
   עוברת בשקט לעמודה הלא נכונה וזה נראה כמו נתון ולא כמו תקלה. */
var STATUS = { 'חדש':'חדש', 'בשיחה':'בשיחה', 'נסגר':'נסגר', 'לא רלוונטי':'לא רלוונטי' };
function status(r){
  return STATUS[String(r && r.status || '').trim()] || 'לא ידוע';
}

/* ---------- רכיבים ----------
   כל אחד מחזיר HTML, כדי שעמוד חדש יוכל להרכיב מהם מה שהוא צריך. */

function kpi(label, value, d, why){
  return '<div class="kpi">' +
    '<span class="label">' + esc(label) + '</span>' +
    '<span class="value num">' + esc(value) + '</span>' +
    (d ? '<span class="delta ' + d.cls + '">' + esc(d.text) + '</span>' : '') +
    (why ? '<span class="why">' + esc(why) + '</span>' : '') +
    '</div>';
}

function monthlyBars(){
  var buckets = [], i, d, t = today();
  for (i = 5; i >= 0; i--){
    d = new Date(t.getFullYear(), t.getMonth() - i, 1);
    buckets.push({ y:d.getFullYear(), m:d.getMonth(), total:0 });
  }
  sales(ROWS).forEach(function(r){
    var dt = parseDate(r.date);
    buckets.forEach(function(b){
      if (b.y === dt.getFullYear() && b.m === dt.getMonth()) b.total += (+r.amount || 0);
    });
  });
  var max = Math.max.apply(null, buckets.map(function(b){ return Math.max(0, b.total); }).concat([1]));
  // התיקו מסומן פעם אחת בלבד, אחרת שתי עמודות נקראות כ"החודש החזק"
  var bestTotal = Math.max.apply(null, buckets.map(function(b){ return b.total; }));
  var bestIdx = -1;
  buckets.forEach(function(b, i){ if (b.total === bestTotal && b.total > 0) bestIdx = i; });
  return '<div class="bars">' + buckets.map(function(b, i){
    var h = Math.max(3, Math.round(Math.max(0, b.total) / max * 130));
    var top = i === bestIdx;
    // חודש בלי הכנסה: 3 פיקסל עם מסגרת דיו נקראים כקו כהה כבד,
    // כאילו קרה שם משהו. חודש ריק מקבל קו שקט ולא סימן.
    return '<div class="bar' + (top ? ' top' : '') + (b.total ? '' : ' zero') + '">' +
      '<span class="amt num">' + (b.total ? money(b.total) : '') + '</span>' +
      '<span class="fill" style="block-size:' + h + 'px"></span>' +
      '<span class="mon">' + MONTHS_SHORT[b.m] + '</span>' +
    '</div>';
  }).join('') + '</div>';
}

function sourceBreakdown(rows){
  var map = {};
  rows.forEach(function(r){
    var s = r.source || 'לא ידוע';
    if (!map[s]) map[s] = { leads:0, revenue:0 };
    if (r.type === 'lead') map[s].leads++;
    if (r.type === 'sale') map[s].revenue += (+r.amount || 0);
  });
  var list = Object.keys(map).map(function(k){
    return { name:k, leads:map[k].leads, revenue:map[k].revenue };
  }).sort(function(a,b){ return (b.revenue - a.revenue) || (b.leads - a.leads); });
  if (!list.length) return '';
  var anyRevenue = list.some(function(s){ return s.revenue > 0; });
  var max = Math.max.apply(null, list.map(function(s){ return anyRevenue ? s.revenue : s.leads; }).concat([1]));
  return '<div class="sources">' + list.map(function(s){
    var w = Math.max(4, Math.round((anyRevenue ? s.revenue : s.leads) / max * 100));
    return '<div class="src">' +
      '<span class="name">' + esc(s.name) + '</span>' +
      '<span class="track"><span class="fill" style="inline-size:' + w + '%"></span></span>' +
      '<span class="n num">' + money(s.revenue) + ' · ' + s.leads + (s.leads === 1 ? ' פנייה' : ' פניות') + '</span>' +
    '</div>';
  }).join('') + '</div>';
}

function recentRows(n){
  var list = ROWS.slice().sort(function(a,b){ return parseDate(b.date) - parseDate(a.date); }).slice(0, n || 10);
  return '<div class="rows">' + list.map(function(r){
    var isSale = r.type === 'sale';
    return '<div class="row">' +
      '<span class="date num">' + dayjs(parseDate(r.date)) + '</span>' +
      '<span class="kind ' + (isSale ? 'sale' : '') + '">' + (isSale ? 'מכירה' : 'פנייה') + '</span>' +
      '<span class="who">' + esc(r.name || '') + (r.source ? ' · ' + esc(r.source) : '') + '</span>' +
      '<span class="amt num">' + (isSale && +r.amount ? money(+r.amount) : '') + '</span>' +
    '</div>';
  }).join('') + '</div>';
}

/* ---------- שלד העמוד ---------- */
function pageHead(current){
  var now = new Date();
  var name = (DATA.business && DATA.business.name) ? DATA.business.name : 'הדאשבורד שלי';
  var el = document.getElementById('bizName');
  if (el) el.textContent = name;
  // התווית הזו היא הדבר היחיד שמספר על טריות הנתונים, ולכן היא נגזרת
  // מהשורה החדשה ביותר ולא מהשעון. מסך שאומר "עודכן היום" מעל נתונים
  // בני שישה שבועות גרוע מהיעדר תווית.
  var up = document.getElementById('updated');
  if (up){
    if (!ROWS.length){ up.textContent = 'עוד אין נתונים'; }
    else {
      var newest = ROWS.reduce(function(a,r){ return parseDate(r.date) > parseDate(a.date) ? r : a; });
      var age = daysSince(newest.date), d = parseDate(newest.date);
      var stamp = '<span class="num">' + d.getDate() + '.' + (d.getMonth()+1) + '.' + d.getFullYear() + '</span>';
      if (age > 14){
        up.innerHTML = 'הנתונים האחרונים מ' + stamp + ', כבר ' + age + ' ימים בלי עדכון';
        up.className = 'updated stale';
      } else {
        up.innerHTML = 'הנתונים האחרונים מ' + stamp;
        up.className = 'updated';
      }
    }
  }
  if (up && (BAD_DATES || FUTURE_ROWS)){
    var warn = [];
    if (BAD_DATES)    warn.push(BAD_DATES + ' שורות עם תאריך לא תקין');
    if (FUTURE_ROWS)  warn.push(FUTURE_ROWS + ' שורות עם תאריך עתידי');
    up.innerHTML += ' <span class="stale">· ' + warn.join(' ו') + '</span>';
  }

  var nav = document.getElementById('nav');
  if (nav && PAGES.length > 1){
    nav.innerHTML = PAGES.map(function(p){
      return '<a href="' + p.file + '"' + (p.file === current ? ' class="on"' : '') + '>' + p.title + '</a>';
    }).join('');
  }
}

function emptyState(){
  return '<div class="empty">' +
    '<p>עוד אין כאן נתונים, וזה בסדר גמור.</p>' +
    '<p>בקשו מהצוות להזין את מה שכבר קרה אצלכם החודש. ברגע שתהיה שורה אחת, הדף הזה יתמלא לבד.</p>' +
    '</div>';
}

/* ---------- עמוד הבית ---------- */
function currentFile(){
  var f = (location.pathname.split('/').pop() || 'index.html');
  return f || 'index.html';
}

function renderHome(){
  pageHead(currentFile());
  var app = document.getElementById('app');
  if (!ROWS.length){ app.innerHTML = emptyState(); return; }

  var win  = windowRows(30);
  var prev = windowRows(30, 30);

  // בלי השורה הזו, חודש של שקט מוצג כארבעה כרטיסים של ירידה במאה אחוז,
  // כלומר המסך אומר "העסק שלך מת" במקום "אין לי נתונים חדשים".
  var quiet = win.length === 0 && prev.length > 0;
  var srcHtml = sourceBreakdown(win);

  var revenue = sum(sales(win)),   revenuePrev = sum(sales(prev));
  var nLeads  = leads(win).length, nLeadsPrev  = leads(prev).length;
  var nSales  = sales(win).length, nSalesPrev  = sales(prev).length;
  // המכירה של החודש הזה שייכת לפנייה של החודש שעבר, ולכן היחס הזה
  // יכול לעבור 100. חוסמים, וכשאין פניות בכלל לא מציגים כרטיס.
  var close     = nLeads ? Math.min(100, Math.round(nSales / nLeads * 100)) : null;
  var closePrev = nLeadsPrev ? Math.min(100, Math.round(nSalesPrev / nLeadsPrev * 100)) : null;
  var avg     = nSales ? revenue / nSales : 0;
  var avgPrev = nSalesPrev ? revenuePrev / nSalesPrev : 0;

  app.innerHTML =
    (quiet ? '<div class="empty" style="margin-block-end:var(--sp-32)">' +
      '<p>לא נכנסה שום שורה בשלושים הימים האחרונים.</p>' +
      '<p>המספרים שלמטה מציגים אפס כי אין מה להציג, ולא כי משהו קרה לעסק. אמרו לצוות מה קרה מאז והמסך יחזור לחיים.</p>' +
      '</div>' : '') +
    '<section><div class="kpis">' +
      kpi('הכנסה', money(revenue), quiet ? null : delta(revenue, revenuePrev),
          'אם המספר הזה יורד חודשיים ברצף, זו לא תקופה, זו מגמה.') +
      kpi('פניות', nLeads, quiet ? null : delta(nLeads, nLeadsPrev),
          'פניות שיורדות מסבירות הכנסה שתרד בעוד חודש.') +
      (close === null ? '' :
      kpi('אחוז סגירה', close + '%', (quiet || closePrev === null) ? null : delta(close, closePrev, true),
          'נמוך עם הרבה פניות: הבעיה בשיחה. גבוה עם מעט פניות: הבעיה בחשיפה.')) +
      kpi('עסקה ממוצעת', money(avg), quiet ? null : delta(avg, avgPrev),
          'הדרך המהירה ביותר להכנסה גדולה יותר בלי יותר עבודה.') +
    '</div></section>' +

    '<section><h2>הכנסה לפי חודש</h2>' +
      '<p class="hint">שישה חודשים אחורה. העמודה הכהה היא החודש החזק ביותר.</p>' +
      '<div class="panel">' + monthlyBars() + '</div></section>' +

    (srcHtml ?
    '<section><h2>מאיפה הם הגיעו</h2>' +
      '<p class="hint">שלושים הימים האחרונים. הערוץ שמייצר כסף, לא הערוץ שמייצר רעש.</p>' +
      '<div class="panel">' + srcHtml + '</div></section>' : '') +

    '<section><h2>מה קרה לאחרונה</h2>' +
      '<div class="panel">' + recentRows(10) + '</div></section>';
}
