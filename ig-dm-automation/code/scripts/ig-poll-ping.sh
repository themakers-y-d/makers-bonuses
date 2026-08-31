#!/bin/bash
# פינג מקומי לסורק, רץ ממתזמן מקומי כשהמחשב דלוק.
# שימוש: ig-poll-ping.sh /path/to/env-file   (קובץ עם IG_POLL_SECRET=...)
set -euo pipefail
ENV_FILE="${1:?usage: ig-poll-ping.sh /path/to/env-file}"
# shellcheck disable=SC1090
source "$ENV_FILE"
: "${IG_POLL_SECRET:?missing in env file}"

out=$(curl -sf --max-time 55 -H "x-poll-secret: ${IG_POLL_SECRET}" "https://<VERCEL_PROJECT>.vercel.app/api/ig-poll")
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ${out}"

# heartbeat: כותב קובץ סטטוס שמערכת ניטור יכולה לקרוא. אופציונלי.
# נכתב ישירות ולא דרך helper חיצוני, כדי שהסקריפט יישאר עצמאי לחלוטין.
HB_DIR="$HOME/Library/Logs/job-heartbeats"
mkdir -p "$HB_DIR" 2>/dev/null || true
case "$out" in
  *'"ok":true'*) printf 'status=0 %s\n' "$(date +%s)" > "$HB_DIR/ig-poll-ping.hb" 2>/dev/null || true ;;
  *)             printf 'status=1 %s\n' "$(date +%s)" > "$HB_DIR/ig-poll-ping.hb" 2>/dev/null || true; exit 1 ;;
esac
