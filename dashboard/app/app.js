/* ============================================================
   החיבור לסופאבייס: התחברות, שליפה, וציור.

   שלושה כללים שמסבירים למה זה נראה ככה:
   אחד, הדאשבורד קורא ולא כותב. מי שכותב הוא הצוות, דרך המפתח
   הסודי שיושב בקובץ במחשב שלו ולא כאן.
   שתיים, אין כאן שום סינון לפי בעלים. הוא נעשה במסד הנתונים
   עצמו, וזה מה שמחזיק גם אם מישהו יפתח את הקוד של הדף.
   שלוש, הקוד מדבר עם הטבלה entries בלבד.
   ============================================================ */

var CFG = window.DASHBOARD_CONFIG || {};
var sb = null;

function el(id){ return document.getElementById(id); }

/* הבעלים לא אמור לקרוא הודעות מערכת באנגלית. וכל מסך שגיאה
   חייב דרך החוצה, אחרת הוא קצה מסלול ורק רענון מוציא ממנו. */
function humanError(e){
  var m = String(e && e.message || e || '').toLowerCase();
  if (m.indexOf('jwt') !== -1 || m.indexOf('expired') !== -1)
    return 'הכניסה שלכם פגה. היכנסו שוב.';
  if (m.indexOf('failed to fetch') !== -1 || m.indexOf('network') !== -1)
    return 'אין חיבור לאינטרנט כרגע, או שהחשבון ישן. אם לא נכנסתם שבוע, ייתכן שהוא הושהה וצריך להפעיל אותו מחדש בלוח הבקרה של סופאבייס.';
  if (m.indexOf('permission') !== -1 || m.indexOf('rls') !== -1)
    return 'אין הרשאה לקרוא את הנתונים. זו הגדרה בחשבון, והצוות שלכם יידע לתקן.';
  return 'משהו השתבש בקריאת הנתונים. נסו שוב בעוד רגע.';
}
function fail(msg, e){
  if (e) console.error(e);
  hide('loading'); hide('app-shell');
  el('errText').textContent = msg;
  show('err');
}
function show(id){ el(id).hidden = false; }
function hide(id){ el(id).hidden = true; }

function configMissing(){
  return !CFG.supabaseUrl || CFG.supabaseUrl.indexOf('PROJECT_REF') !== -1 ||
         !CFG.anonKey || CFG.anonKey.indexOf('ANON_KEY') !== -1;
}

async function loadRows(){
  // בלי סינון לפי בעלים בקוד: ההרשאות בטבלה מחזירות רק את השורות שלו.
  var res = await sb.from('entries')
    .select('date,type,source,name,amount,status,note')
    .order('date', { ascending: false })
    .limit(5000);
  if (res.error) throw res.error;
  return (res.data || []).map(function (r) {
    return {
      date: r.date, type: r.type, source: r.source, name: r.name,
      amount: Number(r.amount) || 0, status: r.status, note: r.note
    };
  });
}

async function draw(){
  hide('auth'); hide('loading'); hide('err');
  try {
    var rows = await loadRows();
    setData(rows, { name: CFG.businessName, currency: CFG.currency });
    show('app-shell');
    // עמוד נוסף מגדיר renderPage משלו. עמוד הבית נופל ל-renderHome.
    (window.renderPage || renderHome)();
  } catch (e) {
    fail(humanError(e), e);
  }
}

async function boot(){
  try {
    // כשל בטעינת הספרייה מהרשת השאיר בעבר את הדף תקוע לנצח על
    // מסך הטעינה, בלי שגיאה ובלי מוצא. זו הבדיקה שמונעת את זה.
    if (!window.supabase || !window.supabase.createClient){
      fail('לא הצלחנו לטעון את הרכיב שמדבר עם החשבון. בדקו חיבור לאינטרנט ורעננו את הדף.');
      return;
    }
    if (configMissing()){
      fail('הדף עוד לא חובר לחשבון. צריך למלא את שני הערכים בקובץ config.js.');
      return;
    }
    sb = window.supabase.createClient(CFG.supabaseUrl, CFG.anonKey);

    var sess = await sb.auth.getSession();
    if (sess.data && sess.data.session) { await draw(); }
    else { hide('loading'); hide('err'); show('auth'); }

    sb.auth.onAuthStateChange(function (event) {
      if (event === 'SIGNED_IN') draw();
      if (event === 'SIGNED_OUT'){
        // מנקים את המסך ואת הזיכרון, אחרת הנתונים נשארים ב-DOM
        // אחרי יציאה, וזה מספיק על מחשב משותף.
        setData([], {});
        var app = el('app'); if (app) app.innerHTML = '';
        hide('app-shell'); hide('err'); show('auth');
      }
    });
  } catch (e) {
    fail(humanError(e), e);
  }
}

document.addEventListener('DOMContentLoaded', function () {
  el('authForm').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var email = el('authEmail').value.trim();
    if (!email) return;
    var btn = el('authBtn'), lbl = btn.querySelector('.btxt');
    btn.disabled = true; lbl.textContent = 'שולח';
    // shouldCreateUser: false קריטי. בלעדיו כל מי שמחזיק את הכתובת
    // יכול ליצור משתמשים בפרויקט ולשרוף את מכסת המיילים, שהיא שניים
    // בשעה בתוכנית החינמית, וכך לנעול את הבעלים מחוץ לדאשבורד שלו.
    var r = await sb.auth.signInWithOtp({
      email: email,
      options: { shouldCreateUser: false, emailRedirectTo: window.location.href.split('#')[0] }
    });
    btn.disabled = false; lbl.textContent = 'שליחת קישור';
    var em = String(r.error && r.error.message || '').toLowerCase();
    el('authMsg').textContent = !r.error
      ? 'שלחנו לכם קישור למייל. פותחים אותו וחוזרים לכאן.'
      : em.indexOf('rate') !== -1
        ? 'נשלחו יותר מדי קישורים בזמן קצר. המתינו שעה ונסו שוב.'
        : em.indexOf('signups not allowed') !== -1 || em.indexOf('not found') !== -1
          ? 'המייל הזה לא מוכר בדאשבורד הזה. ודאו שזה המייל שאיתו הוקם החשבון.'
          : 'לא הצלחנו לשלוח כרגע. נסו שוב בעוד רגע.';
    el('authMsg').hidden = false;
  });

  var retry = el('retry');
  if (retry) retry.addEventListener('click', function(){ hide('err'); show('loading'); boot(); });

  var out = el('signOut');
  if (out) out.addEventListener('click', function(){ sb.auth.signOut(); });

  boot();
});
