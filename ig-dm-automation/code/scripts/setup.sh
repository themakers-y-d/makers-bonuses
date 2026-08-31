#!/usr/bin/env bash
# ============================================================================
# setup.sh: מתקין אינטראקטיבי לערכת האוטומציה של אינסטגרם.
#
# לוקח אדם ממצב "יש לי את תיקיית הערכה" עד "האוטומציה פרוסה ורצה", ועושה
# לבד כל דבר שאפשר לעשות לבד. מה שנשאר לאדם: הדבקת הסכמה בסופאבייס,
# והחיווט בדשבורד של מטא, שתי פעולות שאין להן API ציבורי.
#
# הסקריפט בטוח להרצה חוזרת: סודות שנוצרו בריצה קודמת נטענים מחדש ולא
# מוחלפים, טבלאות קיימות מדולגות, ומשתני סביבה נמחקים לפני שנכתבים.
#
# הרצה:  bash scripts/setup.sh   (מכל מקום, הסקריפט מוצא את עצמו)
# ============================================================================
set -euEo pipefail

# ---------------------------------------------------------------------------
# מצב גלובלי: השלב הנוכחי מוצג בהודעת השגיאה, וכך ברור מה נשבר בלי להדפיס ערכים
# ---------------------------------------------------------------------------
STEP="אתחול"
CLEAN_EXIT=0
TMPFILES=()

cleanup() {
  local f
  for f in "${TMPFILES[@]:-}"; do [ -n "$f" ] && rm -f "$f" 2>/dev/null || true; done
}
trap cleanup EXIT

on_err() {
  local code=$? line="${1:-?}"
  [ "$CLEAN_EXIT" = "1" ] && exit "$code"
  echo ""
  echo "============================================================"
  echo "ההתקנה נעצרה."
  echo "השלב שנכשל: $STEP"
  echo "שורה בסקריפט: $line, קוד יציאה: $code"
  echo ""
  if [ -f "${CODE_DIR:-.}/scripts/doctor.sh" ]; then
    echo "לאבחון הרץ: bash scripts/doctor.sh"
  else
    echo "לאבחון פתח את 03-gotchas.md בשורש הערכה, רוב הכשלים כבר מתועדים שם"
    echo "לפי סימפטום, כולל מה לעשות בכל אחד."
  fi
  echo ""
  echo "אפשר להריץ את הסקריפט שוב אחרי התיקון, הוא בטוח להרצה חוזרת."
  echo "============================================================"
  exit "$code"
}
trap 'on_err $LINENO' ERR

mktmp() {
  local f
  f="$(mktemp "${TMPDIR:-/tmp}/ig-setup.XXXXXX")"
  chmod 600 "$f"
  TMPFILES+=("$f")
  printf '%s' "$f"
}

say()  { printf '%s\n' "$1"; }
head1() { printf '\n%s\n%s\n' "$1" "------------------------------------------------------------"; }
ok()   { printf 'תקין: %s\n' "$1"; }
bad()  { printf 'נכשל: %s\n' "$1"; }
note() { printf 'שים לב: %s\n' "$1"; }

die() {
  CLEAN_EXIT=1
  echo ""
  echo "עצירה: $1"
  [ -n "${2:-}" ] && echo "$2"
  echo ""
  exit 1
}

# ---------------------------------------------------------------------------
# 0) מציאת עצמנו: הסקריפט חייב לעבוד גם כשמריצים אותו מתיקייה אחרת
# ---------------------------------------------------------------------------
STEP="איתור תיקיית הערכה"
SCRIPT_PATH="${BASH_SOURCE[0]}"
while [ -L "$SCRIPT_PATH" ]; do
  link="$(readlink "$SCRIPT_PATH")"
  case "$link" in
    /*) SCRIPT_PATH="$link" ;;
    *)  SCRIPT_PATH="$(dirname "$SCRIPT_PATH")/$link" ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
CODE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CODE_DIR"

MIGRATION_REL="supabase/migrations/001_ig_automation.sql"
for required in "api/ig-poll.js" "api/ig-webhook.js" "$MIGRATION_REL" "vercel.json"; do
  [ -f "$CODE_DIR/$required" ] || die \
    "התיקייה $CODE_DIR לא נראית כמו תיקיית code של הערכה." \
    "חסר הקובץ $required. העתק את הסקריפט לתוך code/scripts/ והרץ שוב."
done

[ -r /dev/tty ] || die "הסקריפט אינטראקטיבי וצריך טרמינל אמיתי." "הרץ אותו ישירות בטרמינל, לא דרך צינור."

# ---------------------------------------------------------------------------
# 1) בדיקות מקדימות: כלים וגרסאות
# ---------------------------------------------------------------------------
STEP="בדיקות מקדימות"
head1 "בדיקות מקדימות"

for tool in node git curl openssl; do
  command -v "$tool" >/dev/null 2>&1 || die "לא נמצא הכלי $tool." "התקן אותו והרץ שוב."
  ok "$tool נמצא"
done

if ! command -v vercel >/dev/null 2>&1; then
  CLEAN_EXIT=1
  echo ""
  echo "עצירה: לא נמצא Vercel CLI, ובלעדיו אי אפשר לפרוס."
  echo ""
  echo "התקן אותו עם הפקודה הבאה, ואז הרץ את הסקריפט שוב:"
  echo ""
  echo "    npm i -g vercel"
  echo ""
  exit 1
fi
ok "vercel נמצא"

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "$NODE_MAJOR" -lt 18 ] 2>/dev/null; then
  die "גרסת Node היא $NODE_MAJOR, והמערכת דורשת 18 ומעלה." \
      "הסיבה: הקוד משתמש ב-fetch המובנה, שקיים רק מגרסה 18. עדכן את Node והרץ שוב."
fi
ok "Node בגרסה $NODE_MAJOR"

if ! command -v jq >/dev/null 2>&1; then
  note "jq לא מותקן. ההתקנה עצמה לא צריכה אותו, אבל scripts/refresh-ig-token.sh"
  note "וגם scripts/ig-poll-ping.sh משתמשים בו בהמשך. שווה להתקין: brew install jq"
fi

# ---------------------------------------------------------------------------
# 2) הסבר קצר ואפשרות לצאת
# ---------------------------------------------------------------------------
STEP="אישור התחלה"
head1 "מה עומד לקרות"
say "הסקריפט יאמת את הטוקן שלך מול אינסטגרם, יריץ את הסכמה בסופאבייס, יזין"
say "שבעה משתני סביבה לוורסל, יפרוס לפרודקשן ויבדוק שהכל חי מקצה לקצה."
say "צריך ביד שלושה דברים: פרויקט Supabase פתוח, חשבון Vercel מחובר,"
say "והטוקן של אינסטגרם יחד עם מזהה המשתמש, שניהם מהדשבורד של מטא."
echo ""
printf 'להמשיך? הקש y להמשך, כל דבר אחר יוצא: '
IFS= read -r go < /dev/tty || go=""
case "$go" in
  y|Y|yes|YES|כן) : ;;
  *) die "יצאת לבקשתך, שום דבר לא שונה." ;;
esac

# ---------------------------------------------------------------------------
# 3) סודות מריצה קודמת: לא מייצרים חדשים ולא שוברים חיווט שכבר עובד
# ---------------------------------------------------------------------------
STEP="טעינת סודות מריצה קודמת"
ENV_DIR="$HOME/.config/ig-automation"
ENV_FILE="$ENV_DIR/ig.env"

read_env_var() {
  local file="$1" key="$2" val=""
  [ -f "$file" ] || return 0
  val="$(sed -n "s/^[[:space:]]*${key}=//p" "$file" | tail -n 1)"
  val="${val%\"}"; val="${val#\"}"
  val="${val%\'}"; val="${val#\'}"
  printf '%s' "$val"
}

PREV_POLL_SECRET="$(read_env_var "$ENV_FILE" IG_POLL_SECRET)"
PREV_VERIFY_TOKEN="$(read_env_var "$ENV_FILE" IG_VERIFY_TOKEN)"

# ---------------------------------------------------------------------------
# 4) איסוף הקלטים, כל אחד עם אימות וניסיון חוזר
# ---------------------------------------------------------------------------
STEP="איסוף הקלטים"

ANSWER=""

# ask <שם משתנה לתצוגה> <טקסט שאלה> <שם פונקציית אימות> <רמז לכשל> <secret|plain>
ask() {
  local label="$1" prompt="$2" validator="$3" hint="$4" mode="${5:-plain}" v=""
  while true; do
    printf '\n%s\n' "$prompt"
    if [ "$mode" = "secret" ]; then
      printf '%s (הקלדה מוסתרת): ' "$label"
      IFS= read -rs v < /dev/tty || v=""
      printf '\n'
    else
      printf '%s: ' "$label"
      IFS= read -r v < /dev/tty || v=""
    fi
    # כל הערכים כאן הם מחרוזות בלי רווחים, ניקוי רווחים מונע הדבקה עם רווח נגרר
    v="$(printf '%s' "$v" | tr -d '[:space:]')"
    if [ -z "$v" ]; then
      bad "לא הוזן כלום."
      continue
    fi
    if "$validator" "$v"; then
      ANSWER="$v"
      return 0
    fi
    bad "$hint"
  done
}

v_supabase_url() {
  local u="${1%/}"
  [[ "$u" =~ ^https://[A-Za-z0-9-]+\.supabase\.co$ ]]
}

# המלכודת מספר 6 בערכה: מפתח שהודבק ריק או חלקי נכתב בלי שגיאה, והכשל מתגלה
# רק בזמן ריצה. לכן בודקים צורה ואורך, ואחר כך גם קוראים איתו מול הסופאבייס.
v_service_key() {
  local k="$1" n="${#1}"
  case "$k" in
    # sb_secret_ בלבד. המפתח הציבורי הוא sb_publishable_ ואסור לקבל אותו כאן:
    # הוא נראה תקין, עובר את בדיקת השורש, ואז נכשל על הטבלאות בצורה שנראית
    # כמו הגירה שלא רצה. שגיאה שמאבחנת את עצמה לא נכון גרועה משגיאה גלויה.
    sb_secret_*) [ "$n" -ge 40 ] ;;
    sb_publishable_*) return 1 ;;
    eyJ*) [ "$n" -ge 100 ] ;;
    *)    return 1 ;;
  esac
}

v_app_secret()  { [[ "$1" =~ ^[0-9a-fA-F]{20,}$ ]]; }
v_ig_user_id()  { [[ "$1" =~ ^[0-9]{10,}$ ]]; }
v_ig_token()    { local t="$1"; [[ "$t" == IG* ]] && [ "${#t}" -ge 50 ]; }

head1 "קלט 1 מתוך 5: כתובת פרויקט הסופאבייס"
ask "SUPABASE_URL" \
  "הכתובת נמצאת ב-Supabase, Project Settings, Data API. הצורה: https://xxxx.supabase.co" \
  v_supabase_url \
  "הכתובת חייבת להיראות כך בדיוק: https://<ref>.supabase.co, בלי נתיב אחריה." \
  plain
SUPABASE_URL="${ANSWER%/}"
PROJECT_REF="${SUPABASE_URL#https://}"
PROJECT_REF="${PROJECT_REF%%.supabase.co}"
ok "פרויקט הסופאבייס: $PROJECT_REF"

head1 "קלט 2 מתוך 5: מפתח service_role של הסופאבייס"
say "זה הקלט הרגיש והשביר ביותר בהתקנה כולה. המפתח מאות תווים, ומי שמדביק"
say "חלק ממנו או מדביק ריק לא מקבל שגיאה עכשיו אלא רק בזמן ריצה, בתור שקט מוחלט."
say "איפה הוא: Supabase, Project Settings, API keys, המפתח הסודי, לא ה-anon."
ask "SUPABASE_SERVICE_ROLE_KEY" \
  "הדבק את המפתח המלא. הוא לא יוצג על המסך." \
  v_service_key \
  "המפתח חייב להתחיל ב-sb_secret_ או ב-eyJ. אם הודבק מפתח שמתחיל ב-sb_publishable_ זה המפתח הציבורי, והוא לא יעבוד. קח את הסודי." \
  secret
SUPABASE_SERVICE_ROLE_KEY="$ANSWER"
ok "המפתח התקבל, אורך ${#SUPABASE_SERVICE_ROLE_KEY} תווים"

head1 "קלט 3 מתוך 5: הסוד של אפליקציית מטא"
ask "META_APP_SECRET" \
  "איפה: developers.facebook.com, האפליקציה שלך, App settings, Basic, App secret, לחיצה על Show." \
  v_app_secret \
  "הערך אמור להיות מחרוזת הקסדצימלית באורך 20 תווים ומעלה." \
  secret
META_APP_SECRET="$ANSWER"
ok "סוד האפליקציה התקבל"

head1 "קלט 4 מתוך 5: מזהה המשתמש של חשבון האינסטגרם"
say "זה מה שמונע מהמערכת לענות לתגובות של עצמה ולהיכנס ללולאה אינסופית."
ask "IG_SELF_USER_ID" \
  "איפה: בשורת החשבון בסעיף Generate access tokens, המספר שמתחיל ב-17841." \
  v_ig_user_id \
  "המזהה הוא ספרות בלבד, לפחות עשר." \
  plain
IG_SELF_USER_ID="$ANSWER"
case "$IG_SELF_USER_ID" in
  17841*) ok "מזהה החשבון: $IG_SELF_USER_ID" ;;
  *) note "המזהה לא מתחיל ב-17841, וזו הצורה הרגילה. אם זו טעות, עצור עכשיו ובדוק." ;;
esac

head1 "קלט 5 מתוך 5: טוקן הגישה של אינסטגרם"
ask "IG_ACCESS_TOKEN" \
  "הטוקן שהעתקת מהדיאלוג של Generate token. הוא מוצג פעם אחת בלבד." \
  v_ig_token \
  "טוקן תקין מתחיל ב-IG ואורכו לפחות 50 תווים. הודעת שגיאה 190 בהמשך משמעה העתקה חלקית." \
  secret
IG_ACCESS_TOKEN="$ANSWER"
ok "הטוקן התקבל, אורך ${#IG_ACCESS_TOKEN} תווים"

# --- שני הסודות שהמערכת מייצרת בעצמה --------------------------------------
# שים לב לתנאי: מספיק שאחד מהשניים חסר כדי לייצר את שניהם מחדש. קובץ חלקי
# מריצה שנקטעה לא יגרור שימוש בחצי סוד ישן וחצי חדש, מצב שקשה מאוד לאבחן.
head1 "שני סודות שנוצרים אוטומטית"
if [ -n "$PREV_VERIFY_TOKEN" ] && [ -n "$PREV_POLL_SECRET" ]; then
  IG_VERIFY_TOKEN="$PREV_VERIFY_TOKEN"
  IG_POLL_SECRET="$PREV_POLL_SECRET"
  say "נמצאו סודות מריצה קודמת ב-$ENV_FILE, ומשתמשים בהם שוב."
  say "זה מכוון: ייצור סודות חדשים היה שובר את החיווט שכבר קיים במטא ואת"
  say "הסוד ששמור ב-GitHub Actions."
else
  IG_VERIFY_TOKEN="$(openssl rand -hex 24)"
  IG_POLL_SECRET="$(openssl rand -hex 24)"
  say "IG_VERIFY_TOKEN ו-IG_POLL_SECRET נוצרו אקראית. אין לך שום דבר להמציא"
  say "ואין מה לזכור, הראשון יוצג לך בסוף כדי להדביק במטא, והשני נשמר לקובץ"
  say "מקומי מוגן שהסורק המקומי קורא ממנו."
fi
ok "שני הסודות מוכנים"

# שומרים את הסודות לקובץ המקומי כבר עכשיו, לפני הפריסה. אם משהו ייפול באמצע,
# הסודות לא יאבדו, וריצה חוזרת תשתמש באותם ערכים במקום לשבור חיווט קיים.
# הכתובת נוספת לקובץ בסוף, אחרי שהיא נקבעת.
STEP="שמירה מוקדמת של הסודות"
mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR" 2>/dev/null || true
: > "$ENV_FILE"
chmod 600 "$ENV_FILE"
{
  echo "# נוצר על ידי scripts/setup.sh, קובץ סודות מקומי, הרשאות 600."
  echo "# משמש את scripts/ig-poll-ping.sh, scripts/refresh-ig-token.sh ו-scripts/doctor.sh."
  echo "# אל תכניס אותו לגיט ואל תעתיק אותו לשום שירות."
  echo "IG_POLL_SECRET=$IG_POLL_SECRET"
  echo "IG_VERIFY_TOKEN=$IG_VERIFY_TOKEN"
  echo "SUPABASE_URL=$SUPABASE_URL"
  echo "SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY"
} >> "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok "הסודות נשמרו ב-$ENV_FILE בהרשאות 600"

# ---------------------------------------------------------------------------
# 5) אימות הטוקן מול ה-API החי, לפני שפורסים משהו
# ---------------------------------------------------------------------------
STEP="אימות הטוקן מול אינסטגרם"
head1 "אימות הטוקן מול אינסטגרם"
say "בודקים מול ה-API האמיתי לפני שנוגעים בוורסל, כי טוקן שגוי מתגלה אחרת"
say "רק בסוף, אחרי שכל השאר כבר הוגדר."

me_body="$(mktmp)"
me_code="$(curl -s -o "$me_body" -w '%{http_code}' --max-time 30 \
  -H "Authorization: Bearer $IG_ACCESS_TOKEN" \
  "https://graph.instagram.com/v23.0/me?fields=user_id,username,account_type" || true)"

json_field() {
  # קורא שדה מקובץ JSON. עובר דרך node כי הוא כבר דרישה, וכך אין תלות ב-jq.
  JSON_FILE="$1" JSON_KEY="$2" node -e '
    const fs = require("fs");
    try {
      const o = JSON.parse(fs.readFileSync(process.env.JSON_FILE, "utf8"));
      const v = o[process.env.JSON_KEY];
      process.stdout.write(v == null ? "" : String(v));
    } catch (e) { process.stdout.write(""); }
  '
}

# קוד 000 משמעו שהבקשה לא הגיעה בכלל. זו לא דחייה של הטוקן, וחשוב לא לשלוח
# את המשתמש להנפיק מחדש טוקן שלם ותקין רק בגלל רשת שנפלה.
if [ "$me_code" = "000" ]; then
  die "לא הצלחנו להגיע לשרתי אינסטגרם." \
"$(printf '%s\n' \
  "הבקשה לא קיבלה שום תשובה, כלומר זו בעיית רשת ולא בעיה בטוקן." \
  "הטוקן שהזנת לא נבדק ולא נפסל, אין צורך להנפיק חדש." \
  "בדוק חיבור לאינטרנט, חומת אש או VPN, והרץ את הסקריפט שוב.")"
fi

if [ "$me_code" != "200" ]; then
  err_msg="$(JSON_FILE="$me_body" node -e '
    const fs=require("fs");
    try{const o=JSON.parse(fs.readFileSync(process.env.JSON_FILE,"utf8"));
      process.stdout.write(String((o.error&&o.error.message)||"")); }catch(e){process.stdout.write("");}
  ')"
  die "אינסטגרם דחתה את הטוקן, קוד תשובה $me_code." \
"$(printf '%s\n' \
  "ההודעה ממטא: ${err_msg:-אין הודעה}" \
  "" \
  "הסיבות הנפוצות, לפי שכיחות:" \
  "1) הטוקן הודבק חלקית. זו שגיאה 190. הפק אותו מחדש והדבק במלואו." \
  "2) הטוקן פג. הוא תקף שישים יום, ואי אפשר לרענן טוקן שכבר פג, רק להפיק חדש." \
  "3) הטוקן הופק לפני שכל שלוש ההרשאות אושרו. הפקה מחדש פותרת.")"
fi

TOKEN_USER_ID="$(json_field "$me_body" user_id)"
TOKEN_USERNAME="$(json_field "$me_body" username)"
TOKEN_ACCOUNT_TYPE="$(json_field "$me_body" account_type)"

if [ -z "$TOKEN_USER_ID" ]; then
  die "התשובה מאינסטגרם לא הכילה user_id." "זו תשובה לא צפויה, שווה להפיק טוקן חדש ולנסות שוב."
fi

if [ "$TOKEN_USER_ID" != "$IG_SELF_USER_ID" ]; then
  die "הטוקן שייך לחשבון אחר מזה שהזנת." \
"$(printf '%s\n' \
  "הזנת כמזהה החשבון: $IG_SELF_USER_ID" \
  "הטוקן בפועל שייך למזהה: $TOKEN_USER_ID, שם משתמש $TOKEN_USERNAME" \
  "" \
  "זה חשוב ולא טכני בלבד: IG_SELF_USER_ID הוא מה שמסנן את התגובות של החשבון" \
  "עצמו. אם הוא לא נכון, המערכת עלולה לענות לעצמה ולהיכנס ללולאה." \
  "תקן את המזהה, או הפק טוקן לחשבון הנכון, והרץ שוב.")"
fi

ok "הטוקן תקף ושייך לחשבון $TOKEN_USERNAME, מזהה $TOKEN_USER_ID, סוג $TOKEN_ACCOUNT_TYPE"
echo ""
printf 'זה החשבון הנכון? הקש y להמשך: '
IFS= read -r confirm_acc < /dev/tty || confirm_acc=""
case "$confirm_acc" in
  y|Y|yes|YES|כן) : ;;
  *) die "עצרנו לפי בקשתך, כי החשבון לא הנכון." "הפק טוקן מהחשבון הנכון והרץ שוב." ;;
esac

case "$TOKEN_ACCOUNT_TYPE" in
  BUSINESS|MEDIA_CREATOR) : ;;
  *) note "סוג החשבון הוא $TOKEN_ACCOUNT_TYPE, והמסלול הזה דורש BUSINESS או MEDIA_CREATOR. אם השליחה תיכשל בהמשך, זו הסיבה הראשונה לבדוק." ;;
esac

# ---------------------------------------------------------------------------
# 6) הסכמה בסופאבייס: קודם מוודאים שהמפתח בכלל עובד, ואז שהטבלאות קיימות
# ---------------------------------------------------------------------------
STEP="הרצת הסכמה בסופאבייס"
head1 "הסכמה בסופאבייס"

SB_REST="$SUPABASE_URL/rest/v1"

sb_get_code() {
  # מחזיר קוד HTTP לקריאה מול PostgREST. הסוד עובר בכותרות, לעולם לא בכתובת.
  local path="$1" out="$2"
  curl -s -o "$out" -w '%{http_code}' --max-time 30 \
    -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
    "$SB_REST/$path" || true
}

probe="$(mktmp)"
root_code="$(sb_get_code "" "$probe")"
case "$root_code" in
  200|404)
    ok "המפתח מתקבל על ידי הסופאבייס"
    ;;
  401|403)
    die "הסופאבייס דחה את המפתח, קוד $root_code." \
"$(printf '%s\n' \
  "המפתח שהודבק אינו מפתח service_role תקף של הפרויקט $PROJECT_REF." \
  "" \
  "שתי הסיבות הנפוצות: הודבק המפתח הציבורי (anon) במקום הסודי, או שהמפתח" \
  "הועתק מפרויקט אחר. קח אותו ישירות מ-Project Settings, API keys, והרץ שוב.")"
    ;;
  000)
    die "אין תשובה מ-$SUPABASE_URL." "בדוק חיבור לרשת, ושהפרויקט לא במצב מושהה בסופאבייס."
    ;;
  *)
    die "תשובה לא צפויה מהסופאבייס, קוד $root_code." "בדוק שכתובת הפרויקט נכונה."
    ;;
esac

# בודק את כל ארבע הטבלאות, לא רק אחת. הגירה שרצה חלקית משאירה טבלה חסרה,
# וההתקנה הייתה מכריזה הצלחה בזמן שכל claim ייפול בשקט בזמן ריצה.
# מחזיר 0 אם כולן קיימות, 1 אם חסרה לפחות אחת, 2 אם המפתח נדחה.
MISSING_TABLES=""
tables_exist() {
  local out code t
  MISSING_TABLES=""
  for t in ig_automation_rules ig_events ig_conversations ig_tokens; do
    out="$(mktmp)"
    code="$(sb_get_code "$t?select=*&limit=1" "$out")"
    case "$code" in
      200) : ;;
      401|403) return 2 ;;
      *) MISSING_TABLES="$MISSING_TABLES $t" ;;
    esac
  done
  [ -z "$MISSING_TABLES" ]
}

tables_state=0
tables_exist || tables_state=$?
if [ "$tables_state" = "2" ]; then
  die "הסופאבייס דחה את המפתח בקריאה לטבלאות." \
      "כמעט תמיד זה המפתח הציבורי במקום הסודי. קח את המפתח מ-Project Settings, API keys, והרץ שוב."
fi

if [ "$tables_state" = "0" ]; then
  ok "כל ארבע הטבלאות קיימות בפרויקט, מדלגים על הרצת הסכמה"
else
  echo ""
  say "עכשיו צריך אותך לרגע אחד. אין דרך להריץ סכמה בפרויקט סופאבייס דרך"
  say "שורת הפקודה בלי כלים נוספים, ולכן זו הפעולה הידנית הראשונה מתוך שתיים."
  echo ""
  say "1) פתח את עורך ה-SQL של הפרויקט שלך:"
  say "   https://supabase.com/dashboard/project/$PROJECT_REF/sql/new"
  echo ""
  say "2) העתק לשם את כל תוכן הקובץ:"
  say "   $CODE_DIR/$MIGRATION_REL"
  echo ""
  say "3) לחץ Run. אמורות להיווצר ארבע טבלאות."
  echo ""
  attempt=0
  while true; do
    tables_state=0
    tables_exist || tables_state=$?
    [ "$tables_state" = "0" ] && break
    [ "$tables_state" = "2" ] && die "הסופאבייס דחה את המפתח." "בדוק שזה מפתח service_role ולא הציבורי."
    attempt=$((attempt + 1))
    if [ "$attempt" -gt 1 ]; then
      bad "חסרות עדיין טבלאות בפרויקט $PROJECT_REF:$MISSING_TABLES"
      say "אם העורך הציג שגיאה, קרא אותה: הודעה על אובייקט שכבר קיים משמעה"
      say "שהסכמה כבר רצה חלקית. הרץ את הקובץ במלואו, הוא יוצר את כל הארבע."
    fi
    if [ "$attempt" -gt 5 ]; then
      die "הסכמה לא רצה אחרי חמישה ניסיונות." \
          "בלי הטבלאות אין טעם להמשיך, כי כל שאר השלבים כותבים אליהן."
    fi
    printf 'סיימת להריץ את הסכמה? הקש Enter לבדיקה: '
    IFS= read -r _ignore < /dev/tty || true
  done
  ok "כל ארבע הטבלאות נוצרו ונקראות בהצלחה"
fi

# ---------------------------------------------------------------------------
# 7) כתיבת הטוקן לטבלה, שהיא מקור האמת השוטף
# ---------------------------------------------------------------------------
STEP="כתיבת הטוקן לטבלת ig_tokens"
head1 "שמירת הטוקן בטבלה"
say "הטוקן נשמר בטבלה ולא רק במשתנה סביבה, כי הוא מתחדש כל שישים יום ופונקציה"
say "בענן לא יכולה לשנות את הסביבה של עצמה. שורה בטבלה מתעדכנת בשאילתה אחת."

EXPIRES_AT="$(node -e 'process.stdout.write(new Date(Date.now() + 60*24*3600*1000).toISOString())')"

payload="$(mktmp)"
# הערכים מועברים ל-node כמשתני סביבה ולא כארגומנטים, כדי שהטוקן לא יופיע
# ברשימת התהליכים. הבנייה דרך JSON.stringify מונעת שבירה על תו מיוחד.
IG_TOK="$IG_ACCESS_TOKEN" IG_UID="$IG_SELF_USER_ID" IG_EXP="$EXPIRES_AT" node -e '
  process.stdout.write(JSON.stringify({
    id: 1,
    access_token: process.env.IG_TOK,
    ig_user_id: process.env.IG_UID,
    expires_at: process.env.IG_EXP,
    refreshed_at: new Date().toISOString(),
  }));
' > "$payload"

upsert_out="$(mktmp)"
upsert_code="$(curl -s -o "$upsert_out" -w '%{http_code}' --max-time 30 \
  -X POST "$SB_REST/ig_tokens" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: resolution=merge-duplicates,return=minimal" \
  --data-binary "@$payload" || true)"
rm -f "$payload"

case "$upsert_code" in
  200|201|204) ok "השורה נכתבה, תוקף עד $EXPIRES_AT" ;;
  *) die "כתיבת הטוקן לטבלה נכשלה, קוד $upsert_code." "התשובה מהסופאבייס: $(cat "$upsert_out" 2>/dev/null | head -c 400)" ;;
esac

# אימות בקריאה חוזרת, כי פקודה שהצליחה אינה הוכחה שהערך נכתב.
# קוראים רק מזהה ותאריך, לעולם לא את הטוקן עצמו.
readback="$(mktmp)"
read_code="$(sb_get_code "ig_tokens?select=ig_user_id,expires_at&id=eq.1" "$readback")"
readback_uid="$(JSON_FILE="$readback" node -e '
  const fs=require("fs");
  try{const a=JSON.parse(fs.readFileSync(process.env.JSON_FILE,"utf8"));
    process.stdout.write(a && a[0] && a[0].ig_user_id ? String(a[0].ig_user_id) : "");
  }catch(e){process.stdout.write("");}
')"
if [ "$read_code" != "200" ] || [ "$readback_uid" != "$IG_SELF_USER_ID" ]; then
  die "הקריאה החוזרת לא אישרה את השורה." \
      "קוד $read_code, מזהה שחזר: ${readback_uid:-ריק}. בלי שורת טוקן תקינה המערכת לא תשלח כלום."
fi
ok "הקריאה החוזרת אישרה את השורה"

# ---------------------------------------------------------------------------
# 8) קישור לוורסל והזנת שבעת משתני הסביבה
# ---------------------------------------------------------------------------
STEP="קישור הפרויקט לוורסל"
head1 "וורסל: קישור והגדרה"

if ! vercel whoami >/dev/null 2>&1; then
  say "אתה לא מחובר לוורסל, פותחים התחברות."
  vercel login < /dev/tty
fi
VERCEL_USER="$(vercel whoami 2>/dev/null || echo "לא ידוע")"
ok "מחובר לוורסל כ-$VERCEL_USER"

if [ -f "$CODE_DIR/.vercel/project.json" ]; then
  ok "התיקייה כבר מקושרת לפרויקט בוורסל, מדלגים על vercel link"
else
  say "מריצים vercel link. ענה על שאלות ה-CLI, אפשר ליצור פרויקט חדש."
  vercel link < /dev/tty
  [ -f "$CODE_DIR/.vercel/project.json" ] || die "הקישור לא הושלם." "הרץ vercel link ידנית ואז הרץ את הסקריפט שוב."
  ok "הפרויקט מקושר"
fi

PROJECT_NAME="$(JSON_FILE="$CODE_DIR/.vercel/project.json" node -e '
  const fs=require("fs");
  try{const o=JSON.parse(fs.readFileSync(process.env.JSON_FILE,"utf8"));
    process.stdout.write(String(o.projectName||o.name||""));
  }catch(e){process.stdout.write("");}
')"
[ -n "$PROJECT_NAME" ] && ok "שם הפרויקט: $PROJECT_NAME"

STEP="הזנת משתני הסביבה לוורסל"
head1 "שבעת משתני הסביבה"
say "כל משתנה נמחק לפני שהוא נכתב, כדי שהרצה חוזרת תעדכן ולא תיכשל בשקט."
say "הערכים מועברים עם הדגל value במפורש. העברה בצינור נבלעת בשקט ויוצרת"
say "משתנה ריק, וזו אחת התקלות שהכי קשה לאבחן."

set_env() {
  local name="$1" value="$2" log
  log="$(mktmp)"
  if [ -z "$value" ]; then
    die "ניסיון לכתוב את $name עם ערך ריק." "זו בדיוק התקלה שהסקריפט אמור למנוע, עצירה מכוונת."
  fi
  vercel env rm "$name" production --yes >/dev/null 2>&1 || true
  if vercel env add "$name" production --value "$value" --yes >"$log" 2>&1 < /dev/null; then
    ok "$name הוזן, אורך ${#value} תווים"
  else
    bad "$name נכשל"
    head -c 600 "$log" 2>/dev/null || true
    echo ""
    die "הזנת $name נכשלה." "אם ההודעה מדברת על הרשאות, ודא שאתה מחובר לחשבון שבבעלותו הפרויקט."
  fi
  rm -f "$log"
}

set_env META_APP_SECRET            "$META_APP_SECRET"
set_env IG_VERIFY_TOKEN            "$IG_VERIFY_TOKEN"
set_env IG_POLL_SECRET             "$IG_POLL_SECRET"
set_env IG_SELF_USER_ID            "$IG_SELF_USER_ID"
set_env SUPABASE_URL               "$SUPABASE_URL"
set_env SUPABASE_SERVICE_ROLE_KEY  "$SUPABASE_SERVICE_ROLE_KEY"
set_env IG_ACCESS_TOKEN            "$IG_ACCESS_TOKEN"

# ---------------------------------------------------------------------------
# 9) פריסה לפרודקשן וקביעת הדומיין
# ---------------------------------------------------------------------------
STEP="פריסה לפרודקשן"
head1 "פריסה"
say "פורסים עכשיו, ורק אחר כך מחווטים במטא. הסדר הזה חשוב: מטא קוראת לכתובת"
say "מיד בלחיצה על Verify and save, ואם הפריסה לא חיה שום דבר לא נשמר."
echo ""

deploy_log="$(mktmp)"
set +e
vercel deploy --prod --yes 2>&1 | tee "$deploy_log"
deploy_rc="${PIPESTATUS[0]}"
set -e
[ "$deploy_rc" = "0" ] || die "הפריסה נכשלה, קוד $deploy_rc." "גלול למעלה לפלט של וורסל, שם ההודעה המדויקת."

DEPLOY_URL="$(grep -Eo 'https://[A-Za-z0-9._-]+\.vercel\.app' "$deploy_log" | tail -n 1 || true)"
[ -n "$DEPLOY_URL" ] && ok "נפרס אל $DEPLOY_URL"

if [ -n "$PROJECT_NAME" ]; then
  DEFAULT_DOMAIN="$PROJECT_NAME.vercel.app"
elif [ -n "$DEPLOY_URL" ]; then
  DEFAULT_DOMAIN="${DEPLOY_URL#https://}"
else
  DEFAULT_DOMAIN=""
fi

echo ""
say "כתובת הפריסה שקיבלת עכשיו היא ייחודית לפריסה הזו ומשתנה בכל פריסה."
say "מה שמחווטים במטא הוא הדומיין הקבוע של הפרודקשן. ברירת המחדל היא"
say "הכתובת של הפרויקט, ואם יש לך דומיין משלך הזן אותו כאן."
printf 'דומיין הפרודקשן [%s]: ' "$DEFAULT_DOMAIN"
IFS= read -r domain_in < /dev/tty || domain_in=""
domain_in="$(printf '%s' "$domain_in" | tr -d '[:space:]')"
[ -z "$domain_in" ] && domain_in="$DEFAULT_DOMAIN"
[ -n "$domain_in" ] || die "לא נקבע דומיין." "בלי דומיין אי אפשר לאמת ואי אפשר לחווט."
domain_in="${domain_in#https://}"
domain_in="${domain_in#http://}"
domain_in="${domain_in%/}"
PROD_DOMAIN="$domain_in"
BASE_URL="https://$PROD_DOMAIN"
ok "הדומיין שנקבע: $BASE_URL"

# ---------------------------------------------------------------------------
# 10) אימות הפריסה החיה
# ---------------------------------------------------------------------------
STEP="אימות הפריסה"
head1 "אימות מול המערכת החיה"
say "לא מאמינים להצלחת פקודה, מאמינים לאימות של התוצאה."
CHECKS_FAILED=0

# בדיקה א: לחיצת היד של ה-webhook. זו הבדיקה היחידה שבה ערך עובר בכתובת,
# כי כך פרוטוקול האימות של מטא בנוי, ומדובר בטוקן שממילא מודבק לדשבורד שלה.
challenge="$(openssl rand -hex 8)"
wh_body="$(mktmp)"
wh_code="$(curl -s -o "$wh_body" -w '%{http_code}' --max-time 30 -G \
  --data-urlencode "hub.mode=subscribe" \
  --data-urlencode "hub.verify_token=$IG_VERIFY_TOKEN" \
  --data-urlencode "hub.challenge=$challenge" \
  "$BASE_URL/api/ig-webhook" || true)"
wh_text="$(cat "$wh_body" 2>/dev/null || true)"

echo ""
if [ "$wh_code" = "200" ] && [ "$wh_text" = "$challenge" ]; then
  ok "בדיקה 1, לחיצת היד של ה-webhook: הוחזר בדיוק ה-challenge שנשלח"
else
  CHECKS_FAILED=1
  bad "בדיקה 1, לחיצת היד של ה-webhook. קוד $wh_code"
  case "$wh_code" in
    403) say "     403 משמעו שה-verify token לא תואם. הכתובת שנבדקה אולי מצביעה לפריסה ישנה." ;;
    500) say "     500 משמעו שחסר משתנה סביבה בפרודקשן. גלול לסעיף משתני הסביבה." ;;
    404) say "     404 משמעו שהדומיין שהזנת אינו הדומיין של הפרויקט הזה." ;;
    000) say "     אין תשובה בכלל. בדוק את הדומיין ואת החיבור לרשת." ;;
    *)   say "     הגוף שחזר: $(printf '%s' "$wh_text" | head -c 200)" ;;
  esac
fi

# בדיקה ב: נקודת הקצה של הסורק, עם הסוד בכותרת
poll_body="$(mktmp)"
poll_code="$(curl -s -o "$poll_body" -w '%{http_code}' --max-time 70 \
  -H "x-poll-secret: $IG_POLL_SECRET" \
  "$BASE_URL/api/ig-poll" || true)"
poll_text="$(cat "$poll_body" 2>/dev/null || true)"

if [ "$poll_code" = "200" ] && printf '%s' "$poll_text" | grep -Eq '"ok"[[:space:]]*:[[:space:]]*true'; then
  ok "בדיקה 2, נקודת הקצה של הסורק: הוחזר ok אמת"
  if printf '%s' "$poll_text" | grep -q 'no active rules'; then
    note "הסורק מדווח שאין עדיין כללים פעילים, וזה בדיוק המצב הצפוי לפני הכלל הראשון."
  fi
else
  CHECKS_FAILED=1
  bad "בדיקה 2, נקודת הקצה של הסורק. קוד $poll_code"
  say "     הגוף שחזר: $(printf '%s' "$poll_text" | head -c 300)"
  case "$poll_code" in
    403) say "     403 משמעו שהסוד בכותרת לא תואם למשתנה בפרודקשן." ;;
    500) say "     500 עם רשימת missing מציין בדיוק אילו משתנים חסרים, לפי שם ובלי ערכים." ;;
  esac
fi

# ---------------------------------------------------------------------------
# 11) קובץ הסביבה המקומי, לסורק המקומי ולריענון הטוקן
# ---------------------------------------------------------------------------
STEP="כתיבת קובץ הסביבה המקומי"
head1 "קובץ הסביבה המקומי"

# הסודות כבר נשמרו מוקדם יותר, לפני הפריסה. כאן רק מוסיפים את הכתובת
# שנקבעה, שהיא מה שהאבחון צריך כדי לדעת לאן לפנות.
if grep -q '^IG_BASE_URL=' "$ENV_FILE" 2>/dev/null; then
  tmp_env="$(mktmp)"
  grep -v '^IG_BASE_URL=' "$ENV_FILE" > "$tmp_env"
  cat "$tmp_env" > "$ENV_FILE"
  rm -f "$tmp_env"
fi
echo "IG_BASE_URL=$BASE_URL" >> "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok "הכתובת נוספה ל-$ENV_FILE"

# החלפת הפלייסהולדר של הדומיין בקבצי התזמון, אם הוא עדיין שם
STEP="עדכון הדומיין בקבצי התזמון"
patch_domain() {
  local file="$1"
  [ -f "$file" ] || return 0
  grep -q '<VERCEL_PROJECT>.vercel.app' "$file" || return 0
  sed -i.bak "s|<VERCEL_PROJECT>\.vercel\.app|$PROD_DOMAIN|g" "$file"
  rm -f "$file.bak"
  ok "הדומיין עודכן בקובץ ${file#$CODE_DIR/}"
}
patch_domain "$CODE_DIR/.github/workflows/poll.yml"
patch_domain "$CODE_DIR/scripts/ig-poll-ping.sh"

# ---------------------------------------------------------------------------
# 12) סיכום ומה נשאר לאדם
# ---------------------------------------------------------------------------
STEP="סיכום"
CLEAN_EXIT=1

echo ""
echo "============================================================"
echo "מה נשאר לך לעשות במטא"
echo "============================================================"
echo ""
say "זו הפעולה הידנית האחרונה, ואין לה API. ארבעה צעדים, בסדר הזה."
echo ""
say "1) בדשבורד של מטא, במוצר Instagram, בסעיף 2. Configure webhooks,"
say "   הדבק את שני הערכים האלה בדיוק כפי שהם:"
echo ""
echo "   Callback URL:"
echo "   $BASE_URL/api/ig-webhook"
echo ""
echo "   Verify token:"
echo "   $IG_VERIFY_TOKEN"
echo ""
say "   ואז לחץ Verify and save. הפריסה כבר חיה ואומתה, כך שהאימות אמור לעבור."
echo ""
say "2) אחרי השמירה, סמן Subscribe על השדה comments. אם אתה רוצה גם מענה"
say "   לסטוריז, סמן גם messages."
echo ""
say "3) חזור לסעיף 1. Generate access tokens, ובשורת החשבון הזז את המתג"
say "   Webhook Subscription למצב On. זה צעד נפרד מהמנוי לשדה, והוא הכי נשכח:"
say "   בלעדיו האפליקציה רשומה אבל החשבון לא משויך, ואף אירוע לא יגיע."
echo ""
say "4) בראש עמוד האפליקציה הזז את App Mode ממצב Development למצב Live."
say "   אם המתג מסרב, הסיבה כמעט תמיד היא מדיניות הפרטיות או שדה Category ריק."
echo ""
say "הערה חשובה על סדר הדברים: הסורק כבר עובד גם בלי כל זה, כי הוא מושך"
say "תגובות בעצמו. החיווט של ה-webhook מקצר את זמן התגובה מדקות לשניות ברגע"
say "שמטא תאשר Advanced Access."
echo ""
echo "============================================================"
echo "הכלל הראשון"
echo "============================================================"
echo ""
say "בלי כלל אחד לפחות המערכת לא תשלח כלום. הדרך הפשוטה, פקודה אחת:"
echo ""
cat <<'RULE_CMD'
    set -a; . "$HOME/.config/ig-automation/ig.env"; set +a; \
    curl -s -X POST "$SUPABASE_URL/rest/v1/ig_automation_rules" \
      -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Content-Type: application/json" \
      -d '{"name":"כלל ראשון","keyword":"מדריך","match_mode":"exact",
           "dm_templates":["היי, הנה הלינק שביקשת: {{link}} מה הדבר הראשון שבא לך לעשות איתו?",
                           "שלחתי! זה כאן: {{link}} ספר לי מה תבנה עם זה",
                           "קיבלתי אותך, הנה: {{link}} סקרן לדעת מה יצא מזה"],
           "comment_reply_templates":["שלחתי לך בפרטי","מחכה לך בהודעות"],
           "link_url":"https://example.com","priority":0}'
RULE_CMD
echo ""
say "החלף את מילת המפתח ואת הלינק. הפקודה קוראת את הסודות מהקובץ המקומי,"
say "כך שאין צורך להדביק מפתח לשורת הפקודה."
say "הרחבה על ניסוח ההודעות ועל שאר השדות נמצאת ב-05-copy-and-rules.md."
echo ""
echo "============================================================"
echo "תזמון ובדיקה"
echo "============================================================"
echo ""
say "לתזמון מהענן: צור בריפו סוד בשם IG_POLL_SECRET בערך שנשמר בקובץ המקומי,"
say "תחת Settings, Secrets and variables, Actions. הקובץ .github/workflows/poll.yml"
say "כבר קיים ומריץ סבב כל חמש דקות."
echo ""
say "לבדיקה מקצה לקצה: מחשבון אינסטגרם שני, לא שלך, הגב את מילת המפתח על"
say "פוסט קיים, ואז הרץ סבב מיד:"
echo ""
echo "    bash scripts/ig-poll-ping.sh \"\$HOME/.config/ig-automation/ig.env\""
echo ""
say "תגובה מהחשבון שלך מסוננת במכוון, כדי שהמערכת לא תענה לעצמה."
echo ""
if [ -f "$CODE_DIR/scripts/doctor.sh" ]; then
  say "לאבחון בכל שלב:"
  echo ""
  echo "    bash scripts/doctor.sh"
else
  say "לאבחון: 03-gotchas.md בשורש הערכה, מסודר לפי סימפטום, עם סדר בדיקה"
  say "מוגדר בסופו לשאלה למה מישהו לא קיבל הודעה."
fi
echo ""

echo "============================================================"
if [ "$CHECKS_FAILED" = "0" ]; then
  echo "ההתקנה הושלמה, כל הבדיקות עברו."
  echo "============================================================"
  exit 0
else
  echo "ההתקנה הושלמה חלקית, בדיקה אחת או יותר נכשלה."
  echo "ההוראות למעלה עדיין נכונות, אבל אל תחווט במטא לפני שהבדיקות ירוקות,"
  echo "כי מטא קוראת לכתובת בזמן אמת והאימות ייכשל."
  echo "תקן לפי ההודעות למעלה והרץ את הסקריפט שוב, הוא בטוח להרצה חוזרת."
  echo "============================================================"
  exit 1
fi
