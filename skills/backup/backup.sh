#!/bin/bash
# MAKERS backup engine. Takes a snapshot of the system folder and sends it to
# the owner's private GitHub repository.
#
#   backup.sh now      back up now, in the foreground, and print one result line
#   backup.sh start    SessionStart hook: report problems from the last runs, then
#                      start a backup in the background if the last try is 3+ hours old
#   backup.sh stop     Stop hook: same 3-hour throttle, background, never prints
#   backup.sh status   print the state, for the agent to read to the owner
#
# How it stays out of the owner's way: the snapshot is built in its own index
# file, kept on its own ref (refs/makers/backup) and sent to its own remote
# (makers-backup), never to "origin". The owner's branch, staging area and the
# restore points the Archivist commits are never touched, and the local history
# is never pushed. GitHub only receives snapshots built here from the current
# files, after the size and secret checks below, and the secret check fails
# closed: if anything that looks like a key is still in the snapshot, nothing
# is sent.
#
# The hooks never block a session: they report from the saved state and run
# the backup itself detached. Problems are recorded in .git/makers-backup/ and
# reported at the next session start once they are real (48 hours without a
# good backup).

set -u
MODE="${1:-now}"
EVERY=10800                 # 3 hours between automatic tries
STALE=172800                # 48 hours without a good backup = tell the owner
REF="refs/makers/backup"
REMOTE="makers-backup"
EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
cd "$ROOT" 2>/dev/null || exit 0

loud() { [ "$MODE" = "now" ] || [ "$MODE" = "status" ] || [ "$MODE" = "run" ]; }
bye() { loud && exit "${1:-0}"; exit 0; }

# Not installed here: nothing to do, and the hooks stay silent.
if [ ! -d .git ] || ! git rev-parse --git-dir >/dev/null 2>&1; then
  loud && echo "NOT INSTALLED: this folder has no backup yet."
  bye 1
fi
ST=".git/makers-backup"
mkdir -p "$ST" 2>/dev/null || bye 1
touch "$ST/held-paths" "$ST/held-reasons" 2>/dev/null

NOW=$(date +%s)
age_of() { local t; t=$(cut -d' ' -f1 "$1" 2>/dev/null); [ -n "$t" ] && echo $(( NOW - t )) || echo 999999999; }
days() { echo $(( $1 / 86400 )); }

report_start() {
  # Only what the owner needs to hear, once, in words the agent turns into Hebrew.
  local ok_age; ok_age=$(age_of "$ST/ok")
  if [ -f "$ST/ok" ] && [ "$ok_age" -gt "$STALE" ]; then
    echo "MAKERS BACKUP: the last good backup was $(days "$ok_age") days ago. Last problem: $(cat "$ST/error" 2>/dev/null || echo unknown). Tell the owner in one Hebrew sentence and offer to fix it now with the backup skill."
  elif [ ! -f "$ST/ok" ] && [ "$(age_of "$ST/first-try")" -gt "$STALE" ]; then
    echo "MAKERS BACKUP: the backup is set up but has never succeeded. Last problem: $(cat "$ST/error" 2>/dev/null || echo unknown). Tell the owner in one Hebrew sentence and offer to fix it now with the backup skill."
  fi
  if [ -s "$ST/held" ] && [ "$(cat "$ST/held")" != "$(cat "$ST/held.told" 2>/dev/null)" ]; then
    echo "MAKERS BACKUP: these files are kept out of the backup on purpose: $(tr '\n' ';' < "$ST/held"). Tell the owner in one Hebrew sentence which files and why. The backup skill explains each reason and how to bring a file back in."
    cp "$ST/held" "$ST/held.told" 2>/dev/null
  fi
}

if [ "$MODE" = "status" ]; then
  if [ -f "$ST/ok" ]; then
    read -r _t iso sha < "$ST/ok"
    echo "LAST GOOD BACKUP: $iso ($(days "$(age_of "$ST/ok")") days ago), snapshot $sha"
  else
    echo "LAST GOOD BACKUP: none yet"
  fi
  [ -f "$ST/error" ] && echo "LAST PROBLEM: $(cat "$ST/error")"
  [ -s "$ST/held" ] && { echo "KEPT OUT ON PURPOSE:"; cat "$ST/held"; }
  echo "REMOTE: $(git remote get-url "$REMOTE" 2>/dev/null || echo none)"
  exit 0
fi

# The hooks: report from the saved state, then run the backup detached, at
# most every 3 hours, so a slow upload never holds the session.
if [ "$MODE" = "start" ] || [ "$MODE" = "stop" ]; then
  [ "$MODE" = "start" ] && report_start
  if [ "$(age_of "$ST/try")" -ge "$EVERY" ]; then
    nohup bash "$HERE/backup.sh" run >/dev/null 2>&1 < /dev/null &
  fi
  exit 0
fi

# From here: "now" (foreground, prints) or "run" (detached, from a hook).
LOCK="$ST/lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  # A lock is stale only when its run is gone, or after 6 hours whatever it says:
  # a slow first upload can take well over an hour and must not be cut in half.
  OWNER=$(cat "$LOCK/pid" 2>/dev/null)
  if { [ -n "$OWNER" ] && ! kill -0 "$OWNER" 2>/dev/null; } || [ -n "$(find "$LOCK" -maxdepth 0 -mmin +360 2>/dev/null)" ]; then
    rm -rf "$LOCK"; mkdir "$LOCK" 2>/dev/null || bye 0
  else
    [ "$MODE" = "now" ] && echo "BUSY: another backup is running right now. Try again in a few minutes."
    bye 0
  fi
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

echo "$NOW" > "$ST/try"
[ -f "$ST/first-try" ] || echo "$NOW" > "$ST/first-try"

fail() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M')" "$1" > "$ST/error"
  [ "$MODE" = "now" ] && echo "PROBLEM: $1"
  bye 1
}

git remote get-url "$REMOTE" >/dev/null 2>&1 || fail "no GitHub address is connected (remote $REMOTE missing)"

IDX="$ST/index"
EXC="$ST/exclude"
# One line of the exclude list for one exact path: glob characters and a
# trailing space are escaped, so the pattern matches that file and nothing else.
pat() { printf '/%s\n' "$(printf '%s' "$1" | sed -e 's/[][*?\\!#]/\\&/g' -e 's/ $/\\ /')"; }
# held-reasons: one line per held file, "<code> <path>", code is one word.
why_of() { case "$1" in secret) echo "looks like it has a password or token inside" ;; big) echo "bigger than 49 MB" ;; nested) echo "a separate git project, its files are not in the backup" ;; *) echo "$1" ;; esac; }
write_exclude() {
  cut -d' ' -f2- "$ST/held-reasons" > "$ST/held-paths" 2>/dev/null
  { cat "$HERE/exclude-base" 2>/dev/null; while IFS= read -r p; do [ -n "$p" ] && pat "$p"; done < "$ST/held-paths"; } > "$EXC"
}           # relative on purpose: the same on Mac and in Git Bash
G() { GIT_INDEX_FILE="$IDX" git -c core.excludesFile="$EXC" -c core.quotepath=off -c core.longpaths=true "$@"; }

# A run killed halfway (timeout, sleep, shutdown) can leave the index locked.
rm -f "$IDX.lock"
# A new version of the fixed list may exclude files the kept index already
# holds; start the index over when the list changed.
LISTSUM=$(git hash-object "$HERE/exclude-base" 2>/dev/null)
[ "$LISTSUM" = "$(cat "$ST/exclude-base.sum" 2>/dev/null)" ] || { rm -f "$IDX"; echo "$LISTSUM" > "$ST/exclude-base.sum"; }

# What never goes to GitHub: the fixed list beside this script, plus files this
# script held back before. Kept in .git so the owner's own git is unaffected.
write_exclude

# Fail closed if the list is not being applied, whatever the reason.
G check-ignore -q --no-index .env 2>/dev/null || fail "the list of files that never go to GitHub is not being applied, so nothing was sent"

hold() {  # hold <code> <path>: keep a file out of every future snapshot
  local code="$1" p="$2"
  G rm -q --cached --ignore-unmatch -- "$p" >/dev/null 2>&1
  grep -qxF -- "$p" "$ST/held-paths" 2>/dev/null && return 0
  pat "$p" >> "$EXC"
  printf '%s\n' "$p" >> "$ST/held-paths"
  printf '%s %s\n' "$code" "$p" >> "$ST/held-reasons"
}
rebuild_held_list() {
  : > "$ST/held"
  while IFS= read -r line; do
    [ -n "$line" ] && printf '%s (%s)\n' "${line#* }" "$(why_of "${line%% *}")" >> "$ST/held"
  done < "$ST/held-reasons" 2>/dev/null
}

# Passwords and tokens. Each alternative must start a word, so a long note
# name with "sk-" inside it is not mistaken for a key.
B='(^|[^A-Za-z0-9_-])'
PAT="${B}(sk-ant-[A-Za-z0-9_-]{20,}|sk-(proj-)?[A-Za-z0-9_-]{32,}|sk_[a-f0-9]{40,}|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|GOCSPX-[A-Za-z0-9_-]{20,}|EAA[A-Za-z0-9]{80,}|hf_[A-Za-z0-9]{30,}|(ntn|secret)_[A-Za-z0-9]{40,}|sbp_[A-Za-z0-9]{30,}|sk_live_[A-Za-z0-9]{20,}|rk_live_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.|[0-9]{8,10}:[A-Za-z0-9_-]{35})|-----BEGIN [A-Z ]*PRIVATE KEY-----"

# A file held for a secret comes back by itself once the secret is gone from it.
if [ -s "$ST/held-reasons" ]; then
  : > "$ST/held-reasons.new"
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    code="${line%% *}"; p="${line#* }"
    if [ "$code" = "secret" ] && [ -f "$p" ] && ! LC_ALL=C grep -aqE -- "$PAT" "$p" 2>/dev/null; then
      continue
    fi
    printf '%s\n' "$line" >> "$ST/held-reasons.new"
  done < "$ST/held-reasons"
  mv "$ST/held-reasons.new" "$ST/held-reasons"
  write_exclude
fi

# Big files first: GitHub refuses anything over 100 MB and warns over 50.
while IFS= read -r -d '' f; do
  f="${f#./}"; G check-ignore -q --no-index -- "$f" 2>/dev/null || hold big "$f"
done < <(find . -path ./.git -prune -o -type f -size +49M -print0 2>/dev/null)

# The index is kept between runs, so only changed files are read again.
# --ignore-errors: one locked or unreadable file must not stop the whole backup.
G add -A --ignore-errors . >/dev/null 2>"$ST/add.err"
TREE=$(G write-tree 2>/dev/null) || fail "could not read the folder ($(head -c 200 "$ST/add.err"))"

PARENT=$(git rev-parse -q --verify "$REF^{commit}" 2>/dev/null || git rev-parse -q --verify "refs/remotes/$REMOTE/main^{commit}" 2>/dev/null || true)
PTREE=${PARENT:+$(git rev-parse "$PARENT^{tree}")}
BASE=${PTREE:-$EMPTY_TREE}

secrets_in() { git -c core.quotepath=off diff -z --text --name-only --diff-filter=ACMR -G"$PAT" "$BASE" "$1" 2>/dev/null; }
FOUND=0
while IFS= read -r -d '' f; do
  [ -n "$f" ] && { hold secret "$f"; FOUND=1; }
done < <(secrets_in "$TREE")
if [ "$FOUND" = 1 ]; then
  TREE=$(G write-tree 2>/dev/null) || fail "could not read the folder after holding back a file"
  [ -z "$(secrets_in "$TREE" | tr -d '\0')" ] || fail "a file that looks like it has a password inside could not be kept out, so nothing was sent"
fi

# Separate git projects inside the folder are stored as a pointer only.
while IFS= read -r -d '' line; do
  p="${line#*$'\t'}"; grep -qxF -- "$p" "$ST/held-paths" 2>/dev/null || hold nested "$p"
done < <(git ls-tree -r -z "$TREE" 2>/dev/null | tr '\0' '\n' | awk '$1=="160000"' | tr '\n' '\0')
rebuild_held_list

if [ -n "$PARENT" ] && [ "$TREE" = "$PTREE" ]; then
  : # nothing changed since the last snapshot; still confirm GitHub has it below
else
  MSG="גיבוי $(date '+%d.%m.%Y %H:%M')"
  C=$(git -c user.name="MAKERS backup" -c user.email="backup@makers.local" commit-tree "$TREE" ${PARENT:+-p "$PARENT"} -m "$MSG" 2>"$ST/commit.err") \
    || fail "could not create the snapshot ($(head -c 200 "$ST/commit.err"))"
  git update-ref "$REF" "$C" || fail "could not record the snapshot"
fi
SNAP=$(git rev-parse -q --verify "$REF" 2>/dev/null || echo "$PARENT")
[ -n "$SNAP" ] || fail "no snapshot to send"

# A short check first, so an offline laptop gives up within a minute. Slow
# networks take several seconds to answer, so the wait is generous.
{ curl -sI -m 20 https://github.com >/dev/null 2>&1 || { sleep 5; curl -sI -m 30 https://github.com >/dev/null 2>&1; }; } || fail "no internet connection to github.com"

export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 push -q --no-verify "$REMOTE" "$REF:refs/heads/main" 2>"$ST/push.err" \
  || fail "GitHub refused the upload ($(tr '\n' ' ' < "$ST/push.err" | head -c 300))"

# Proof, not inference: read back what GitHub holds now.
ONGH=$(git ls-remote "$REMOTE" refs/heads/main 2>/dev/null | cut -f1)
[ "$ONGH" = "$SNAP" ] || fail "uploaded, but GitHub shows a different snapshot ($ONGH)"

printf '%s %s %s\n' "$(date +%s)" "$(date '+%Y-%m-%dT%H:%M')" "${SNAP:0:7}" > "$ST/ok"
rm -f "$ST/error"
[ "$MODE" = "now" ] && echo "BACKED UP: snapshot ${SNAP:0:7} is on GitHub, $(date '+%d.%m.%Y %H:%M')"
exit 0
