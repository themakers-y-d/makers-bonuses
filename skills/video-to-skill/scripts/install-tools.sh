#!/bin/bash
# The tools of the video-to-skill skill, on the owner's own computer (Claude Code or Codex).
# Same folder (~/reel-studio), same pinned uv, Python and transcription libraries as the MAKERS video editor and
# the carousel skill, so a gift the owner already installed is reused and nothing downloads twice.
#
#   base   uv, Python, and the small tools: yt-dlp (captions and video from a link), av and Pillow (frames).
#          About a minute and about 150 MB.
#   libs   the transcription libraries (faster-whisper). Only needed for a video with no captions, a reel or a
#          file. The long part: a few minutes and about 300 MB. The Hebrew model (1.6 GB) downloads later, on
#          the first transcription.
#   wait LOG MARK   returns within about 90 seconds with READY, STILL RUNNING, STUCK or FAILED.
#   update  updates yt-dlp only, when a video site changed and a link stopped working.
#
# yt-dlp is not pinned on purpose: video sites change every few weeks and an old yt-dlp stops reading them.
# REEL_STUDIO overrides the folder, for tests only.
STUDIO="${REEL_STUDIO:-$HOME/reel-studio}"
mkdir -p "$STUDIO/tools" "$STUDIO/models" && cd "$STUDIO" || exit 1
export UV_PYTHON_INSTALL_DIR="$STUDIO/tools/python" UV_CACHE_DIR="$STUDIO/tools/cache" VIRTUAL_ENV="$STUDIO/.venv"
PY="$STUDIO/.venv/bin/python"; [ -x "$PY" ] || PY="$STUDIO/.venv/Scripts/python.exe"
UV="$STUDIO/tools/uv/uv"; [ -x "$UV" ] || UV="$STUDIO/tools/uv/uv.exe"

if [ "$1" = "base" ]; then
  if [ ! -x "$STUDIO/tools/uv/uv" ] && [ ! -x "$STUDIO/tools/uv/uv.exe" ]; then
    case "$(uname -sm)" in
      "Darwin arm64")  UVPKG=uv-aarch64-apple-darwin.tar.gz ;;
      "Darwin x86_64") UVPKG=uv-x86_64-apple-darwin.tar.gz ;;
      MINGW*|MSYS*|CYGWIN*) UVPKG=uv-x86_64-pc-windows-msvc.zip ;;
      *) echo "PROBLEM unsupported computer $(uname -sm)"; exit 1 ;;
    esac
    case "$UVPKG" in
      uv-aarch64-apple-darwin.tar.gz) UVSHA=a9a8df1eedeb192f2e47e40e2faabfb387db4b850209118786d42f89dde3e0ba ;;
      uv-x86_64-apple-darwin.tar.gz)  UVSHA=cb5fa57bafe68fc0fb94b17f06bee0b0b9a7feb94ccbd110445afa0696e39273 ;;
      uv-x86_64-pc-windows-msvc.zip)  UVSHA=6dbb02d79e419522f1c500f0adb1cddcff0cda7d59b0d66ea7f5e3b4a1b2f5f0 ;;
    esac
    # the shell writes the file, not curl: curl -o into a path with Hebrew letters fails on Windows Git Bash
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/0.12.19/$UVPKG" > "tools/$UVPKG" \
      || { echo "PROBLEM no internet connection, or GitHub is blocked"; rm -f "tools/$UVPKG"; exit 1; }
    GOT=$( (shasum -a 256 "tools/$UVPKG" 2>/dev/null || sha256sum "tools/$UVPKG") | cut -d' ' -f1 )
    [ "$GOT" = "$UVSHA" ] || { echo "PROBLEM the downloaded file does not match its checksum, stopping"; rm -f "tools/$UVPKG"; exit 1; }
    mkdir -p tools/uv
    case "$UVPKG" in
      *.zip) if command -v unzip >/dev/null 2>&1; then unzip -oq "tools/$UVPKG" -d tools/uv; else powershell -NoProfile -Command "Expand-Archive -Force 'tools/$UVPKG' 'tools/uv'"; fi ;;
      *) tar -xzf "tools/$UVPKG" -C tools/uv --strip-components 1 ;;
    esac
    UV="$STUDIO/tools/uv/uv"; [ -x "$UV" ] || UV="$STUDIO/tools/uv/uv.exe"
  fi
  if [ -x "$PY" ]; then echo "the Python environment is already here, kept as it is"
  else "$UV" venv --python "${PYVER:-3.12}" "$STUDIO/.venv" || { echo "PROBLEM Python did not install"; exit 1; }; fi
  "$UV" pip install -q yt-dlp av==18.1.0 pillow==11.3.0 certifi==2026.7.22 > "$STUDIO/pip-base.log" 2>&1 \
    || { tail -5 "$STUDIO/pip-base.log"; echo "PROBLEM the small tools did not install"; exit 1; }
  echo "BASE READY"
fi

if [ "$1" = "update" ]; then
  "$UV" pip install -q --upgrade yt-dlp > "$STUDIO/pip-update.log" 2>&1 || { tail -3 "$STUDIO/pip-update.log"; echo "PROBLEM yt-dlp did not update"; exit 1; }
  echo "UPDATED yt-dlp"
fi

if [ "$1" = "libs" ]; then
  "$UV" pip install faster-whisper==1.2.1 av==18.1.0 certifi==2026.7.22 > "$STUDIO/pip.log" 2>&1 &
  PIP=$!
  while kill -0 $PIP 2>/dev/null; do echo "installing libraries, $(du -sm "$STUDIO/.venv" 2>/dev/null | cut -f1) MB so far"; sleep 15; done
  wait $PIP || { tail -5 "$STUDIO/pip.log"; echo "PROBLEM the libraries did not install"; exit 1; }
  "$UV" cache clean >/dev/null 2>&1
  echo "INSTALLED $(du -sh "$STUDIO" | cut -f1) in $STUDIO"
fi

if [ "$1" = "wait" ]; then
  LOG="$2"; MARK="$3"; T=0
  while [ $T -lt 90 ]; do
    if [ -f "$LOG" ]; then
      grep -q "$MARK" "$LOG" && { tail -1 "$LOG"; echo "READY"; exit 0; }
      grep -q -e "PROBLEM" -e "Traceback" "$LOG" && { tail -5 "$LOG"; echo "FAILED"; exit 2; }
      [ -n "$(find "$LOG" -mmin +5 2>/dev/null)" ] && { tail -1 "$LOG"; echo "STUCK nothing new in the log for 5 minutes"; exit 3; }
    fi
    sleep 5; T=$((T + 5))
  done
  tail -1 "$LOG" 2>/dev/null; echo "STILL RUNNING (run the same wait command again)"
fi
