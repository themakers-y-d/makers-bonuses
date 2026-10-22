#!/bin/bash
# The video editor's tools, shared with the reel style builder.
# base: uv and Python (about a minute). libs: the libraries (the long part).
# wait LOG MARK: returns within about 90 seconds with READY, STILL RUNNING, STUCK or FAILED.
STUDIO="$HOME/reel-studio"
mkdir -p "$STUDIO/tools" "$STUDIO/in" "$STUDIO/models" && cd "$STUDIO" || exit 1
export UV_PYTHON_INSTALL_DIR="$STUDIO/tools/python" UV_CACHE_DIR="$STUDIO/tools/cache" VIRTUAL_ENV="$STUDIO/.venv"
PY="$STUDIO/.venv/bin/python"; [ -x "$PY" ] || PY="$STUDIO/.venv/Scripts/python.exe"
if [ "$1" = "base" ]; then
  if [ ! -x tools/uv/uv ] && [ ! -x tools/uv/uv.exe ]; then
    case "$(uname -sm)" in
      "Darwin arm64")  UVPKG=uv-aarch64-apple-darwin.tar.gz ;;
      "Darwin x86_64") UVPKG=uv-x86_64-apple-darwin.tar.gz ;;
      MINGW*|MSYS*|CYGWIN*) UVPKG=uv-x86_64-pc-windows-msvc.zip ;;
      *) echo "PROBLEM unsupported computer $(uname -sm)"; exit 1 ;;
    esac
    case "$UVPKG" in
      uv-aarch64-apple-darwin.tar.gz) UVSHA=a9a8df1eedeb192f2e47e40e2faabfb387db4b850209118786d42f89dde3e0ba
        UVURL=https://github.com/astral-sh/uv/releases/download/0.12.19/uv-aarch64-apple-darwin.tar.gz ;;
      uv-x86_64-apple-darwin.tar.gz)  UVSHA=cb5fa57bafe68fc0fb94b17f06bee0b0b9a7feb94ccbd110445afa0696e39273
        UVURL=https://github.com/astral-sh/uv/releases/download/0.12.19/uv-x86_64-apple-darwin.tar.gz ;;
      uv-x86_64-pc-windows-msvc.zip)  UVSHA=6dbb02d79e419522f1c500f0adb1cddcff0cda7d59b0d66ea7f5e3b4a1b2f5f0
        UVURL=https://github.com/astral-sh/uv/releases/download/0.12.19/uv-x86_64-pc-windows-msvc.zip ;;
    esac
    curl -fsSL -o "tools/$UVPKG" "$UVURL" || { echo "PROBLEM no internet connection, or GitHub is blocked"; exit 1; }
    GOT=$( (shasum -a 256 "tools/$UVPKG" 2>/dev/null || sha256sum "tools/$UVPKG") | cut -d' ' -f1 )
    [ "$GOT" = "$UVSHA" ] || { echo "PROBLEM the downloaded file does not match its checksum, stopping"; rm -f "tools/$UVPKG"; exit 1; }
    mkdir -p tools/uv
    case "$UVPKG" in
      *.zip) if command -v unzip >/dev/null 2>&1; then unzip -oq "tools/$UVPKG" -d tools/uv; else powershell -NoProfile -Command "Expand-Archive -Force 'tools/$UVPKG' 'tools/uv'"; fi ;;
      *) tar -xzf "tools/$UVPKG" -C tools/uv --strip-components 1 ;;
    esac
  fi
  if [ -x "$PY" ]; then echo "the Python environment is already here, kept as it is"; else tools/uv/uv venv --python "${PYVER:-3.12}" "$STUDIO/.venv" || exit 1; fi
  echo "BASE READY"
fi
if [ "$1" = "libs" ]; then
  tools/uv/uv pip install numpy==2.5.3 pillow==12.3.0 opencv-python-headless==4.14.0.94 faster-whisper==1.2.1 av==18.1.0 imageio-ffmpeg==0.6.0 certifi==2026.7.22 > "$STUDIO/pip.log" 2>&1 &
  PIP=$!
  while kill -0 $PIP 2>/dev/null; do echo "installing libraries, $(du -sm "$STUDIO/.venv" 2>/dev/null | cut -f1) MB so far"; sleep 15; done
  wait $PIP || { tail -5 "$STUDIO/pip.log"; echo "PROBLEM the libraries did not install"; exit 1; }
  tools/uv/uv cache clean >/dev/null 2>&1
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
