#!/bin/bash
# רענון טוקן ה-Instagram Graph (60 יום), רץ יומית מ-launchd.
# שימוש: refresh-ig-token.sh /path/to/env-file
# קובץ ה-env מכיל: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# הטוקן חי בשורה יחידה (id=1) בטבלת ig_tokens; מרעננים כשנשארו פחות מ-10 ימים.
set -euo pipefail

ENV_FILE="${1:?usage: refresh-ig-token.sh /path/to/env-file}"
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${SUPABASE_URL:?missing in env file}"
: "${SUPABASE_SERVICE_ROLE_KEY:?missing in env file}"

SB="${SUPABASE_URL%/}/rest/v1/ig_tokens"
AUTH=(-H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY")

row=$(curl -sf "${SB}?select=access_token,expires_at&id=eq.1" "${AUTH[@]}")
token=$(echo "$row" | jq -r '.[0].access_token // empty')
expires=$(echo "$row" | jq -r '.[0].expires_at // empty')

if [ -z "$token" ]; then
  echo "refresh-ig-token: no token row in ig_tokens (id=1), nothing to refresh" >&2
  exit 1
fi

now_s=$(date +%s)
exp_s=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${expires%%[.+]*}" +%s 2>/dev/null || echo 0)
days_left=$(( (exp_s - now_s) / 86400 ))

# heartbeat: גם "לא נדרש רענון" הוא ריצה מוצלחת.
HB_DIR="$HOME/Library/Logs/job-heartbeats"
beat() { mkdir -p "$HB_DIR" 2>/dev/null || true; printf 'status=%s %s\n' "${1:-0}" "$(date +%s)" > "$HB_DIR/ig-token-refresh.hb" 2>/dev/null || true; }
trap 'beat 1' ERR

if [ "$days_left" -ge 10 ]; then
  echo "refresh-ig-token: ${days_left} days left, no refresh needed"
  beat 0
  exit 0
fi

# הטוקן חייב להיות בן 24 שעות לפחות ולא פג; מחזיר 60 יום חדשים.
resp=$(curl -sf "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=${token}")
new_token=$(echo "$resp" | jq -r '.access_token // empty')
expires_in=$(echo "$resp" | jq -r '.expires_in // empty')

if [ -z "$new_token" ] || [ -z "$expires_in" ]; then
  echo "refresh-ig-token: refresh call failed: $(echo "$resp" | jq -c 'del(.access_token)' 2>/dev/null || echo 'unparseable')" >&2
  exit 1
fi

new_expires=$(date -u -v "+${expires_in}S" +"%Y-%m-%dT%H:%M:%SZ")
curl -sf -X PATCH "${SB}?id=eq.1" "${AUTH[@]}" \
  -H "Content-Type: application/json" -H "Prefer: return=minimal" \
  -d "{\"access_token\":\"${new_token}\",\"expires_at\":\"${new_expires}\",\"refreshed_at\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"

echo "refresh-ig-token: refreshed, new expiry ${new_expires}"
beat 0
