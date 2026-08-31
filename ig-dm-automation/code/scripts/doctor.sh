#!/bin/bash
# doctor.sh: אבחון מקצה לקצה של אוטומציית מילת המפתח ל-DM באינסטגרם.
#
# שימוש:
#   doctor.sh [נתיב לקובץ env] [כתובת הפריסה]
#   doctor.sh --live ...   מריץ מחזור סריקה אמיתי במקום בדיקה יבשה
#   ברירת מחדל לקובץ ה-env: $HOME/.config/ig-automation/ig.env
#
# קובץ ה-env מכיל: IG_POLL_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
# כתובת הפריסה נלקחת מ-IG_BASE_URL בקובץ, או מהארגומנט השני, או בשאלה חד פעמית.
#
# הסקריפט קורא בלבד. הוא לא כותב לבסיס הנתונים, לא משנה הגדרות, ולא שולח
# הודעות: בדיקת הסורק רצה במצב יבש שעוצר לפני התגובות. רק הדגל --live מריץ
# מחזור אמיתי, ואז הוא כן עלול לשלוח, בדיוק כמו הרצה רגילה של הסורק.
# הוא לעולם לא מדפיס ערך של סוד, רק שם של משתנה, אורך, וסטטוס.
#
# עשר בדיקות, כל אחת עצמאית: כישלון באחת לא עוצר את השאר, כי התמונה המלאה
# היא מה שמאפשר לאבחן בלי שיחת תמיכה. יציאה שונה מאפס אם משהו נכשל,
# כדי שאפשר יהיה להריץ אותו כג'וב מתוזמן.
#
# תלויות: curl ו-python3 בלבד. אין תלות ב-jq.

set -o pipefail

# ── תשתית ────────────────────────────────────────────────────────────────

PASSED=0
FAILED=0
WARNED=0
FIRST_ACTION=""

TMP=""
cleanup() { [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null; }
trap cleanup EXIT

pass() {
  PASSED=$((PASSED + 1))
  printf 'תקין: %s\n' "$1"
}

# fail "שם הבדיקה" "מה לעשות" ["שורה נוספת" ...]
fail() {
  FAILED=$((FAILED + 1))
  printf 'נכשל: %s\n' "$1"
  shift
  [ -z "$FIRST_ACTION" ] && [ -n "$1" ] && FIRST_ACTION="$1"
  while [ "$#" -gt 0 ]; do
    printf '    %s\n' "$1"
    shift
  done
}

# warn "שם הבדיקה" "מה לעשות" ["שורה נוספת" ...]
warn() {
  WARNED=$((WARNED + 1))
  printf 'אזהרה: %s\n' "$1"
  shift
  while [ "$#" -gt 0 ]; do
    printf '    %s\n' "$1"
    shift
  done
}

# info: שורת המשך אינפורמטיבית מתחת לבדיקה שעברה, בלי סטטוס משלה
info() { printf '    %s\n' "$1"; }

# http_get TIMEOUT URL [ארגומנטים נוספים ל-curl]
# ממלא HTTP_CODE, HTTP_BODY, HTTP_ERR. מחזיר 1 אם הקריאה עצמה נכשלה (קוד 000).
HTTP_CODE="000"
HTTP_BODY=""
HTTP_ERR=""
http_get() {
  local t="$1"
  local url="$2"
  shift 2
  HTTP_CODE="000"
  HTTP_BODY=""
  HTTP_ERR=""
  HTTP_CODE=$(curl -sS -o "$TMP/body" -w '%{http_code}' --max-time "$t" "$@" "$url" 2>"$TMP/err")
  [ -z "$HTTP_CODE" ] && HTTP_CODE="000"
  HTTP_BODY=$(cat "$TMP/body" 2>/dev/null)
  HTTP_ERR=$(tr -d '\r' <"$TMP/err" 2>/dev/null | head -n 1)
  [ "$HTTP_CODE" != "000" ]
}

# חילוץ ערך יחיד מ-JSON, בלי jq. שימוש: json_get "נתיב.בנקודות" <<< "$body"
# מערך בשורש נתמך דרך אינדקס מספרי, לדוגמה "0.expires_at".
json_get() {
  python3 -c '
import sys, json
path = sys.argv[1].split(".") if sys.argv[1] else []
try:
    cur = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for p in path:
    try:
        if isinstance(cur, list):
            cur = cur[int(p)]
        else:
            cur = cur[p]
    except Exception:
        sys.exit(0)
if cur is None:
    sys.exit(0)
if isinstance(cur, (dict, list)):
    sys.stdout.write(json.dumps(cur, ensure_ascii=False))
else:
    sys.stdout.write(str(cur))
' "$1" 2>/dev/null
}

# מספר האיברים במערך JSON בשורש, או ריק אם הגוף אינו מערך
json_len() {
  python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if isinstance(d, list):
    sys.stdout.write(str(len(d)))
' 2>/dev/null
}

# המרת חותמת ISO לשניות מאז 1970, ניידת: קודם BSD (מק), אחר כך GNU, ואז python3.
epoch_of() {
  local iso="$1"
  local base
  base=$(printf '%s' "$iso" | cut -c1-19 | tr ' ' 'T')
  local out
  out=$(TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%S" "$base" +%s 2>/dev/null)
  if [ -z "$out" ]; then
    out=$(date -u -d "${base}Z" +%s 2>/dev/null)
  fi
  if [ -z "$out" ]; then
    out=$(python3 -c '
import sys, datetime
try:
    d = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%S")
    sys.stdout.write(str(int(d.replace(tzinfo=datetime.timezone.utc).timestamp())))
except Exception:
    pass
' "$base" 2>/dev/null)
  fi
  printf '%s' "$out"
}

# חותמת ISO של "לפני N שעות", ניידת: BSD ואז GNU
iso_hours_ago() {
  local h="$1"
  local out
  out=$(date -u -v-"${h}"H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
  if [ -z "$out" ]; then
    out=$(date -u -d "${h} hours ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
  fi
  printf '%s' "$out"
}

# ── הגנה על התלויות ──────────────────────────────────────────────────────

if ! command -v curl >/dev/null 2>&1; then
  printf 'נכשל: הכלי curl אינו מותקן\n'
  printf '    התקן curl. בלעדיו אי אפשר לבדוק שום דבר.\n'
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf 'נכשל: הכלי python3 אינו מותקן\n'
  printf '    התקן python3. הוא משמש לפענוח תשובות JSON, ובלעדיו אין אבחון.\n'
  exit 2
fi

TMP=$(mktemp -d 2>/dev/null || mktemp -d -t igdoctor)
if [ -z "$TMP" ] || [ ! -d "$TMP" ]; then
  printf 'נכשל: לא ניתן ליצור תיקייה זמנית\n'
  printf '    בדוק הרשאות כתיבה ב-/tmp והרץ שוב.\n'
  exit 2
fi

# ── קריאת קובץ ה-env ─────────────────────────────────────────────────────

# הדגל --live יכול להופיע בכל מקום בשורת הפקודה, והשאר נשאר מיקומי כרגיל
DOCTOR_LIVE_POLL=0
POSITIONAL=""
POSITIONAL2=""
for arg in "$@"; do
  case "$arg" in
    --live) DOCTOR_LIVE_POLL=1 ;;
    *)
      if [ -z "$POSITIONAL" ]; then POSITIONAL="$arg"
      elif [ -z "$POSITIONAL2" ]; then POSITIONAL2="$arg"
      fi
      ;;
  esac
done

ENV_FILE="${POSITIONAL:-$HOME/.config/ig-automation/ig.env}"
BASE_URL_ARG="${POSITIONAL2:-}"

IG_POLL_SECRET=""
SUPABASE_URL=""
SUPABASE_SERVICE_ROLE_KEY=""
IG_ACCESS_TOKEN=""
IG_BASE_URL=""
ENV_READABLE="no"

# פרסור ולא source: הקובץ לא מורץ כקוד, ותווים מיוחדים בסודות לא שוברים כלום.
if [ -f "$ENV_FILE" ] && [ -r "$ENV_FILE" ]; then
  ENV_READABLE="yes"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      \#* | "") continue ;;
    esac
    line="${line#export }"
    case "$line" in
      *=*) ;;
      *) continue ;;
    esac
    k="${line%%=*}"
    v="${line#*=}"
    k=$(printf '%s' "$k" | tr -d ' \t')
    # הסרת מרכאות עוטפות, אם יש
    case "$v" in
      \"*\") v="${v#\"}"; v="${v%\"}" ;;
      \'*\') v="${v#\'}"; v="${v%\'}" ;;
    esac
    v="${v%$'\r'}"
    case "$k" in
      IG_POLL_SECRET) IG_POLL_SECRET="$v" ;;
      SUPABASE_URL) SUPABASE_URL="$v" ;;
      SUPABASE_SERVICE_ROLE_KEY) SUPABASE_SERVICE_ROLE_KEY="$v" ;;
      IG_ACCESS_TOKEN) IG_ACCESS_TOKEN="$v" ;;
      IG_BASE_URL) IG_BASE_URL="$v" ;;
    esac
  done <"$ENV_FILE"
fi

SB_URL="${SUPABASE_URL%/}"
SB_KEY="$SUPABASE_SERVICE_ROLE_KEY"

# כתובת הפריסה: ארגומנט שני גובר, אחריו IG_BASE_URL מהקובץ, ואם אין, שאלה אחת.
BASE_URL="$BASE_URL_ARG"
[ -z "$BASE_URL" ] && BASE_URL="$IG_BASE_URL"
if [ -z "$BASE_URL" ] && [ -t 0 ]; then
  printf 'כתובת הפריסה חסרה. הזן אותה, לדוגמה https://my-project.vercel.app וסיים באנטר: '
  read -r BASE_URL || BASE_URL=""
  printf '\n'
fi
BASE_URL="${BASE_URL%/}"
case "$BASE_URL" in
  http://* | https://*) ;;
  "") ;;
  *) BASE_URL="https://$BASE_URL" ;;
esac

printf 'אבחון אוטומציית האינסטגרם\n'
printf 'קובץ הגדרות: %s\n' "$ENV_FILE"
printf 'כתובת פריסה: %s\n' "${BASE_URL:-לא הוגדרה}"
printf '\n'

SB_HDR_A="apikey: ${SB_KEY}"
SB_HDR_B="Authorization: Bearer ${SB_KEY}"

# ── בדיקה 1: קובץ ההגדרות והמשתנים ───────────────────────────────────────

if [ "$ENV_READABLE" != "yes" ]; then
  if [ -f "$ENV_FILE" ]; then
    fail "קובץ ההגדרות קיים אך לא ניתן לקריאה" \
      "הרץ: chmod 600 \"$ENV_FILE\" ובדוק שהמשתמש הנוכחי הוא הבעלים." \
      "אם הקובץ יושב ב-iCloud Drive, העבר אותו למקום מקומי, ג'וב מתוזמן לא יקרא אותו משם."
  else
    fail "קובץ ההגדרות לא נמצא" \
      "צור אותו: mkdir -p \"$(dirname "$ENV_FILE")\" ואז ערוך את $ENV_FILE" \
      "שלוש שורות חובה: IG_POLL_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ושורה רביעית מומלצת IG_BASE_URL." \
      "אפשר גם להצביע על קובץ אחר: doctor.sh /path/to/env"
  fi
else
  MISSING=""
  [ -z "$IG_POLL_SECRET" ] && MISSING="$MISSING IG_POLL_SECRET"
  [ -z "$SUPABASE_URL" ] && MISSING="$MISSING SUPABASE_URL"
  [ -z "$SUPABASE_SERVICE_ROLE_KEY" ] && MISSING="$MISSING SUPABASE_SERVICE_ROLE_KEY"

  if [ -n "$MISSING" ]; then
    fail "משתנים חסרים או ריקים בקובץ ההגדרות" \
      "מלא ערך אמיתי לכל אחד מאלה:$MISSING" \
      "משתנה שקיים בשורה אך ערכו ריק הוא התקלה הנפוצה ביותר כאן, בדרך כלל אחרי העתקה שנבלעה בשקט." \
      "לעולם אל תעתיק סוד דרך משיכת סביבה, סודות מסומנים חוזרים משם כמחרוזת ריקה. משוך תמיד ממקור האמת."
  else
    pass "קובץ ההגדרות קיים וכל המשתנים הנדרשים מלאים"

    LEN_SECRET=${#IG_POLL_SECRET}
    LEN_KEY=${#SB_KEY}

    if [ "$LEN_SECRET" -lt 16 ]; then
      warn "הערך של IG_POLL_SECRET קצר בצורה חשודה, $LEN_SECRET תווים" \
        "סוד תקין נוצר עם openssl rand -hex 24 והוא באורך 48 תווים." \
        "ודא שהערך כאן זהה תו בתו לערך שהוגדר בסביבת הפרודקשן של הפריסה."
    fi

    KEY_SHAPE="לא מוכר"
    case "$SB_KEY" in
      eyJ*) KEY_SHAPE="JWT" ;;
      sb_secret_*) KEY_SHAPE="sb_secret" ;;
    esac
    if [ "$LEN_KEY" -lt 40 ] || [ "$KEY_SHAPE" = "לא מוכר" ]; then
      warn "הערך של SUPABASE_SERVICE_ROLE_KEY נראה לא תקין, $LEN_KEY תווים, תבנית $KEY_SHAPE" \
        "מפתח service אמיתי הוא או JWT ארוך שמתחיל ב-eyJ או מפתח שמתחיל ב-sb_secret_" \
        "משוך אותו מחדש מלוח הבקרה של סופאבייס, תחת Project Settings ואז API keys, והדבק אותו במלואו."
    fi

    case "$SB_URL" in
      https://*.supabase.co) ;;
      *)
        warn "SUPABASE_URL בתבנית לא צפויה" \
          "הצורה התקינה היא https://<PROJECT_REF>.supabase.co בלי לוכסן בסוף ובלי נתיב." \
          "הערך הנוכחי מתחיל ב: $(printf '%s' "$SB_URL" | cut -c1-40)"
        ;;
    esac
  fi
fi

# ── בדיקה 2: חיבור לסופאבייס ─────────────────────────────────────────────

SB_OK="no"
if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "חיבור לסופאבייס לא נבדק, חסרים פרטי גישה" \
    "מלא את SUPABASE_URL ואת SUPABASE_SERVICE_ROLE_KEY בקובץ $ENV_FILE והרץ שוב."
else
  if http_get 20 "${SB_URL}/rest/v1/ig_automation_rules?select=id&limit=1" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
    case "$HTTP_CODE" in
      200)
        SB_OK="yes"
        pass "סופאבייס עונה, קוד 200"
        ;;
      401 | 403)
        fail "סופאבייס דחה את המפתח, קוד $HTTP_CODE" \
          "המפתח שגוי, ריק למעשה, או שייך לפרויקט אחר. הפק אותו מחדש מ-Project Settings ואז API keys." \
          "ודא שזה מפתח service ולא מפתח ציבורי, ושהוא נכתב לקובץ במלואו ולא נחתך."
        ;;
      404)
        fail "סופאבייס עונה אך הטבלה לא קיימת, קוד 404" \
          "ההגירה מעולם לא רצה על הפרויקט הזה. הרץ את supabase/migrations/001_ig_automation.sql בעורך ה-SQL של סופאבייס." \
          "אם ההגירה כן רצה, ודא ש-SUPABASE_URL מצביע על אותו פרויקט שבו נוצרו הטבלאות."
        ;;
      *)
        fail "סופאבייס החזיר קוד לא צפוי, $HTTP_CODE" \
          "פתח את הפרויקט בלוח הבקרה של סופאבייס וודא שהוא פעיל ולא מושהה." \
          "גוף התשובה: $(printf '%s' "$HTTP_BODY" | cut -c1-200)"
        ;;
    esac
  else
    fail "אין תקשורת אל סופאבייס" \
      "בדוק את הכתובת ואת החיבור לרשת. הכתובת שנוסתה: ${SB_URL}/rest/v1/" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 3: ארבע הטבלאות ────────────────────────────────────────────────

if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "בדיקת הטבלאות לא רצה, אין גישה לסופאבייס" \
    "תקן קודם את בדיקה 2 והרץ שוב."
else
  MISSING_TABLES=""
  UNKNOWN_TABLES=""
  DENIED=0
  CHECKED=0
  for t in ig_automation_rules ig_events ig_conversations ig_tokens; do
    CHECKED=$((CHECKED + 1))
    if http_get 20 "${SB_URL}/rest/v1/${t}?select=*&limit=1" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
      case "$HTTP_CODE" in
        200) ;;
        404) MISSING_TABLES="$MISSING_TABLES $t" ;;
        401 | 403) DENIED=$((DENIED + 1)) ;;
        *) UNKNOWN_TABLES="$UNKNOWN_TABLES ${t}:${HTTP_CODE}" ;;
      esac
    else
      UNKNOWN_TABLES="$UNKNOWN_TABLES ${t}:אין_תקשורת"
    fi
  done

  if [ "$DENIED" = "$CHECKED" ]; then
    fail "אף טבלה לא נבדקה, הגישה נדחתה על כל אחת מהן" \
      "זו אותה בעיית מפתח שבבדיקה 2, ולא בעיה בטבלאות. תקן את SUPABASE_SERVICE_ROLE_KEY והרץ שוב."
  elif [ "$DENIED" -gt 0 ]; then
    fail "הגישה נדחתה על חלק מהטבלאות" \
      "מצב לא צפוי, כי כל ארבע הטבלאות מוגדרות עם אותן הרשאות בדיוק. בדוק שלא שונו ידנית ההרשאות של טבלה בודדת."
  elif [ -n "$MISSING_TABLES" ]; then
    fail "טבלאות חסרות:$MISSING_TABLES" \
      "הרץ את ההגירה המלאה, supabase/migrations/001_ig_automation.sql, בעורך ה-SQL של הפרויקט." \
      "הרצה חלקית של ההגירה משאירה את המערכת במצב שבו חלק מהזרימה עובד וחלק נופל בשקט."
  elif [ -n "$UNKNOWN_TABLES" ]; then
    fail "טבלאות שהחזירו תשובה לא צפויה:$UNKNOWN_TABLES" \
      "בדוק בלוח הבקרה של סופאבייס שהפרויקט פעיל ושהטבלאות לא שונו ידנית."
  else
    pass "כל ארבע הטבלאות קיימות ונגישות"
  fi
fi

# ── בדיקה 4: שורת הטוקן ותאריך התפוגה ────────────────────────────────────

TOKEN=""
TOKEN_SOURCE=""
if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "בדיקת הטוקן לא רצה, אין גישה לסופאבייס" \
    "תקן קודם את בדיקה 2 והרץ שוב."
else
  if http_get 20 "${SB_URL}/rest/v1/ig_tokens?select=access_token,expires_at,refreshed_at&id=eq.1" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
    if [ "$HTTP_CODE" = "200" ]; then
      ROWS=$(printf '%s' "$HTTP_BODY" | json_len)
      if [ "${ROWS:-0}" = "0" ]; then
        if [ -n "$IG_ACCESS_TOKEN" ]; then
          TOKEN="$IG_ACCESS_TOKEN"
          TOKEN_SOURCE="משתנה הסביבה IG_ACCESS_TOKEN"
          warn "אין שורת טוקן בטבלת ig_tokens, המערכת נשענת על משתנה הסביבה" \
            "הקוד נופל אחורה אל IG_ACCESS_TOKEN, כך שהשליחה עשויה לעבוד, אבל הרענון האוטומטי לא יעבוד לעולם." \
            "הכנס את הטוקן לטבלה: insert into ig_tokens (id, access_token, expires_at) values (1, '<TOKEN>', '<ISO_EXPIRY>');" \
            "בלי זה הטוקן יפוג בעוד שישים יום והמערכת תשתתק בלי שום שגיאה גלויה."
        else
          fail "אין שורת טוקן בטבלת ig_tokens ואין טוקן גיבוי" \
            "המערכת לא יכולה לשלוח שום הודעה. הפק טוקן בלוח הבקרה של מטא והכנס אותו לטבלה." \
            "insert into ig_tokens (id, access_token, expires_at) values (1, '<TOKEN>', '<ISO_EXPIRY>');" \
            "הטוקן מוצג פעם אחת בלבד בדיאלוג של מטא, העתק אותו מיד."
        fi
      else
        TOKEN=$(printf '%s' "$HTTP_BODY" | json_get "0.access_token")
        TOKEN_SOURCE="טבלת ig_tokens"
        EXPIRES=$(printf '%s' "$HTTP_BODY" | json_get "0.expires_at")
        REFRESHED=$(printf '%s' "$HTTP_BODY" | json_get "0.refreshed_at")
        if [ -z "$EXPIRES" ]; then
          fail "שורת הטוקן קיימת אך אין בה תאריך תפוגה" \
            "עדכן את expires_at בשורה id=1. בלי תאריך, ג'וב הרענון לא יודע מתי לפעול והטוקן ימות בשקט."
        else
          EXP_S=$(epoch_of "$EXPIRES")
          NOW_S=$(date -u +%s)
          if [ -z "$EXP_S" ] || [ "$EXP_S" = "0" ]; then
            warn "לא הצלחתי לפענח את תאריך התפוגה של הטוקן" \
              "הערך בטבלה: $EXPIRES" \
              "ודא שהוא בפורמט ISO, לדוגמה 2026-10-28T12:00:00Z"
          else
            DAYS_LEFT=$(((EXP_S - NOW_S) / 86400))
            if [ "$DAYS_LEFT" -lt 0 ]; then
              fail "הטוקן פג לפני $((0 - DAYS_LEFT)) ימים" \
                "טוקן שפג אי אפשר לרענן בשום צורה. הפק טוקן חדש בלוח הבקרה של מטא, תחת Generate access tokens." \
                "אחרי ההפקה עדכן את הטבלה: update ig_tokens set access_token='<TOKEN>', expires_at='<ISO_EXPIRY>', refreshed_at=now() where id=1;" \
                "זו הסיבה הנפוצה ביותר למערכת ששותקת לגמרי בלי להיראות שבורה."
            elif [ "$DAYS_LEFT" -lt 10 ]; then
              warn "לטוקן נותרו $DAYS_LEFT ימים בלבד" \
                "הרץ עכשיו: scripts/refresh-ig-token.sh \"$ENV_FILE\"" \
                "אם הוא לא רץ אוטומטית מדי יום, תזמן אותו. הבאפר של עשרה ימים קיים כדי לתת עשר הזדמנויות להיכשל בלי לאבד את הטוקן."
            else
              pass "הטוקן קיים בטבלה, נותרו $DAYS_LEFT ימים לתפוגה"
              [ -n "$REFRESHED" ] && info "רוענן לאחרונה: $REFRESHED"
            fi
          fi
        fi
      fi
    elif [ "$HTTP_CODE" = "404" ]; then
      fail "טבלת ig_tokens לא קיימת" \
        "הרץ את ההגירה supabase/migrations/001_ig_automation.sql."
    else
      fail "קריאת טבלת ig_tokens נכשלה, קוד $HTTP_CODE" \
        "ראה את בדיקה 2, זו כנראה אותה בעיית גישה."
    fi
  else
    fail "אין תקשורת בקריאת טבלת ig_tokens" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 5: הטוקן מול ה-API החי ─────────────────────────────────────────

if [ -z "$TOKEN" ]; then
  fail "תוקף הטוקן מול אינסטגרם לא נבדק, אין טוקן לבדוק" \
    "תקן קודם את בדיקה 4."
else
  if http_get 20 "https://graph.instagram.com/v23.0/me?fields=user_id,username" -H "Authorization: Bearer ${TOKEN}"; then
    if [ "$HTTP_CODE" = "200" ]; then
      IG_USERNAME=$(printf '%s' "$HTTP_BODY" | json_get "username")
      IG_UID=$(printf '%s' "$HTTP_BODY" | json_get "user_id")
      pass "הטוקן תקף מול אינסטגרם, החשבון הוא ${IG_USERNAME:-לא ידוע}"
      info "מזהה המשתמש: ${IG_UID:-לא ידוע}, מקור הטוקן: $TOKEN_SOURCE"
    else
      ERR_CODE=$(printf '%s' "$HTTP_BODY" | json_get "error.code")
      ERR_MSG=$(printf '%s' "$HTTP_BODY" | json_get "error.message")
      if [ "$ERR_CODE" = "190" ]; then
        fail "הטוקן נדחה עם שגיאה 190, כלומר פג תוקף או בוטל" \
          "הפק טוקן חדש בלוח הבקרה של מטא ועדכן את הטבלה: update ig_tokens set access_token='<TOKEN>', expires_at='<ISO_EXPIRY>', refreshed_at=now() where id=1;" \
          "טוקן מתבטל גם כשמפיקים אחד חדש, כי ההפקה החדשה מבטלת את הקודם. אם הפקת טוקן לאחרונה ושכחת לעדכן את הטבלה, זו הסיבה." \
          "הודעת מטא: ${ERR_MSG:-אין}"
      else
        fail "הטוקן נדחה, קוד HTTP $HTTP_CODE, קוד שגיאה ${ERR_CODE:-לא ידוע}" \
          "הודעת מטא: ${ERR_MSG:-$(printf '%s' "$HTTP_BODY" | cut -c1-200)}" \
          "אם זו שגיאת הרשאה, הטוקן הופק לפני שכל ההרשאות אושרו. אשר את ההרשאות והפק אותו מחדש."
      fi
    fi
  else
    fail "אין תקשורת אל graph.instagram.com" \
      "בדוק חיבור לרשת. פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 6: קיים לפחות כלל פעיל אחד ─────────────────────────────────────

if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "בדיקת הכללים לא רצה, אין גישה לסופאבייס" \
    "תקן קודם את בדיקה 2."
else
  if http_get 20 "${SB_URL}/rest/v1/ig_automation_rules?select=id,name,keyword,match_mode&active=eq.true&order=priority.desc&limit=200" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
    if [ "$HTTP_CODE" = "200" ]; then
      RULE_COUNT=$(printf '%s' "$HTTP_BODY" | json_len)
      RULE_COUNT="${RULE_COUNT:-0}"
      if [ "$RULE_COUNT" = "0" ]; then
        fail "אין אף כלל פעיל, המערכת לעולם לא תשלח שום הודעה" \
          "הסורק יוצא מיד עם ההערה no active rules, וזה נראה כמו הצלחה. הוסף כלל אחד לפחות:" \
          "insert into ig_automation_rules (name, keyword, match_mode, dm_templates, comment_reply_templates, link_url, active, priority)" \
          "values ('מדריך', 'מדריך', 'exact', '[\"שלחתי לך: {{link}}\",\"הנה זה, {{link}}\"]'::jsonb, '[\"שלחתי בפרטי\"]'::jsonb, 'https://example.com', true, 0);" \
          "החזק בין ארבעה לשמונה נוסחים שונים ב-dm_templates, טקסט זהה שנשלח שוב ושוב נקרא כספאם." \
          "אם קיימים כללים אך כולם כבויים, בדוק את העמודה active."
      else
        pass "קיימים $RULE_COUNT כללים פעילים"
        printf '%s' "$HTTP_BODY" | python3 -c '
import sys, json
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for r in rows[:5]:
    sys.stdout.write("    %s: מילת מפתח %s, מצב %s\n" % (
        r.get("name") or "בלי שם", r.get("keyword"), r.get("match_mode")))
' 2>/dev/null
      fi
    else
      fail "קריאת טבלת הכללים נכשלה, קוד $HTTP_CODE" \
        "ראה את בדיקה 2, זו כנראה אותה בעיית גישה."
    fi
  else
    fail "אין תקשורת בקריאת טבלת הכללים" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 7: נקודת הקצה של ה-webhook ─────────────────────────────────────

if [ -z "$BASE_URL" ]; then
  fail "נקודת הקצה של ה-webhook לא נבדקה, אין כתובת פריסה" \
    "הוסף שורה IG_BASE_URL=https://<PROJECT>.vercel.app לקובץ $ENV_FILE, או העבר את הכתובת כארגומנט שני."
else
  if http_get 20 "${BASE_URL}/api/ig-webhook?hub.mode=subscribe&hub.verify_token=doctor-intentionally-wrong&hub.challenge=doctor" ; then
    case "$HTTP_CODE" in
      403)
        pass "נקודת הקצה של ה-webhook חיה ודוחה טוקן אימות שגוי כמצופה"
        info "זו בדיקת שלילה בלבד. לחיצת יד מלאה דורשת את IG_VERIFY_TOKEN, והאבחון הזה לא שומר אותו."
        info "לבדיקה מלאה הרץ ידנית: curl -i \"${BASE_URL}/api/ig-webhook?hub.mode=subscribe&hub.verify_token=<IG_VERIFY_TOKEN>&hub.challenge=12345\" וצפה ל-200 עם הטקסט 12345 בלבד."
        ;;
      200)
        fail "נקודת הקצה החזירה 200 לטוקן אימות שגוי" \
          "זו חשיפה אמיתית: כל אחד יכול לרשום את ה-webhook. ודא ש-IG_VERIFY_TOKEN מוגדר בסביבת הפרודקשן ואינו ריק." \
          "משתנה ריק בסביבה גורם בדיוק להתנהגות הזו, וזה נכשל בשקט."
        ;;
      404)
        fail "נקודת הקצה של ה-webhook לא נמצאה, קוד 404" \
          "הפריסה לא כוללת את api/ig-webhook.js, או שכתובת הבסיס שגויה. הכתובת שנוסתה: ${BASE_URL}/api/ig-webhook" \
          "ודא שהפריסה האחרונה הצליחה ושהיא סביבת production ולא preview."
        ;;
      500)
        fail "נקודת הקצה של ה-webhook עונה אך קורסת, קוד 500" \
          "בדרך כלל משתנה סביבה חסר בפרודקשן. בדוק את META_APP_SECRET, IG_VERIFY_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IG_SELF_USER_ID." \
          "בדיקה 8 מדפיסה את השמות החסרים בדיוק, אם הסורק סובל מאותה בעיה."
        ;;
      *)
        fail "נקודת הקצה של ה-webhook החזירה קוד לא צפוי, $HTTP_CODE" \
          "גוף התשובה: $(printf '%s' "$HTTP_BODY" | cut -c1-200)"
        ;;
    esac
  else
    fail "אין תקשורת אל נקודת הקצה של ה-webhook" \
      "הכתובת שנוסתה: ${BASE_URL}/api/ig-webhook" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 8: נקודת הקצה של הסורק ─────────────────────────────────────────

if [ -z "$BASE_URL" ]; then
  fail "נקודת הקצה של הסורק לא נבדקה, אין כתובת פריסה" \
    "הוסף שורה IG_BASE_URL=https://<PROJECT>.vercel.app לקובץ $ENV_FILE, או העבר את הכתובת כארגומנט שני."
elif [ -z "$IG_POLL_SECRET" ]; then
  fail "נקודת הקצה של הסורק לא נבדקה, חסר IG_POLL_SECRET" \
    "מלא את IG_POLL_SECRET בקובץ $ENV_FILE, באותו ערך בדיוק שהוגדר בסביבת הפרודקשן."
else
  # מצב יבש כברירת מחדל: הסורק מאשר שהוא מוגדר ומחובר, ועוצר לפני התגובות.
  # זה מכוון: כלי אבחון לא אמור לשלוח הודעה לאדם אמיתי רק מפני שהרצת אותו.
  # למחזור אמיתי הרץ עם --live, או הרץ את scripts/ig-poll-ping.sh.
  if [ "${DOCTOR_LIVE_POLL:-0}" = "1" ]; then
    POLL_MODE_NOTE="מחזור חי"
    POLL_DRY_HEADER="x-poll-dry-run: 0"
  else
    POLL_MODE_NOTE="מצב יבש, בלי שליחה"
    POLL_DRY_HEADER="x-poll-dry-run: 1"
  fi
  # הסבב עצמו מוגבל לארבעים וחמש שניות, לכן ההמתנה כאן ארוכה יותר
  if http_get 75 "${BASE_URL}/api/ig-poll" -H "x-poll-secret: ${IG_POLL_SECRET}" -H "$POLL_DRY_HEADER"; then
    case "$HTTP_CODE" in
      200)
        POLL_OK=$(printf '%s' "$HTTP_BODY" | json_get "ok")
        if [ "$POLL_OK" = "True" ] || [ "$POLL_OK" = "true" ]; then
          pass "הסורק ענה ok, $POLL_MODE_NOTE"
          printf '%s' "$HTTP_BODY" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if d.get("dryRun"):
    sys.stdout.write("    בדיקה יבשה: הטוקן נטען, נמצאו %s כללים פעילים, ולא נשלחה שום הודעה.\n" % d.get("activeRules", 0))
    sys.stdout.write("    למחזור אמיתי: doctor.sh --live, או scripts/ig-poll-ping.sh\n")
else:
    keys = ["scanned", "sent", "duplicate", "backlog", "failed"]
    parts = ["%s %s" % (k, d.get(k, 0)) for k in keys]
    parts.append("truncated %s" % ("כן" if d.get("truncated") else "לא"))
    sys.stdout.write("    מונים: " + ", ".join(parts) + "\n")
    if d.get("truncated"):
        sys.stdout.write("    הסבב נקטע על תקציב הזמן, זה תקין. הסבב הבא ימשיך מאותה נקודה.\n")
if d.get("note"):
    sys.stdout.write("    הערה מהסורק: %s\n" % d["note"])
' 2>/dev/null
        else
          POLL_ERR=$(printf '%s' "$HTTP_BODY" | json_get "error")
          case "$POLL_ERR" in
            "no token")
              fail "הסורק רץ אך אין לו טוקן" \
                "טבלת ig_tokens ריקה וגם משתנה הסביבה IG_ACCESS_TOKEN אינו מוגדר בפרודקשן. ראה את בדיקה 4."
              ;;
            "rules load failed")
              fail "הסורק לא הצליח לטעון את הכללים" \
                "לפונקציה בפרודקשן אין גישה לסופאבייס. בדוק את SUPABASE_URL ואת SUPABASE_SERVICE_ROLE_KEY בהגדרות הפריסה, לא בקובץ המקומי." \
                "סוד שהועתק דרך משיכת סביבה נכתב לעיתים כמחרוזת ריקה, בלי שום שגיאה בדרך."
              ;;
            *)
              fail "הסורק החזיר ok שלילי" \
                "השגיאה שדווחה: ${POLL_ERR:-אין}" \
                "שגיאה שמתחילה ב-graph היא תשובה של אינסטגרם, ואז בדיקה 5 מסבירה אותה. שגיאת timeout היא איטיות רשת ולא תקלת הגדרה."
              ;;
          esac
        fi
        ;;
      403)
        fail "הסורק דחה את הבקשה, קוד 403" \
          "הערך של IG_POLL_SECRET בקובץ המקומי אינו זהה לזה שבסביבת הפרודקשן." \
          "הגדר אותו מחדש בפריסה עם העברה מפורשת של הערך, לדוגמה: vercel env add IG_POLL_SECRET production --value \"\$VALUE\" --yes" \
          "אל תזרים ערך דרך צינור, במצב לא אינטראקטיבי הוא נבלע והמשתנה נוצר ריק."
        ;;
      500)
        MISSING_LIST=$(printf '%s' "$HTTP_BODY" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
m = d.get("missing") or {}
names = [k for k, v in m.items() if v]
sys.stdout.write(" ".join(names))
' 2>/dev/null)
        if [ -n "$MISSING_LIST" ]; then
          fail "הסורק אינו מוגדר בפרודקשן, משתנים חסרים או ריקים" \
            "השמות שהפונקציה דיווחה עליהם:$MISSING_LIST" \
            "הגדר כל אחד מהם בסביבת ה-production של הפריסה עם --value מפורש, ואז פרוס מחדש." \
            "משתנה שקיים ברשימה אך ערכו ריק מדווח כאן בדיוק כמו משתנה חסר."
        else
          fail "הסורק החזיר 500 בלי פירוט" \
            "בדוק את לוגי הפונקציה בפריסה. גוף התשובה: $(printf '%s' "$HTTP_BODY" | cut -c1-200)"
        fi
        ;;
      404)
        fail "נקודת הקצה של הסורק לא נמצאה, קוד 404" \
          "הכתובת שנוסתה: ${BASE_URL}/api/ig-poll" \
          "ודא שהפריסה כוללת את api/ig-poll.js ושכתובת הבסיס היא של סביבת production."
        ;;
      *)
        fail "הסורק החזיר קוד לא צפוי, $HTTP_CODE" \
          "גוף התשובה: $(printf '%s' "$HTTP_BODY" | cut -c1-200)"
        ;;
    esac
  else
    fail "אין תקשורת אל נקודת הקצה של הסורק" \
      "הכתובת שנוסתה: ${BASE_URL}/api/ig-poll" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}" \
      "אם השגיאה היא פסק זמן, ייתכן שהסבב ארוך מהרגיל. הרץ שוב פעם אחת לפני שמסיקים תקלה."
  fi
fi

# ── בדיקה 9: פעילות אחרונה ביומן האירועים ────────────────────────────────

if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "סיכום הפעילות לא רץ, אין גישה לסופאבייס" \
    "תקן קודם את בדיקה 2."
else
  SINCE_7D=$(iso_hours_ago 168)
  if [ -z "$SINCE_7D" ]; then
    warn "לא הצלחתי לחשב את חלון שבעת הימים" \
      "פקודת date במערכת הזו אינה תואמת לא ל-BSD ולא ל-GNU. הרץ את שאילתות האבחון ידנית בעורך ה-SQL."
  elif http_get 30 "${SB_URL}/rest/v1/ig_events?select=action,created_at,error&created_at=gte.${SINCE_7D}&order=id.desc&limit=5000" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
    if [ "$HTTP_CODE" = "200" ]; then
      SUMMARY=$(printf '%s' "$HTTP_BODY" | python3 -c '
import sys, json, datetime
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(1)
if not isinstance(rows, list):
    sys.exit(1)
now = datetime.datetime.now(datetime.timezone.utc)
d1 = now - datetime.timedelta(hours=24)
c24, c7 = {}, {}
for r in rows:
    a = r.get("action") or "לא ידוע"
    c7[a] = c7.get(a, 0) + 1
    ts = (r.get("created_at") or "").replace("Z", "+00:00")
    try:
        t = datetime.datetime.fromisoformat(ts)
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        continue
    if t >= d1:
        c24[a] = c24.get(a, 0) + 1

def line(c):
    if not c:
        return "אין"
    return ", ".join("%s %d" % (k, v) for k, v in sorted(c.items(), key=lambda x: -x[1]))

print("TOTAL7=%d" % len(rows))
print("L24=%s" % line(c24))
print("L7=%s" % line(c7))
print("SENT24=%d" % c24.get("dm_sent", 0))
print("FAILED7=%d" % c7.get("dm_failed", 0))
' 2>/dev/null)
      if [ -z "$SUMMARY" ]; then
        warn "יומן האירועים נקרא אך התשובה לא נפענחה" \
          "הרץ ידנית בעורך ה-SQL: select action, count(*) from ig_events where created_at > now() - interval '24 hours' group by 1;"
      else
        TOTAL7=$(printf '%s' "$SUMMARY" | sed -n 's/^TOTAL7=//p')
        L24=$(printf '%s' "$SUMMARY" | sed -n 's/^L24=//p')
        L7=$(printf '%s' "$SUMMARY" | sed -n 's/^L7=//p')
        FAILED7=$(printf '%s' "$SUMMARY" | sed -n 's/^FAILED7=//p')

        if [ "${TOTAL7:-0}" = "0" ]; then
          warn "אין שום אירוע ביומן בשבעת הימים האחרונים" \
            "אם הגיעו תגובות בתקופה הזו, המערכת לא ראתה אותן. בדוק שהסורק באמת מתוזמן ורץ, ולא רק שהוא עונה כשקוראים לו ידנית." \
            "אם לא הגיעו תגובות, זה תקין ואין מה לתקן."
        else
          pass "יומן האירועים פעיל, $TOTAL7 אירועים בשבעת הימים האחרונים"
          info "ב-24 שעות אחרונות: $L24"
          info "בשבעה ימים אחרונים: $L7"
        fi

        if [ "${FAILED7:-0}" != "0" ]; then
          if http_get 20 "${SB_URL}/rest/v1/ig_events?select=created_at,event_key,error&action=eq.dm_failed&order=id.desc&limit=1" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
            LAST_ERR=$(printf '%s' "$HTTP_BODY" | json_get "0.error")
            LAST_AT=$(printf '%s' "$HTTP_BODY" | json_get "0.created_at")
            warn "יש $FAILED7 שליחות שנכשלו בשבעת הימים האחרונים" \
              "הכישלון האחרון, $LAST_AT: ${LAST_ERR:-אין טקסט שגיאה}" \
              "קוד 190 בטקסט משמעו טוקן שפג, ראה בדיקה 5. שגיאה על חלון זמן משמעה תגובה בת יותר משבעה ימים, וזה חסום מצד מטא. שגיאת הרשאה משמעה שהטוקן הופק לפני אישור כל ההרשאות, ואז מפיקים אותו מחדש."
          fi
        fi
      fi
    elif [ "$HTTP_CODE" = "404" ]; then
      fail "טבלת ig_events לא קיימת" \
        "הרץ את ההגירה supabase/migrations/001_ig_automation.sql."
    else
      fail "קריאת יומן האירועים נכשלה, קוד $HTTP_CODE" \
        "ראה את בדיקה 2, זו כנראה אותה בעיית גישה."
    fi
  else
    fail "אין תקשורת בקריאת יומן האירועים" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── בדיקה 10: שורות תקועות ───────────────────────────────────────────────

if [ -z "$SB_URL" ] || [ -z "$SB_KEY" ]; then
  fail "בדיקת שורות תקועות לא רצה, אין גישה לסופאבייס" \
    "תקן קודם את בדיקה 2."
else
  SINCE_10M=""
  S10=$(date -u -v-10M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
  [ -z "$S10" ] && S10=$(date -u -d "10 minutes ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null)
  SINCE_10M="$S10"

  if [ -z "$SINCE_10M" ]; then
    warn "לא הצלחתי לחשב את חלון עשר הדקות" \
      "הרץ ידנית: select * from ig_events where action = 'claimed' and created_at < now() - interval '10 minutes';"
  elif http_get 20 "${SB_URL}/rest/v1/ig_events?select=id,event_key,created_at&action=eq.claimed&created_at=lt.${SINCE_10M}&order=id.desc&limit=100" -H "$SB_HDR_A" -H "$SB_HDR_B"; then
    if [ "$HTTP_CODE" = "200" ]; then
      STUCK=$(printf '%s' "$HTTP_BODY" | json_len)
      STUCK="${STUCK:-0}"
      if [ "$STUCK" = "0" ]; then
        pass "אין שורות תקועות בסטטוס claimed"
      else
        OLDEST=$(printf '%s' "$HTTP_BODY" | python3 -c '
import sys, json
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if rows:
    r = rows[-1]
    sys.stdout.write("%s (id %s)" % (r.get("created_at"), r.get("id")))
' 2>/dev/null)
        warn "יש $STUCK שורות תקועות בסטטוס claimed, כלומר פונקציה נקטעה באמצע" \
          "הישנה ביותר: ${OLDEST:-לא ידוע}" \
          "כנראה שהאנשים האלה לא קיבלו הודעה, והמערכת לא תנסה שוב כי השורה כבר תפוסה." \
          "אזהרה לפני שמוחקים: שורה יכולה להישאר claimed גם אחרי שההודעה כן נשלחה," \
          "כי עדכון הסטטוס הוא מיטב מאמץ ויכול להיכשל בנפרד מהשליחה. מחיקה כזו" \
          "מחזירה את התגובה למצב לא מטופל, ואז הסבב הבא ישלח לאותו אדם הודעה שנייה." \
          "לכן: בדוק קודם בהודעות של החשבון אם ההודעה יצאה. אם היא יצאה, אל תמחק." \
          "רק אם ודאי שלא נשלחה, זו המחיקה היחידה שמותרת בטבלה:" \
          "delete from ig_events where action = 'claimed' and created_at < now() - interval '10 minutes';" \
          "אם זה חוזר בכל סבב, הסבב חורג מתקציב הזמן. הקטן את מספר פריטי המדיה או את מספר התגובות לפריט."
      fi
    else
      fail "בדיקת השורות התקועות נכשלה, קוד $HTTP_CODE" \
        "ראה את בדיקה 2, זו כנראה אותה בעיית גישה."
    fi
  else
    fail "אין תקשורת בבדיקת השורות התקועות" \
      "פרטי השגיאה מ-curl: ${HTTP_ERR:-אין}"
  fi
fi

# ── סיכום ────────────────────────────────────────────────────────────────

printf '\n'
printf 'סיכום: %d עברו, %d נכשלו, %d אזהרות\n' "$PASSED" "$FAILED" "$WARNED"

if [ "$FAILED" -gt 0 ]; then
  printf 'הפעולה החשובה ביותר עכשיו: %s\n' "$FIRST_ACTION"
  exit 1
fi

if [ "$WARNED" -gt 0 ]; then
  printf 'המערכת עובדת, אבל יש אזהרות שכדאי לטפל בהן לפני שהן הופכות לתקלה.\n'
fi

exit 0
