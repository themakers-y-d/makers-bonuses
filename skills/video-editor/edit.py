#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""video-editor engine: cut, clean, caption and finish a talking-to-camera video, Hebrew first.

Always run it with the Python inside the studio folder (the same one the reel style builder uses):
  mac      ~/reel-studio/.venv/bin/python         edit.py <command> ...
  windows  ~/reel-studio/.venv/Scripts/python.exe edit.py <command> ...

Commands
  doctor                              check every tool; prints what is missing and the one line that fixes it
  model <ivrit|medium|small>          download a transcription model (large, run it in the background)
  info <video>                        duration, size, fps, orientation, audio, and the JOB FOLDER
  transcribe <video> [--model ivrit|medium|small] [--lang he] [--force]
                                      word timings to words.json, numbered lines to transcript.txt
  silences <video> [--db -30] [--min 0.6] [--pad 0.15]
                                      propose dead-air cuts, cuts-silence.json
  fillers <video>                     propose filler cuts (אממ, אהה, repeats, restarts; כאילו and רגע to confirm), cuts-fillers.json
  edl <video> [--keep "7,1-6,8-12"] [--remove "5,9,1:20-1:35,40.5-42"] [--use silence,fillers] [--fillers 1,4|all|none]
                                      the keep list in play order, edl.json; prints the length before and after
  style <video> [--from-css file] [--font name|file] [--color #hex] [--outline #hex|none] [--box #hex|none]
                [--size px] [--position pct] [--words n] [--reset]
                                      the caption look, style.json, and a preview image
  sheet <video> [--format ...] [--style file]       one frame of every kept part of the edit, captions in place
  frames <video> <t> [<t> ...] [--safe] [--format ...] [--style file]
                                      full-size frames at seconds of the edit (--safe marks what the app covers)
  render <video> [--format reel|wide|square|source] [--fit auto|crop|band|blur] [--captions burn|soft|none]
                 [--style file] [--music file [--duck]] [--lufs -14] [--no-edl] [--out file.mp4]
                                      the finished video, a new numbered file beside the original (long: background)
  verify <out.mp4>                    pass/fail table: plays, length, streams, loudness, captions, safe zone
  wait <log> <marker>                 wait up to 90 s for a background job: READY, STILL RUNNING, STUCK or FAILED
  open <path>                         open a file with the system viewer

Line numbers and times: in --keep and --remove a bare number or range ("5", "3-7") is a LINE of transcript.txt;
a time has a colon, a decimal point or an s ("1:20-1:35", "40.5-42", "40s-42s").
The original video is never changed, moved or overwritten. Every render is a new file.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

STUDIO = Path(os.environ.get("REEL_STUDIO", str(Path.home() / "reel-studio"))).expanduser()
os.environ.setdefault("HF_HOME", str(STUDIO / "models"))      # the same model cache as the reel style builder
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
IS_WIN = os.name == "nt"

MODEL_REVISIONS = {"ivrit-ai/whisper-large-v3-turbo-ct2": "72ad623a37947395efcc3933132353790e5a12f5"}
MODELS = {
    "ivrit": "ivrit-ai/whisper-large-v3-turbo-ct2",   # Hebrew fine-tune, about 1.6 GB
    "medium": "medium",                               # multilingual, about 1.5 GB
    "small": "small",                                 # multilingual, about 0.5 GB, faster, less accurate in Hebrew
}
PINS = {"numpy": "numpy==2.5.3", "PIL": "pillow==12.3.0", "cv2": "opencv-python-headless==4.14.0.94",
        "faster_whisper": "faster-whisper==1.2.1", "imageio_ffmpeg": "imageio-ffmpeg==0.6.0", "certifi": "certifi==2026.7.22"}

# Hebrew fonts, free (OFL), from one pinned commit of github.com/google/fonts, checked by sha256.
FONT_COMMIT = "23e54b51ddffbc7713c583748e3bd86f62b1fa4a"
FONTS = {
    "Assistant": ("Assistant.ttf", "ofl/assistant/Assistant%5Bwght%5D.ttf", "1c3b393884f8fb133a1b17f41d26178adae1050a4f86d7a429d1b5658c314fa3"),
    "Heebo": ("Heebo.ttf", "ofl/heebo/Heebo%5Bwght%5D.ttf", "18f930b583fa8fe6b40b2f8263b7ac6afbac07adc91a12467874e7467d3ace30"),
    "Rubik": ("Rubik.ttf", "ofl/rubik/Rubik%5Bwght%5D.ttf", "1b3a7437ba2af80e465e773ed60c5036d1ba6ace492d89046dbcf18fb31e4e88"),
    "Secular One": ("SecularOne.ttf", "ofl/secularone/SecularOne-Regular.ttf", "2f45092a521db5042887941edfef73178ed7c5ba7fdfc5b6f581d44aab7b0234"),
    "Varela Round": ("VarelaRound.ttf", "ofl/varelaround/VarelaRound-Regular.ttf", "e1e47eb66dbc2ddc106661338e712d9176c9e83c669a82fde155324823d03aa2"),
    "Noto Sans Hebrew": ("NotoSansHebrew.ttf", "ofl/notosanshebrew/NotoSansHebrew%5Bwdth,wght%5D.ttf", "7ef36a2c3593758cdb622e1bdef4f84523e92fbc3ccc667438dd80ff54c2de88"),
    "Frank Ruhl Libre": ("FrankRuhlLibre.ttf", "ofl/frankruhllibre/FrankRuhlLibre%5Bwght%5D.ttf", "f9bf26966681037aae894b031bd0dcf2c1bfdfa128dd0640cf276fe62a338a43"),
    "Suez One": ("SuezOne.ttf", "ofl/suezone/SuezOne-Regular.ttf", "3ef86844aad0cf9db7dcbda326f3d2f54cc4ccfe56db949e9e0c60a17031bd41"),
}

# The proven numbers (Orel, on real talking-head footage).
SIL_DB, SIL_MIN, SIL_PAD = -30.0, 0.6, 0.15   # silence threshold, shortest silence worth cutting, air kept around speech
MINSEG = 0.20                                 # a kept piece shorter than this is dropped
FILLER_PAD = 0.06                             # air shaved around a filler cut
LUFS_SOCIAL, LUFS_LONG, TRUE_PEAK = -14.0, -16.0, -1.5
MUSIC_UNDER_DUCKED, MUSIC_UNDER_STATIC = 7.0, 16.0   # LU the bed sits under the voice before ducking / with no ducking
DUCK = "threshold=0.02:ratio=6:attack=20:release=400"  # sidechaincompress: about 15 to 20 dB down while someone talks
MUSIC_FADE = 2.0
SR = 48000

FORMATS = {"reel": (1080, 1920), "wide": (1920, 1080), "square": (1080, 1080)}
# where text may sit, (x0, y0, x1, y1) as fractions of the frame (craft.md, safe zones)
SAFE = {"reel": (110 / 1080, 270 / 1920, 930 / 1080, 1540 / 1920), "wide": (0.05, 0.05, 0.95, 0.95),
        "square": (60 / 1080, 60 / 1080, 1020 / 1080, 1020 / 1080)}
CAP_BOTTOM = {"reel": 75.0, "wide": 91.0, "square": 89.0}        # bottom edge of the caption block, % of the height
CAP_WIDTH = {"reel": 780 / 1080, "wide": 0.72, "square": 0.80}  # widest caption line, fraction of the width
CAP_WORDS = {"reel": 3, "wide": 8, "square": 4}                 # words per caption

DEFAULT_STYLE = {
    "font": "Assistant", "weight": 800, "size": 78,
    "color": "#ffffff", "outline": "#111111", "outline_width": 5,
    "box": None, "box_opacity": 1.0, "box_radius": 14,
    "shadow": True,
    "position": None, "max_words": None, "max_lines": 2, "max_chars": 32,
    "note": "size and outline_width are pixels on a 1080-wide frame; position is the bottom edge of the captions in % of the height (empty = the safe default for the format)",
}


# ----------------------------------------------------------------------------- basics

def say(*a):
    print(*a, flush=True)


def die(msg, code=2):
    say("PROBLEM " + msg)
    sys.exit(code)


def write_text(p, s):
    """UTF-8, \\n newlines on every system, written to a temp file and renamed (never half a file)."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    os.replace(tmp, p)


def save_json(p, data):
    write_text(p, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except ValueError:
        say(f"NOTE {p} is not valid JSON, ignoring it")
        return default


def opt(a, name, default=None):
    if name in a:
        i = a.index(name)
        if i + 1 >= len(a) or a[i + 1].startswith("--"):
            die(f"{name} needs a value")
        return a[i + 1]
    return default


def fnum(a, name, default):
    v = opt(a, name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError:
        die(f"{name} needs a number, got {v}")


def path_arg(s):
    s = s.strip().strip('"').strip("'")
    if IS_WIN:
        m = re.match(r"^/([a-zA-Z])/(.*)$", s)          # /c/Users/... written for Git Bash
        if m:
            s = f"{m.group(1).upper()}:/{m.group(2)}"
    return Path(s).expanduser()


def video_arg(a, what="video"):
    if not a or a[0].startswith("--"):
        die(f"give the {what} path first, in double quotes")
    p = path_arg(a[0])
    if not p.is_file():
        die(f"no file at {p}. Write the full path in double quotes, without ~ inside the quotes.")
    return p.resolve()


def even(x):
    return max(2, int(round(x / 2.0)) * 2)


def fmt_t(t):
    t = round(max(0.0, float(t)), 1)
    m, s = divmod(t, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{int(h)}:{int(m):02d}:{s:04.1f}"
    return f"{int(m)}:{s:04.1f}"


def parse_t(x):
    x = x.strip().lower()
    if x.endswith("s"):
        x = x[:-1]
    v = 0.0
    for part in x.split(":"):
        v = v * 60 + float(part)
    return v


_FF = None


def ffmpeg_exe():
    global _FF
    if _FF:
        return _FF
    try:
        import imageio_ffmpeg
        _FF = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        _FF = shutil.which("ffmpeg")
    if not _FF:
        die("ffmpeg is missing. Install the libraries again (see doctor).")
    return _FF


def ff(*args):
    """Run ffmpeg, return the CompletedProcess with stderr as text."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", *[str(x) for x in args]]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def ff_bytes(*args):
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-v", "error", *[str(x) for x in args]]
    return subprocess.run(cmd, capture_output=True).stdout


_CAPS = {}


def ff_has(kind, name):
    """kind: filters, encoders, decoders. Cached."""
    if kind not in _CAPS:
        _CAPS[kind] = ff(f"-{kind}").stdout
    return re.search(rf"\s{re.escape(name)}\s", _CAPS[kind]) is not None


def filter_script_flag():
    v = ff("-version").stdout
    m = re.search(r"ffmpeg version n?(\d+)", v)
    return "-/filter_complex" if m and int(m.group(1)) >= 7 else "-filter_complex_script"


def free_name(p):
    """Never overwrite: returns p, or p-2, p-3... whichever does not exist yet."""
    p = Path(p)
    if not p.exists():
        return p
    i = 2
    while True:
        q = p.with_name(f"{p.stem}-{i}{p.suffix}")
        if not q.exists():
            return q
        i += 1


def ssl_ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def download(url, dest, sha256=None):
    import hashlib
    import urllib.request
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, context=ssl_ctx(), timeout=60) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    if sha256:
        h = hashlib.sha256(tmp.read_bytes()).hexdigest()
        if h != sha256:
            tmp.unlink(missing_ok=True)
            die(f"the downloaded {dest.name} does not match its checksum. Check the internet connection and run again.")
    os.replace(tmp, dest)


# ----------------------------------------------------------------------------- reading a video

def probe(video):
    p = ff("-i", video)
    err = p.stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        die(f"could not read the video: {video}. On a Mac, check that Claude Code (VS Code or Terminal) may access this folder: "
            "System Settings, Privacy & Security, Files and Folders. If the file is in iCloud Drive or OneDrive with a cloud "
            "icon, it is not on the computer yet: open it once (Mac) or right click, Always keep on this device (Windows).")
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    lines = err.splitlines()
    vline = aline = sline = None
    rot = 0.0
    for i, l in enumerate(lines):
        if " Video: " in l and "attached pic" not in l and vline is None:
            vline = l
            for l2 in lines[i + 1:i + 12]:
                if "Stream #" in l2:
                    break
                r = re.search(r"rotation of (-?[\d.]+)", l2) or re.search(r"rotate\s*:\s*(-?\d+)", l2)
                if r:
                    rot = float(r.group(1))
        elif " Audio: " in l and aline is None:
            aline = l
        elif " Subtitle: " in l and sline is None:
            sline = l
    w = h = 0
    fps = None
    vcodec = pix = None
    hdr = None
    if vline:
        v = re.search(r", (\d{2,5})x(\d{2,5})", vline)
        if v:
            w, h = int(v.group(1)), int(v.group(2))
        f = re.search(r"([\d.]+) fps", vline) or re.search(r"([\d.]+) tbr", vline)
        fps = float(f.group(1)) if f else None
        c = re.search(r"Video: (\w+)", vline)
        vcodec = c.group(1) if c else None
        px = re.search(r"Video: [^,]*, (\w+)", vline)
        pix = px.group(1) if px else None
        if "arib-std-b67" in vline:
            hdr = "HLG"
        elif "smpte2084" in vline:
            hdr = "PQ"
        if abs(abs(rot) - 90) < 1:
            w, h = h, w
    acodec = rate = None
    if aline:
        c = re.search(r"Audio: (\w+)", aline)
        acodec = c.group(1) if c else None
        r = re.search(r"(\d+) Hz", aline)
        rate = int(r.group(1)) if r else None
    orient = "vertical" if h > w * 1.05 else ("horizontal" if w > h * 1.05 else "square")
    return {"duration": round(dur, 3), "width": w, "height": h, "fps": fps, "vcodec": vcodec, "pix_fmt": pix,
            "hdr": hdr, "rotation": rot, "has_video": vline is not None and w > 0, "has_audio": aline is not None,
            "acodec": acodec, "audio_rate": rate, "has_subtitles": sline is not None, "orientation": orient,
            "bytes": Path(video).stat().st_size}


def choose_fps(fps):
    """Keep the source frame rate (30 stays 30, 60 stays 60). Only slow-motion rates above 60 come down to 30."""
    if not fps or fps <= 0:
        return 30.0, "30"
    if fps > 61:
        fps = 30.0
    for target, s, v in ((23.976, "24000/1001", 24000 / 1001), (29.97, "30000/1001", 30000 / 1001), (59.94, "60000/1001", 60000 / 1001)):
        if abs(fps - target) < 0.01:
            return v, s
    r = round(fps)
    if abs(fps - r) < 0.05:
        return float(r), str(r)
    return round(fps, 3), f"{fps:.3f}"


def safe_name(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip().rstrip(".")
    return s or "video"


def job_dir(video):
    """One working folder per source video in the studio. Same file, same folder; a different file with
    the same name gets its own folder, so nothing from one video leaks into another."""
    video = Path(video).resolve()
    st = video.stat()
    ident = {"source": str(video), "name": video.name, "bytes": st.st_size}
    base = STUDIO / "jobs" / safe_name(video.stem)
    for i in range(1, 1000):
        d = base if i == 1 else base.with_name(f"{base.name}-{i}")
        sj = d / "source.json"
        if not d.exists():
            d.mkdir(parents=True)
            save_json(sj, ident)
            return d
        cur = load_json(sj)
        if cur is None:                     # a folder the reel style builder made for this name: adopt it
            save_json(sj, ident)
            return d
        if cur.get("bytes") == st.st_size and (cur.get("source") == str(video) or cur.get("name") == video.name):
            if cur.get("source") != str(video):
                save_json(sj, ident)        # the same file, moved
            return d
    die("too many job folders with this name")


def load_words(jd, need=True):
    data = load_json(jd / "words.json")
    if not data or not data.get("words"):
        if need:
            die("there is no transcript for this video yet. Run transcribe first.")
        return None
    words = [w for w in data["words"] if str(w.get("w", "")).strip()]
    for w in words:
        w["s"], w["e"] = float(w["s"]), float(w["e"])
        if w["e"] < w["s"]:
            w["e"] = w["s"]
    data["words"] = words
    if not data.get("lines") or "n" not in data["lines"][0] or "w0" not in data["lines"][0]:
        data["lines"] = make_lines(words)
    return data


def settings(jd):
    return load_json(jd / "settings.json", {}) or {}


# ----------------------------------------------------------------------------- Hebrew text

def _cls(ch):
    o = ord(ch)
    if 0x0590 <= o <= 0x05FF or 0xFB1D <= o <= 0xFB4F:
        return "R"
    if unicodedata.combining(ch):
        return "M"
    if ch.isdigit():
        return "N"
    if ch.isalpha():
        return "L"
    return "O"


MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<", "«": "»", "»": "«"}
NUM_INNER = set(".,:/-")            # 3.5  1,000  10:30  1/2  10-20
NUM_AFFIX = set("%$₪€£°#+")         # 100%  ₪50  +972
LTR_INNER = set(" -'._&/+:@")        # Word Press, e-mail, Node.js, Q&A, GPT-4


def bidi_visual(s):
    """A logical Hebrew line to left-to-right drawing order, for a right-to-left line.

    Pillow here draws without a bidi engine, so the line is reordered here, following the Unicode
    bidi rules that matter for captions: Hebrew runs right to left; English words and numbers keep
    their own order (GPT-4, 3.5, 10:30, 100%); punctuation between two Hebrew words, or at the edge
    of the line, belongs to the Hebrew (a question mark at the end shows on the left); brackets are
    mirrored; niqqud stays on its letter.
    """
    s = s.strip()
    if not s:
        return s
    # 1. classify, attaching combining marks to the character before them
    units = []
    for ch in s:
        c = _cls(ch)
        if c == "M" and units:
            units[-1][0] += ch
        else:
            units.append([ch, "R" if c == "M" else c])
    n = len(units)
    cl = [u[1] for u in units]
    # 2. numbers swallow their separators and affixes
    for i in range(n):
        if cl[i] == "O":
            ch = units[i][0]
            if ch in NUM_INNER and 0 < i < n - 1 and cl[i - 1] == "N" and cl[i + 1] == "N":
                cl[i] = "N"
    changed = True
    while changed:
        changed = False
        for i in range(n):
            if cl[i] == "O" and units[i][0] in NUM_AFFIX:
                if (i > 0 and cl[i - 1] == "N") or (i < n - 1 and cl[i + 1] == "N"):
                    cl[i] = "N"
                    changed = True
    # 3. a number after English (GPT 4, iPhone 15) is part of the English run
    last_strong = "R"
    for i in range(n):
        if cl[i] in ("L", "R"):
            last_strong = cl[i]
        elif cl[i] == "N" and last_strong == "L":
            cl[i] = "L"
    # 4. neutrals: between two runs of the same direction they take it; otherwise they are Hebrew
    i = 0
    while i < n:
        if cl[i] != "O":
            i += 1
            continue
        j = i
        while j < n and cl[j] == "O":
            j += 1
        before = cl[i - 1] if i > 0 else "R"
        after = cl[j] if j < n else "R"
        b = "R" if before == "N" else before
        a2 = "R" if after == "N" else after
        txt = "".join(u[0] for u in units[i:j])
        if b == "L" and a2 == "L" and all(c in LTR_INNER for c in txt):
            d = "L"
        elif b == a2:
            d = b
        else:
            d = "R"
        for k in range(i, j):
            cl[k] = d
        i = j
    # 5. runs: R at level 1, L and N at level 2; reverse the line, keep level-2 runs in their order
    runs = []
    for u, c in zip(units, cl):
        lvl = 1 if c == "R" else 2
        if runs and runs[-1][0] == lvl:
            runs[-1][1].append(u[0])
        else:
            runs.append([lvl, [u[0]]])
    out = []
    for lvl, chars in reversed(runs):
        if lvl == 2:
            out.append("".join(chars))
        else:
            out.append("".join(MIRROR.get(ch, ch) for ch in reversed(chars)))
    return "".join(out)


def norm_word(w):
    s = "".join(ch for ch in str(w) if not unicodedata.category(ch).startswith("P"))
    return s.strip().lower()


def ends_sentence(w):
    return str(w).rstrip().endswith((".", "?", "!", "…"))


# ----------------------------------------------------------------------------- fonts and style

_font_cache = {}


def font_file(name):
    if not name:
        name = "Assistant"
    if name in FONTS:
        fname, rel, sha = FONTS[name]
        dest = STUDIO / "fonts" / fname
        if not dest.exists():
            say(f"downloading the {name} font (free Google font, OFL license)")
            download(f"https://github.com/google/fonts/raw/{FONT_COMMIT}/{rel}", dest, sha)
        return dest
    p = STUDIO / "fonts" / name
    if p.is_file():
        return p
    p = path_arg(name)
    if p.is_file():
        return p
    die(f"unknown font {name}. Use one of: {', '.join(FONTS)}, or the path of a .ttf or .otf file")


def font(style, px):
    from PIL import ImageFont
    path = font_file(style.get("font"))
    weight = int(style.get("weight", 800))
    key = (str(path), int(px), weight)
    if key in _font_cache:
        return _font_cache[key]
    f = ImageFont.truetype(str(path), int(px), layout_engine=ImageFont.Layout.BASIC)
    try:
        axes = f.get_variation_axes()
        vals = []
        for ax in axes:
            nm = ax.get("name", b"")
            nm = nm.decode("latin-1", "ignore") if isinstance(nm, bytes) else str(nm)
            if "eight" in nm.lower() or nm.lower() == "wght":
                vals.append(max(ax["minimum"], min(ax["maximum"], weight)))
            else:
                vals.append(ax.get("default", ax["minimum"]))
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    _font_cache[key] = f
    return f


def has_hebrew(path):
    from PIL import Image, ImageDraw, ImageFont
    try:
        f = ImageFont.truetype(str(path), 48, layout_engine=ImageFont.Layout.BASIC)
    except Exception:
        return False
    def ink(ch):
        im = Image.new("L", (80, 80), 0)
        ImageDraw.Draw(im).text((10, 10), ch, font=f, fill=255)
        return im.tobytes()
    a, missing = ink("ש"), ink("\u0378")
    return any(a) and a != missing


def hexrgb(h):
    h = str(h).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgbhex(c):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, round(v)))) for v in c[:3])


def lum(c):
    r = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c[:3]]
    return 0.2126 * r[0] + 0.7152 * r[1] + 0.0722 * r[2]


def contrast(c1, c2):
    l1, l2 = sorted((lum(c1), lum(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def load_style(path=None, jd=None):
    """The caption style: a given file, else the job's style.json, else the safe default."""
    st = dict(DEFAULT_STYLE)
    src = None
    if path:
        src = path_arg(path)
        if not src.is_file():
            die(f"no style file at {src}")
    elif jd and (jd / "style.json").is_file():
        src = jd / "style.json"
    if src:
        data = load_json(src, {})
        if isinstance(data, dict):
            st.update({k: v for k, v in data.items() if k in DEFAULT_STYLE})
    return st, src


def fmt_of(name, W, H):
    if name in FORMATS:
        return name
    return "reel" if H > W * 1.05 else ("wide" if W > H * 1.05 else "square")


def safe_rect(fmtname, W, H):
    x0, y0, x1, y1 = SAFE[fmt_of(fmtname, W, H)]
    return (round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H))


# ----------------------------------------------------------------------------- captions

def remap_words(words, segs):
    """Word times from the source onto the edited timeline, through the keep list (any order)."""
    out, off = [], 0.0
    for a, b in segs:
        for w in words:
            lo, hi = max(w["s"], a), min(w["e"], b)
            mid = (w["s"] + w["e"]) / 2
            if (a <= mid < b) or (hi - lo >= 0.08 and hi - lo >= 0.5 * (w["e"] - w["s"])):
                out.append({"w": w["w"], "s": round(max(lo, a) - a + off, 3), "e": round(max(hi, lo) - a + off, 3),
                            "line": w.get("line")})
        off += b - a
    return out


def clean_tail(t):
    t = t.rstrip()
    while t and t[-1] in ".,…،;":
        t = t[:-1].rstrip()
    return t


def text_width(style, px, s):
    return font(style, px).getlength(bidi_visual(s))


def wrap(words, style, px, maxpx, max_lines, max_chars):
    one = " ".join(words)
    if (text_width(style, px, one) <= maxpx and len(one) <= max_chars) or max_lines < 2 or len(words) < 2:
        return [one]
    best, best_pen = None, None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        w1, w2 = text_width(style, px, l1), text_width(style, px, l2)
        pen = (max(0, w1 - maxpx) + max(0, w2 - maxpx)) * 20 + abs(w1 - w2)
        pen += max(0, len(l1) - max_chars) * 200 + max(0, len(l2) - max_chars) * 200
        last1, first2 = norm_word(words[i - 1]), norm_word(words[i])
        if any(ch.isdigit() for ch in last1):
            pen += 5000           # never split a number from its unit
        if len(last1) <= 1:
            pen += 5000           # never strand a one-letter word at the end of a line
        if len(first2) <= 1 and i == len(words) - 1:
            pen += 2000
        if best_pen is None or pen < best_pen:
            best, best_pen = [l1, l2], pen
    return best


def build_chunks(words, style, fmtname, W, H, total):
    """Caption chunks on the edited timeline: [{'s','e','lines'}]."""
    scale = min(W, H) / 1080
    px = style["size"] * scale
    maxpx = CAP_WIDTH[fmt_of(fmtname, W, H)] * W
    maxw = int(style.get("max_words") or CAP_WORDS[fmt_of(fmtname, W, H)])
    max_lines = int(style.get("max_lines") or 2)
    max_chars = int(style.get("max_chars") or 32)
    chunks, cur = [], []

    def flush():
        if cur:
            chunks.append({"s": cur[0]["s"], "e": cur[-1]["e"], "words": [w["w"] for w in cur],
                           "line": cur[-1].get("line"), "clause": str(cur[-1]["w"]).rstrip().endswith((",", ";", ":"))})
            cur.clear()

    for w in words:
        if cur:
            gap = w["s"] - cur[-1]["e"]
            last = cur[-1]
            new_line = w.get("line") is not None and w.get("line") != last.get("line")
            clause = str(last["w"]).rstrip().endswith((",", ";", ":")) and len(cur) >= 2
            if (gap > 0.6 or len(cur) >= maxw or ends_sentence(last["w"]) or new_line or clause
                    or w["e"] - cur[0]["s"] > 3.2 or len(" ".join(x["w"] for x in cur + [w])) > max_chars * max_lines):
                flush()
        cur.append(w)
    flush()
    # nothing flickers: a caption shorter than half a second takes the next one in, if it fits and
    # belongs to the same sentence; across a sentence only when it would flash for under a third of a second
    i = 0
    while i < len(chunks) - 1:
        c, nx = chunks[i], chunks[i + 1]
        dur = nx["s"] - c["s"]
        same = c.get("line") == nx.get("line") and not c.get("clause")
        if (dur < 0.5 and same or dur < 0.32) and len(c["words"]) + len(nx["words"]) <= maxw + 2 \
                and not ends_sentence(c["words"][-1]):
            c["words"] += nx["words"]
            c["e"] = nx["e"]
            c["line"], c["clause"] = nx.get("line"), nx.get("clause")
            chunks.pop(i + 1)
        else:
            i += 1
    starts = []
    for i, c in enumerate(chunks):
        st0 = max(0.0, c["s"] - 0.05)
        if i == 0 and st0 < 0.6:
            st0 = 0.0               # the first frame already carries a caption
        if starts:
            st0 = max(st0, starts[-1] + 0.05)
        starts.append(st0)
    for i, c in enumerate(chunks):
        start = starts[i]
        nxt = starts[i + 1] if i + 1 < len(chunks) else total
        end = c["e"] + 0.3
        if nxt - end < 0.6:
            end = nxt
        c["s"], c["e"] = round(start, 3), round(max(min(end, nxt, total), min(start + 0.1, nxt)), 3)
        ws = list(c["words"])
        ws[-1] = clean_tail(ws[-1])
        ws = [x for x in ws if x.strip()]
        c["lines"] = wrap(ws, style, px, maxpx, max_lines, max_chars) if ws else []
    return [c for c in chunks if c["lines"]]


def draw_caption(lines, style, fmtname, W, H):
    """One caption as a full-frame transparent image (PIL RGBA), plus its box in frame pixels."""
    from PIL import Image, ImageDraw, ImageFilter
    SS = 2
    scale = min(W, H) / 1080
    px = style["size"] * scale
    maxpx = CAP_WIDTH[fmt_of(fmtname, W, H)] * W
    widest = max(text_width(style, px, l) for l in lines)
    if widest > maxpx:                                   # one long word: shrink this caption, never overflow
        px = max(px * 0.7, px * maxpx / widest)
    f = font(style, px * SS)
    vis = [bidi_visual(l) for l in lines]
    widths = [f.getlength(v) for v in vis]
    cap_h = -f.getbbox("שלום", anchor="ls")[1]
    desc = 0.24 * px * SS
    ow = int(round(float(style.get("outline_width") or 0) * scale * SS)) if style.get("outline") else 0
    boxed = bool(style.get("box"))
    padx, pady = (0.32 * px * SS, 0.16 * px * SS) if boxed else (ow, ow)
    gap = 0.10 * px * SS if boxed else 0.02 * px * SS
    line_h = cap_h + desc + 2 * pady
    block_h = len(lines) * line_h + (len(lines) - 1) * gap
    margin = int(12 * SS + ow)
    tw = int(max(widths) + 2 * padx + 2 * margin)
    th = int(block_h + 2 * margin)
    tile = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    col = hexrgb(style.get("color") or "#ffffff")
    out_col = hexrgb(style["outline"]) if style.get("outline") else None
    if style.get("shadow") and not boxed:
        sh = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for k, v in enumerate(vis):
            base = margin + k * (line_h + gap) + pady + cap_h
            x = (tw - widths[k]) / 2
            sd.text((x, base + 3 * SS * scale), v, font=f, fill=(0, 0, 0, 120), anchor="ls",
                    stroke_width=ow, stroke_fill=(0, 0, 0, 120))
        tile.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * SS * scale)))
    d = ImageDraw.Draw(tile)
    for k, v in enumerate(vis):
        top = margin + k * (line_h + gap)
        base = top + pady + cap_h
        x = (tw - widths[k]) / 2
        if boxed:
            bc = hexrgb(style["box"]) + (int(255 * float(style.get("box_opacity", 1.0))),)
            d.rounded_rectangle((x - padx, top, x + widths[k] + padx, top + line_h),
                                radius=float(style.get("box_radius", 14)) * scale * SS, fill=bc)
        kw = {}
        if out_col and ow > 0:
            kw = {"stroke_width": ow, "stroke_fill": out_col + (255,)}
        d.text((x, base), v, font=f, fill=col + (255,), anchor="ls", **kw)
    small = tile.resize((max(1, tw // SS), max(1, th // SS)), Image.LANCZOS)
    pos = style.get("position")
    bottom = (float(pos) if pos not in (None, "") else CAP_BOTTOM[fmt_of(fmtname, W, H)]) / 100 * H
    x0 = int(round(W / 2 - small.width / 2))
    y0 = int(round(bottom - small.height + margin / SS))
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frame.paste(small, (x0, y0))          # onto an empty frame a plain paste copies colour and alpha exactly
    m = margin / SS
    box = [max(0, x0 + m), max(0, y0 + m), min(W, x0 + small.width - m), min(H, y0 + small.height - m)]
    return frame, [round(v) for v in box]


# ----------------------------------------------------------------------------- the plan of an edit

class Plan:
    """Everything sheet, frames and render agree on: format, fit, keep list, captions."""

    def __init__(self, video, a, need_words=False):
        self.video = video
        self.info = probe(video)
        if not self.info["has_video"]:
            die("this file has no picture. The editor works on videos.")
        self.jd = job_dir(video)
        st = settings(self.jd)
        fmtname = opt(a, "--format") or st.get("format")
        if fmtname is None:
            fmtname = {"vertical": "reel", "horizontal": "wide", "square": "square"}[self.info["orientation"]]
        if fmtname not in ("reel", "wide", "square", "source"):
            die("--format is one of reel, wide, square, source")
        fit = opt(a, "--fit") or st.get("fit") or "auto"
        if fit not in ("auto", "crop", "band", "blur"):
            die("--fit is one of auto, crop, band, blur")
        style_arg = opt(a, "--style") or st.get("style")
        if style_arg and not path_arg(style_arg).is_file():
            if opt(a, "--style"):
                die(f"no style file at {style_arg}")
            style_arg = None
        self.style, self.style_src = load_style(style_arg, self.jd)
        remember = {}
        if opt(a, "--format"):
            remember["format"] = fmtname
        if opt(a, "--fit"):
            remember["fit"] = fit
        if opt(a, "--style"):
            remember["style"] = str(path_arg(style_arg).resolve())
        if remember:
            st.update(remember)
            save_json(self.jd / "settings.json", st)
        self.fmt, self.fit_req = fmtname, fit
        sw, sh = self.info["width"], self.info["height"]
        if fmtname == "source":
            if sh >= sw:
                W = min(1080, sw)
                H = sh * W / sw
            else:
                H = min(1080, sh)
                W = sw * H / sh
            self.W, self.H = even(W), even(H)
        else:
            self.W, self.H = FORMATS[fmtname]
        edl = None if "--no-edl" in a else load_json(self.jd / "edl.json")
        if edl and edl.get("keep"):
            self.segs = [(float(x), float(y)) for x, y in edl["keep"]]
            self.F, self.fstr = float(edl.get("fps") or 30), edl.get("fps_str") or "30"
            self.has_edl = True
        else:
            self.F, self.fstr = choose_fps(self.info["fps"])
            end = math.floor(self.info["duration"] * self.F) / self.F
            self.segs = [(0.0, end)]
            self.has_edl = False
        self.offsets, t = [], 0.0
        for a0, b0 in self.segs:
            self.offsets.append(t)
            t += b0 - a0
        self.total = t
        data = load_words(self.jd, need=need_words)
        self.words = data["words"] if data else None
        self.chunks = []
        self.fit = None

    def to_source(self, t):
        for (a0, b0), off in zip(self.segs, self.offsets):
            if off <= t < off + (b0 - a0):
                return a0 + (t - off)
        a0, b0 = self.segs[-1]
        return max(a0, b0 - 0.5 / self.F)

    def make_chunks(self):
        if self.words:
            self.chunks = build_chunks(remap_words(self.words, self.segs), self.style, self.fmt, self.W, self.H, self.total)
        return self.chunks

    def chunk_at(self, t):
        for c in self.chunks:
            if c["s"] <= t < c["e"]:
                return c
        return None

    # --- the picture
    def rotate_chain(self):
        """Only for render: the filters that stand an upright phone video up (frame grabs are turned by ffmpeg)."""
        r = round(self.info.get("rotation") or 0) % 360
        return {90: "transpose=cclock,", 270: "transpose=clock,", 180: "hflip,vflip,"}.get(r, "")

    def hdr_chain(self):
        hdr = self.info.get("hdr")
        if not hdr:
            return ""
        tin = "arib-std-b67" if hdr == "HLG" else "smpte2084"
        if ff_has("filters", "zscale") and ff_has("filters", "tonemap"):
            return (f"zscale=tin={tin}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
                    "zscale=p=bt709,tonemap=tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
        if ff_has("filters", "colorspace"):
            return "colorspace=all=bt709:iall=bt2020:itrc=bt2020-10:fast=1,"
        return ""

    def decide_fit(self, quiet=False):
        if self.fit:
            return self.fit
        sw, sh, W, H = self.info["width"], self.info["height"], self.W, self.H
        if self.fmt == "source":
            self.fit = {"mode": "scale"}
            return self.fit
        src_a, dst_a = sw / sh, W / H
        mode = self.fit_req
        cx, cy = 0.5, 0.5
        note = ""
        if mode in ("auto", "crop"):
            if abs(src_a - dst_a) / dst_a < 0.12:
                mode = "crop"
            else:
                faces = self.faces()
                if faces is None:
                    note = "the face finder is not available"
                    mode = "band" if mode == "auto" else "crop"
                else:
                    found = [f for f in faces if f]
                    multi = sum(1 for f in faces if f and len(f) > 1)
                    if len(found) >= max(2, 0.4 * len(faces)) and multi <= 0.25 * len(faces):
                        boxes = [max(f, key=lambda b: b[2] * b[3]) for f in found]
                        cxs = sorted(b[0] + b[2] / 2 for b in boxes)
                        cys = sorted(b[1] + b[3] / 2 for b in boxes)
                        fw = sorted(b[2] for b in boxes)[len(boxes) // 2]
                        fh = sorted(b[3] for b in boxes)[len(boxes) // 2]
                        k = max(W / sw, H / sh)
                        win_w, win_h = W / k / sw, H / k / sh       # crop window as a fraction of the source
                        # the face's centre must stay in the middle half of the crop, and the face must fit in it
                        if (cxs[-1] - cxs[0] <= win_w * 0.5 and cys[-1] - cys[0] <= win_h * 0.5
                                and fw <= win_w * 0.95 and fh <= win_h * 0.95):
                            cx, cy = (cxs[0] + cxs[-1]) / 2, (cys[0] + cys[-1]) / 2
                            mode = "crop"
                            note = "one person: cropped around the face"
                        else:
                            mode = "band" if mode == "auto" else "crop"
                            note = "the face moves wider than the crop window"
                    else:
                        if mode == "auto":
                            mode = "band"
                        note = "no single steady face (a stage, two people or a screen): the whole picture is kept"
        self.fit = {"mode": mode, "cx": round(cx, 4), "cy": round(cy, 4), "note": note}
        if not quiet and note:
            say(f"NOTE {note}")
        return self.fit

    def faces(self):
        """Face boxes (fractions of the source frame) on frames sampled across the kept parts, or None."""
        cache = self.jd / "faces.json"
        data = load_json(cache, {})
        key = json.dumps(self.segs)
        if data.get("key") == key:
            return data["faces"]
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        casc = cv2.CascadeClassifier(xml)
        if casc.empty():
            # on Windows opencv cannot open a path with non-ASCII letters (a Hebrew user folder): load it from memory
            fs = cv2.FileStorage(Path(xml).read_text(encoding="utf-8"), cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            casc = cv2.CascadeClassifier()
            casc.read(fs.getFirstTopLevelNode())
        if casc.empty():
            return None
        sw, sh = self.info["width"], self.info["height"]
        k = 640 / max(sw, sh)
        w, h = even(sw * k), even(sh * k)
        out = []
        n = 12
        for i in range(n):
            t = self.total * (i + 0.5) / n
            raw = ff_bytes("-ss", f"{self.to_source(t):.3f}", "-i", self.video, "-frames:v", "1",
                           "-vf", f"{self.hdr_chain()}scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-")
            if len(raw) < w * h:
                out.append([])
                continue
            g = np.frombuffer(raw[:w * h], np.uint8).reshape(h, w)
            fs = casc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(max(24, w // 20), max(24, w // 20)))
            out.append([[float(x / w), float(y / h), float(bw / w), float(bh / h)] for x, y, bw, bh in fs])
        save_json(cache, {"key": key, "faces": out})
        return out

    def fit_chain(self):
        """The filter that turns a source frame into a W x H frame of the format."""
        fit = self.decide_fit(quiet=True)
        sw, sh, W, H = self.info["width"], self.info["height"], self.W, self.H
        if fit["mode"] == "scale":
            return f"scale={W}:{H}:flags=bicubic,setsar=1"
        if fit["mode"] == "crop":
            k = max(W / sw, H / sh)
            w2, h2 = max(W, even(sw * k)), max(H, even(sh * k))
            x = int(min(max(fit["cx"] * w2 - W / 2, 0), w2 - W))
            y = int(min(max(fit["cy"] * h2 - H / 2, 0), h2 - H))
            return f"scale={w2}:{h2}:flags=bicubic,crop={W}:{H}:{x}:{y},setsar=1"
        if fit["mode"] == "band":
            return (f"scale={W}:{H}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=bicubic,"
                    f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x111111,setsar=1")
        bw, bh = even(W / 8), even(H / 8)
        return (f"split=2[bgs][fgs];[bgs]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
                f"gblur=sigma=5,scale={W}:{H}:flags=bilinear,eq=brightness=-0.07:saturation=0.85[bg];"
                f"[fgs]scale={W}:{H}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=bicubic[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")

    def frame(self, t, captions=True):
        """The frame of the edit at edited time t, as it will render (PIL RGB), with its caption."""
        import numpy as np
        from PIL import Image
        W, H = self.W, self.H
        raw = ff_bytes("-ss", f"{self.to_source(t):.3f}", "-i", self.video, "-frames:v", "1",
                       "-vf", f"{self.hdr_chain()}{self.fit_chain()},format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-")
        if len(raw) < W * H * 3:
            im = Image.new("RGB", (W, H), (0, 0, 0))
        else:
            im = Image.fromarray(np.frombuffer(raw[:W * H * 3], np.uint8).reshape(H, W, 3).copy())
        c = self.chunk_at(t) if captions else None
        if c:
            cap, _ = draw_caption(c["lines"], self.style, self.fmt, W, H)
            im = Image.alpha_composite(im.convert("RGBA"), cap).convert("RGB")
        return im


def draw_safe(im, fmtname):
    """Shade what the platform covers, and outline where text may sit."""
    from PIL import Image, ImageDraw
    W, H = im.size
    x0, y0, x1, y1 = safe_rect(fmtname, W, H)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    red = (255, 40, 60, 48)
    d.rectangle((0, 0, W, y0), fill=red)
    d.rectangle((0, y1, W, H), fill=red)
    d.rectangle((0, y0, x0, y1), fill=red)
    d.rectangle((x1, y0, W, y1), fill=red)
    d.rectangle((x0, y0, x1, y1), outline=(255, 40, 60, 220), width=max(2, W // 400))
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


# ----------------------------------------------------------------------------- commands: setup

def cmd_doctor(a):
    import importlib.util
    ok, fixes = True, []
    say(f"python   {sys.version.split()[0]}  {sys.executable}")
    say(f"engine   {Path(__file__).resolve()}")
    say(f"studio   {STUDIO}")
    if sys.version_info < (3, 10):
        ok = False
        say("MISSING  Python 3.10 or newer")
    uv = STUDIO / "tools" / "uv" / ("uv.exe" if IS_WIN else "uv")
    for mod, pin in PINS.items():
        if importlib.util.find_spec(mod):
            say(f"OK       {mod}")
        else:
            ok = False
            say(f"MISSING  {mod}")
            fixes.append(f'"{uv}" pip install --python "{sys.executable}" {pin}' if uv.exists()
                         else f'"{sys.executable}" -m pip install {pin}')
    try:
        exe = ffmpeg_exe()
        v = ff("-version").stdout.split("\n")[0]
        x264 = ff_has("encoders", "libx264")
        say(f"{'OK      ' if x264 else 'MISSING '} ffmpeg  {v[:40]}  x264={'yes' if x264 else 'NO'}")
        ok &= x264
        need = [("filters", n) for n in ("silencedetect", "loudnorm", "ebur128", "sidechaincompress", "amix", "afade",
                                         "overlay", "trim", "atrim", "concat", "scale", "crop", "pad", "fps")]
        need += [("encoders", "aac"), ("encoders", "mov_text"), ("decoders", "png"), ("decoders", "hevc"), ("decoders", "h264")]
        miss = [n for k, n in need if not ff_has(k, n)]
        if miss:
            ok = False
            say(f"MISSING  ffmpeg parts: {', '.join(miss)}")
            fixes.append(f'"{uv}" pip install --python "{sys.executable}" --reinstall {PINS["imageio_ffmpeg"]}')
        else:
            say("OK       ffmpeg parts for cutting, captions, loudness and music")
        hdr = ff_has("filters", "zscale") and ff_has("filters", "tonemap")
        say(f"{'OK      ' if hdr else 'NOTE    '} HDR phone video {'is tone mapped' if hdr else 'is converted roughly (no zscale in this ffmpeg)'}")
        if not exe:
            ok = False
    except SystemExit:
        ok = False
        fixes.append(f'"{uv}" pip install --python "{sys.executable}" {PINS["imageio_ffmpeg"]}')
    fpath = STUDIO / "fonts" / FONTS["Assistant"][0]
    say(f"{'OK      ' if fpath.exists() else 'LATER   '} Hebrew caption font" + ("" if fpath.exists() else "  (downloads by itself the first time, about 100 KB)"))
    mdir = STUDIO / "models"
    have = [k for k, v in MODELS.items() if mdir.exists() and any(mdir.glob(f"models--*{v.split('/')[-1]}"))]
    if have:
        say(f"OK       transcription model  {', '.join(have)}")
    else:
        ok = False
        say("MISSING  transcription model")
        fixes.append(f'"{sys.executable}" "{Path(__file__).resolve()}" model ivrit   (about 1.6 GB, run it in the background)')
    try:
        STUDIO.mkdir(parents=True, exist_ok=True)
        t = STUDIO / ".write-test"
        write_text(t, "ok\n")
        t.unlink()
    except Exception as e:
        ok = False
        say(f"PROBLEM  cannot write in {STUDIO}: {e}")
    free = shutil.disk_usage(STUDIO if STUDIO.exists() else Path.home()).free / 1e9
    say(f"disk     {free:.1f} GB free")
    if free < 3:
        say("NOTE     less than 3 GB free: a render of a long video may not fit")
    for f in fixes:
        say("FIX      " + f)
    say("ALL GOOD" if ok else "NOT READY")


def cmd_model(a):
    import threading
    name = a[0] if a else "ivrit"
    if name not in MODELS:
        die(f"unknown model {name}. Use one of {', '.join(MODELS)}")
    mdir = STUDIO / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    stop = []

    def watch():
        while not stop:
            size = sum(f.stat().st_size for f in mdir.rglob("*") if f.is_file()) / 1e9
            say(f"downloaded so far {size:.2f} GB")
            time.sleep(15)

    threading.Thread(target=watch, daemon=True).start()
    from faster_whisper.utils import download_model
    path = download_model(MODELS[name], cache_dir=str(mdir), revision=MODEL_REVISIONS.get(MODELS[name]))
    stop.append(1)
    say(f"MODEL READY {name} at {path}")


def cmd_info(a):
    video = video_arg(a)
    info = probe(video)
    jd = job_dir(video)
    save_json(jd / "info.json", info)
    say(f"file        {video.name}")
    say(f"length      {fmt_t(info['duration'])}  ({info['duration']:.2f} s)")
    if info["has_video"]:
        say(f"picture     {info['width']}x{info['height']}  {info['orientation']}  {info['fps'] or '?'} fps  {info['vcodec']}"
            + (f"  HDR ({info['hdr']})" if info["hdr"] else ""))
    else:
        say("picture     none")
    say(f"sound       {info['acodec']} {info['audio_rate']} Hz" if info["has_audio"] else "sound       none")
    say(f"size        {info['bytes'] / 1e6:.1f} MB")
    if info["orientation"] == "horizontal":
        say("NOTE landscape: for a vertical reel it is cropped around one face, or kept whole with a band above and below")
    if info["hdr"]:
        say("NOTE recorded in HDR: it is tone mapped to normal video in the render, check the colours on the sheet")
    if not info["has_audio"]:
        say("NOTE the video has no sound: no transcript, no silences and no captions from speech; cut it by time")
    if info["duration"] > 300:
        say("NOTE longer than five minutes: the long-form mode applies")
    if info["vcodec"] == "hevc" or (info["width"] * info["height"] > 1920 * 1080 * 1.1):
        say("NOTE HEVC or larger than 1080p: renders take longer; the output is H.264 at most 1080 wide")
    say(f"JOB FOLDER {jd}")


# ----------------------------------------------------------------------------- transcription

def make_lines(words):
    """Numbered lines (sentences or phrases) from word timings."""
    lines, cur = [], []

    def flush():
        if cur:
            i0, i1 = cur[0], cur[-1]
            lines.append({"n": len(lines) + 1, "start": round(words[i0]["s"], 2), "end": round(words[i1]["e"], 2),
                          "text": " ".join(words[i]["w"] for i in cur), "w0": i0, "w1": i1})
            cur.clear()

    for i, w in enumerate(words):
        if cur:
            last = words[cur[-1]]
            gap = w["s"] - last["e"]
            n = len(cur)
            new_seg = w.get("seg") is not None and w.get("seg") != last.get("seg")
            if (gap >= 0.7 or n >= 16 or w["e"] - words[cur[0]]["s"] > 9 or (ends_sentence(last["w"]) and n >= 3)
                    or (new_seg and n >= 4) or (str(last["w"]).rstrip().endswith((",", ";", ":")) and n >= 4)):
                flush()
        cur.append(i)
    flush()
    for L in lines:
        for i in range(L["w0"], L["w1"] + 1):
            words[i]["line"] = L["n"]
    return lines


def transcript_text(video, data):
    lines = data["lines"]
    out = [f"# {Path(video).name}. {len(lines)} lines, numbered. edl --keep and --remove take these numbers.", ""]
    for L in lines:
        out.append(f"{L['n']:3d}) [{fmt_t(L['start'])}-{fmt_t(L['end'])}] {L['text']}")
    return "\n".join(out) + "\n"


def cmd_transcribe(a):
    video = video_arg(a)
    name = opt(a, "--model", "ivrit")
    if name not in MODELS:
        die(f"unknown model {name}. Use one of {', '.join(MODELS)}")
    lang = opt(a, "--lang", "he")
    jd = job_dir(video)
    wj, tt = jd / "words.json", jd / "transcript.txt"
    if "--force" not in a:
        data = load_words(jd, need=False)
        if data:
            for L in data["lines"]:
                for i in range(L["w0"], L["w1"] + 1):
                    data["words"][i]["line"] = L["n"]
            save_json(wj, data)
            if not tt.exists():
                write_text(tt, transcript_text(video, data))
            say(f"reusing the existing transcript ({data.get('model', '?')} model); --force makes a new one")
            say(f"TRANSCRIPT {tt}")
            say(f"TRANSCRIBED {len(data['words'])} words in {len(data['lines'])} lines")
            return
    info = probe(video)
    if not info["has_audio"]:
        die("this video has no sound track, so there is nothing to transcribe. Cut it by time instead: edl --remove \"0:10-0:20\"")
    mdir = STUDIO / "models"
    if not any(mdir.glob(f"models--*{MODELS[name].split('/')[-1]}")):
        say(f"NOTE the {name} model is not on this computer yet; it downloads now (see the model command for progress)")
    dur = info["duration"]
    # long recordings in windows of about ten minutes, split in a pause: one long pass drifts and invents text
    bounds = [0.0]
    if dur > 720:
        sil = detect_silences(video, -35, 0.3, dur)
        t = 600.0
        while t < dur - 120:
            near = [((s + e) / 2) for s, e in sil if abs((s + e) / 2 - t) < 60]
            b = min(near, key=lambda x: abs(x - t)) if near else t
            bounds.append(b)
            t = b + 600
    bounds.append(dur)
    import numpy as np
    from faster_whisper import WhisperModel
    say(f"loading the {name} model (about a minute the first time)")
    model = WhisperModel(MODELS[name], device="cpu", compute_type="int8", download_root=str(mdir),
                         revision=MODEL_REVISIONS.get(MODELS[name]))
    say("transcribing, one line per sentence as it finishes")
    words, nseg = [], 0
    for wi in range(len(bounds) - 1):
        t0, t1 = bounds[wi], bounds[wi + 1]
        # the sound goes to the model as samples decoded by our own ffmpeg, never as a file path: faster-whisper's
        # own file reader depends on the PyAV version that happened to install, and breaks when it changes
        raw = ff_bytes("-ss", f"{t0:.3f}", "-i", video, "-t", f"{t1 - t0:.3f}", "-vn", "-ac", "1", "-ar", "16000",
                       "-f", "f32le", "-")
        if len(raw) < 16000 * 4 * 0.2:
            die("could not read the sound of the video")
        audio = np.frombuffer(raw[:len(raw) // 4 * 4], np.float32).copy()
        if len(bounds) > 2:
            say(f"part {wi + 1} of {len(bounds) - 1}, from {fmt_t(t0)}")
        segs, _ = model.transcribe(audio, language=None if lang == "auto" else lang, beam_size=5,
                                   word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
        for s in segs:
            say(f"[{fmt_t(s.start + t0)} - {fmt_t(s.end + t0)}] {s.text.strip()}")
            nseg += 1
            for k, w in enumerate(s.words or []):
                if not w.word.strip():
                    continue
                if k > 0 and words and not w.word[:1].isspace() and words[-1].get("seg") == nseg:
                    # a piece of the same word (פיצ + 'רים): join it, one word on screen
                    words[-1]["w"] += w.word.strip()
                    words[-1]["e"] = round(w.end + t0, 3)
                    words[-1]["p"] = round(min(words[-1]["p"], w.probability), 2)
                    continue
                words.append({"w": w.word.strip(), "s": round(w.start + t0, 3), "e": round(w.end + t0, 3),
                              "p": round(w.probability, 2), "seg": nseg})
    if not words:
        die("the model heard no speech. Check that the video has sound, or try --lang auto")
    lines = make_lines(words)
    data = {"model": name, "lang": lang, "source": str(video), "words": words, "lines": lines}
    if wj.exists():
        os.replace(wj, jd / "words.prev.json")
    save_json(wj, data)
    write_text(tt, transcript_text(video, data))
    say(f"TRANSCRIPT {tt}")
    say(f"TRANSCRIBED {len(words)} words in {len(lines)} lines, saved to {wj}")


# ----------------------------------------------------------------------------- silences and fillers

def detect_silences(video, db, mind, dur):
    p = ff("-i", video, "-vn", "-sn", "-dn", "-af", f"silencedetect=noise={db}dB:d={mind}", "-f", "null", "-")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+(?:e-?\d+)?)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+(?:e-?\d+)?)", p.stderr)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else dur
        out.append((max(0.0, s), min(dur, e)))
    return out


def merge(iv, gap=0.0):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def subtract(intervals, holes):
    holes = merge(holes)
    res = []
    for a, b in intervals:
        cur = a
        for ha, hb in holes:
            if hb <= cur or ha >= b:
                continue
            if ha > cur:
                res.append((cur, ha))
            cur = max(cur, hb)
            if cur >= b:
                break
        if cur < b:
            res.append((cur, b))
    return res


def line_of(words, t, before=True):
    best = None
    for w in words:
        if before and w["e"] <= t + 0.05:
            best = w.get("line")
        elif not before and w["s"] >= t - 0.05:
            return w.get("line")
    return best


def cmd_silences(a):
    video = video_arg(a)
    info = probe(video)
    jd = job_dir(video)
    if not info["has_audio"]:
        die("this video has no sound, so there is no dead air to find. Cut by time instead: edl --remove \"0:10-0:20\"")
    db, mind, pad = fnum(a, "--db", SIL_DB), fnum(a, "--min", SIL_MIN), fnum(a, "--pad", SIL_PAD)
    if db > 0:
        db = -db
    dur = info["duration"]
    data = load_words(jd, need=False)
    words = data["words"] if data else []
    guard = [(w["s"] - 0.05, w["e"] + 0.05) for w in words]
    cuts, guarded = [], 0
    for s, e in detect_silences(video, db, mind, dur):
        a0 = 0.0 if s <= 0.05 else s + pad
        b0 = dur if e >= dur - 0.05 else e - pad
        if b0 - a0 < 0.05:
            continue
        pieces = subtract([(a0, b0)], guard) if guard else [(a0, b0)]
        pieces = [(x, y) for x, y in pieces if y - x >= MINSEG]
        if guard and sum(y - x for x, y in pieces) < (b0 - a0) - 0.01:
            guarded += 1
        cuts.extend(pieces)
    items = []
    for i, (x, y) in enumerate(cuts, 1):
        items.append({"n": i, "a": round(x, 3), "b": round(y, 3), "after_line": line_of(words, x) if words else None,
                      "before_line": line_of(words, y, before=False) if words else None})
    saved = sum(c["b"] - c["a"] for c in items)
    save_json(jd / "cuts-silence.json", {"params": {"db": db, "min": mind, "pad": pad}, "source_duration": dur,
                                         "transcript_guard": bool(words), "cuts": items, "seconds": round(saved, 2)})
    say(f"SILENCES {len(items)} dead-air cuts, {saved:.1f} s of {dur:.1f} s "
        f"(quieter than {db:g} dB for at least {mind:g} s, {pad:g} s kept on each side)")
    for c in items[:60]:
        where = ""
        if c["after_line"] or c["before_line"]:
            where = f"  between line {c['after_line'] or '-'} and line {c['before_line'] or '-'}"
        say(f"  {c['n']:3d}) {fmt_t(c['a'])}-{fmt_t(c['b'])}  {c['b'] - c['a']:.1f} s{where}")
    if len(items) > 60:
        say(f"  ... and {len(items) - 60} more")
    if guarded:
        say(f"NOTE {guarded} silences were shortened because the transcript heard words in them")
    if not words:
        say("NOTE no transcript yet: transcribe first and run this again, so quiet words are protected")
    say(f"saved to {jd / 'cuts-silence.json'}. Apply with: edl <video> --use silence")
    say(f"Word starts clipped or a quiet speaker: --db {db - 5:g}. A noisy room where nothing was found: --db {db + 5:g}.")


HESITATIONS = set("אה אהה אההה אהההה אמ אממ אמם אממם אמממ אהם אהמ אהממ אהמם המ הממ המם עמ עממ עמם ממ מממ "
                  "uh uhh um umm erm hmm hm em ehm mm mmm".split())
DISCOURSE = {"כאילו": "often a filler, sometimes it carries meaning", "יעני": "often a filler, sometimes it carries meaning",
             "רגע": "often a restart marker, sometimes a real 'wait'", "בעצם": "often a filler, sometimes it carries meaning"}
# a doubled short function word is a stutter; a doubled content word is usually Hebrew on purpose (לאט לאט, מאוד מאוד)
STUTTER = set("אני אתה את זה זאת זו של על אז כי ש ה ו ב ל מ אם גם רק עם הוא היא אנחנו הם הן יש אין מה איך "
              "the a an i to and so it is".split())


def cmd_fillers(a):
    video = video_arg(a)
    jd = job_dir(video)
    data = load_words(jd)
    words = data["words"]
    dur = probe(video)["duration"]
    nw = [norm_word(w["w"]) for w in words]
    n = len(words)
    items, used = [], set()

    def window(i0, i1_next):
        prev_e = words[i0 - 1]["e"] if i0 > 0 else 0.0
        return max(prev_e, words[i0]["s"] - 0.03), max(words[i0]["s"], words[i1_next]["s"] - 0.02)

    i = 0
    while i < n:                                   # a phrase said twice: the first take goes
        hit = False
        for k in (5, 4, 3, 2):
            if i + 2 * k <= n and all(nw[i + j] and nw[i + j] == nw[i + k + j] for j in range(k)) \
                    and words[i + k]["s"] - words[i + k - 1]["e"] < 1.2:
                x, y = window(i, i + k)
                items.append({"a": x, "b": y, "i": i, "kind": "restart", "use": True,
                              "text": " ".join(words[j]["w"] for j in range(i, i + k)),
                              "why": f"the same {k} words said twice in a row; the first take goes"})
                used.update(range(i, i + k))
                i += k
                hit = True
                break
        if not hit:
            i += 1
    for i, w in enumerate(words):
        if i in used:
            continue
        t = nw[i]
        prev_e = words[i - 1]["e"] if i > 0 else 0.0
        next_s = words[i + 1]["s"] if i + 1 < n else dur
        if t in HESITATIONS:
            items.append({"a": max(prev_e, w["s"] - FILLER_PAD), "b": min(next_s, w["e"] + FILLER_PAD), "i": i,
                          "kind": "hesitation", "use": True, "text": w["w"], "why": "a hesitation sound"})
        elif t in DISCOURSE:
            items.append({"a": max(prev_e, w["s"] - FILLER_PAD), "b": min(next_s, w["e"] + FILLER_PAD), "i": i,
                          "kind": "maybe", "use": False, "text": w["w"], "why": DISCOURSE[t] + "; cut only if the owner agrees"})
        elif i + 1 < n and t and t == nw[i + 1] and words[i + 1]["s"] - w["e"] < 0.8:
            x, y = window(i, i + 1)
            stutter = t in STUTTER
            items.append({"a": x, "b": y, "i": i, "kind": "repeat", "use": stutter, "text": f"{w['w']} {words[i + 1]['w']}",
                          "why": "the same word twice in a row, a stutter; the first goes" if stutter
                          else "a doubled word, maybe on purpose (לאט לאט); ask"})
        elif (i + 1 < n and len(t) >= 2 and nw[i + 1].startswith(t) and len(nw[i + 1]) > len(t)
              and words[i + 1]["s"] - w["e"] < 0.6):
            x, y = window(i, i + 1)
            cut_off = str(w["w"]).rstrip().endswith(("-", "–", "—"))
            items.append({"a": x, "b": y, "i": i, "kind": "false start", "use": cut_off, "text": f"{w['w']} {words[i + 1]['w']}",
                          "why": "a word cut off and started again" if cut_off else "maybe a word started twice, ask"})
    items.sort(key=lambda c: c["a"])
    out = []
    for k, c in enumerate(items, 1):
        out.append({"n": k, "a": round(c["a"], 3), "b": round(c["b"], 3), "line": words[c["i"]].get("line"),
                    "text": c["text"], "kind": c["kind"], "use": c["use"], "why": c["why"]})
    save_json(jd / "cuts-fillers.json", {"cuts": out})
    sure = [c for c in out if c["use"]]
    say(f"FILLERS {len(out)} found: {len(sure)} marked cut ({sum(c['b'] - c['a'] for c in sure):.1f} s), "
        f"{len(out) - len(sure)} marked ask")
    for c in out:
        say(f"  {c['n']:3d}) line {c['line'] or '-':>3}  {fmt_t(c['a'])}-{fmt_t(c['b'])}  "
            f"{'cut' if c['use'] else 'ask'}  \"{c['text']}\"  {c['why']}")
    say(f"saved to {jd / 'cuts-fillers.json'}")
    say("Apply the ones marked cut: edl <video> --use fillers. Choose exactly: --fillers 1,4 (or all, or none).")
    say("NOTE the model often leaves sounds like אממ out of the text; the silence pass catches most of those")


# ----------------------------------------------------------------------------- the edit list

def parse_spec(spec, what):
    items = []
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        parts = [p.strip() for p in tok.split("-")]
        if len(parts) > 2 or not all(parts):
            die(f"cannot read '{tok}' in {what}. Lines: 5 or 3-7. Times: 1:20-1:35 or 40.5-42 or 40s-42s")
        is_time = any(c in tok for c in ":.sS")
        try:
            if is_time:
                if len(parts) != 2:
                    die(f"a time in {what} needs a start and an end, like 1:20-1:35")
                x, y = parse_t(parts[0]), parse_t(parts[1])
                if y <= x:
                    die(f"in '{tok}' the end comes before the start")
                items.append(("time", x, y))
            else:
                x = int(parts[0])
                y = int(parts[1]) if len(parts) == 2 else x
                items.append(("lines", x, y))
        except ValueError:
            die(f"cannot read '{tok}' in {what}")
    return items


def line_windows(lines, dur):
    """For every line: the window that keeps it, and the window that removes it with its pauses."""
    res = {}
    for i, L in enumerate(lines):
        s, e = L["start"], L["end"]
        prev_e = lines[i - 1]["end"] if i > 0 else None
        next_s = lines[i + 1]["start"] if i + 1 < len(lines) else None
        lead = 0.25 if prev_e is None else min(0.25, max(0.0, (s - prev_e) / 2))
        tail = 0.25 if next_s is None else min(0.25, max(0.0, (next_s - e) / 2))
        keep = (max(0.0, s - lead), min(dur, e + tail))
        rem = (0.0 if prev_e is None else prev_e + min(0.25, max(0.0, (s - prev_e) / 2)),
               dur if next_s is None else next_s - min(0.25, max(0.0, (next_s - e) / 2)))
        res[L["n"]] = {"keep": keep, "remove": rem, "text": L["text"]}
    return res


def cmd_edl(a):
    video = video_arg(a)
    info = probe(video)
    jd = job_dir(video)
    dur = info["duration"]
    F, fstr = choose_fps(info["fps"])
    data = load_words(jd, need=False)
    lines = data["lines"] if data else []
    lw = line_windows(lines, dur) if lines else {}
    notes = []

    def need_lines(n):
        if not lw:
            die("line numbers need a transcript. Run transcribe first, or give times like 1:20-1:35")
        if n not in lw:
            die(f"there is no line {n}; the transcript has lines 1 to {len(lw)}")

    keep_spec = opt(a, "--keep")
    if keep_spec:
        base = []
        for kind, x, y in parse_spec(keep_spec, "--keep"):
            if kind == "lines":
                step = 1 if y >= x else -1
                for n in range(x, y + step, step):
                    need_lines(n)
                ks = [lw[n]["keep"] for n in range(x, y + step, step)]
                if step == 1:
                    base.append((ks[0][0], ks[-1][1]))     # a range in order keeps the pauses between its lines
                else:
                    base.extend(ks)
                notes.append(f"keep lines {x}" + (f"-{y}" if y != x else ""))
            else:
                base.append((max(0.0, x), min(dur, y)))
                notes.append(f"keep {fmt_t(x)}-{fmt_t(y)}")
    else:
        base = [(0.0, dur)]
    removals, removed_lines = [], []
    rem_spec = opt(a, "--remove")
    if rem_spec:
        for kind, x, y in parse_spec(rem_spec, "--remove"):
            if kind == "lines":
                for n in range(min(x, y), max(x, y) + 1):
                    need_lines(n)
                    removals.append(lw[n]["remove"])
                    removed_lines.append(n)
            else:
                removals.append((x, y))
                notes.append(f"remove {fmt_t(x)}-{fmt_t(y)}")
    use = [u.strip() for u in (opt(a, "--use") or "").split(",") if u.strip()]
    for u in use:
        if u not in ("silence", "fillers"):
            die("--use takes silence, fillers or both: --use silence,fillers")
    fill_spec = opt(a, "--fillers")
    if fill_spec and "fillers" not in use:
        use.append("fillers")
    n_sil = n_fill = 0
    if "silence" in use:
        cs = load_json(jd / "cuts-silence.json")
        if not cs:
            die("no silence report yet. Run silences first")
        removals += [(c["a"], c["b"]) for c in cs["cuts"]]
        n_sil = len(cs["cuts"])
    if "fillers" in use:
        cf = load_json(jd / "cuts-fillers.json")
        if not cf:
            die("no filler report yet. Run fillers first")
        allc = cf["cuts"]
        if fill_spec in (None, ""):
            chosen = [c for c in allc if c.get("use")]
        elif fill_spec == "all":
            chosen = allc
        elif fill_spec == "none":
            chosen = []
        else:
            nums = set()
            for kind, x, y in parse_spec(fill_spec, "--fillers"):
                if kind != "lines":
                    die("--fillers takes the numbers from the filler report, like 1,4")
                nums.update(range(min(x, y), max(x, y) + 1))
            chosen = [c for c in allc if c["n"] in nums]
            bad = nums - {c["n"] for c in allc}
            if bad:
                die(f"the filler report has no item {sorted(bad)[0]}")
        removals += [(c["a"], c["b"]) for c in chosen]
        n_fill = len(chosen)
    keep = subtract(base, removals) if removals else list(base)
    # whole frames, so picture and sound cut at exactly the same moment
    end_max = math.floor(dur * F) / F
    snapped = []
    for x, y in keep:
        x2, y2 = round(x * F) / F, min(round(y * F) / F, end_max)
        if y2 - x2 < MINSEG:
            continue
        if snapped and 0 <= x2 - snapped[-1][1] <= 1.01 / F:
            snapped[-1] = (snapped[-1][0], y2)     # a gap of one frame or less is no cut
        else:
            snapped.append((x2, y2))
    if not snapped:
        die("this edit keeps nothing. Check the line numbers and times")
    total = sum(y - x for x, y in snapped)
    ej = jd / "edl.json"
    if ej.exists():
        os.replace(ej, jd / "edl.prev.json")
    save_json(ej, {"source": str(video), "source_duration": dur, "fps": F, "fps_str": fstr,
                   "keep": [[round(x, 6), round(y, 6)] for x, y in snapped], "duration": round(total, 3),
                   "made_from": {"keep": keep_spec, "remove": rem_spec, "use": use, "fillers": fill_spec}})
    say(f"EDL {len(snapped)} pieces kept, {dur:.1f} s -> {total:.1f} s ({dur - total:.1f} s cut)")
    for n_ in removed_lines:
        say(f"  removed line {n_}: {lw[n_]['text'][:70]}")
    for nt in notes:
        say(f"  {nt}")
    if n_sil:
        say(f"  {n_sil} silence cuts applied")
    if "fillers" in use:
        say(f"  {n_fill} filler cuts applied")
    order = [x for x, _ in snapped]
    if order != sorted(order):
        say("  the order changed: the pieces play in the order of --keep")
    for k, (x, y) in enumerate(snapped[:40], 1):
        say(f"    {k:3d}) {fmt_t(x)}-{fmt_t(y)}  {y - x:.1f} s")
    if len(snapped) > 40:
        say(f"    ... and {len(snapped) - 40} more pieces")
    say(f"saved to {ej}")


# ----------------------------------------------------------------------------- style

def parse_color(v):
    v = v.strip().lower()
    named = {"white": (255, 255, 255), "black": (0, 0, 0)}
    if v in named:
        return named[v]
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h[:3])
        return hexrgb(h[:6]) if len(h) >= 6 else None
    nums = lambda s: [x for x in re.split(r"[\s,/]+", s.strip()) if x]
    m = re.fullmatch(r"rgba?\((.*)\)", v)
    if m:
        p = nums(m.group(1))[:3]
        return tuple(float(x[:-1]) * 2.55 if x.endswith("%") else float(x) for x in p) if len(p) == 3 else None
    m = re.fullmatch(r"hsla?\((.*)\)", v)
    if m:
        import colorsys
        p = nums(m.group(1))[:3]
        if len(p) < 3:
            return None
        h = float(p[0].replace("deg", "")) / 360
        s, l = float(p[1].rstrip("%")) / 100, float(p[2].rstrip("%")) / 100
        return tuple(x * 255 for x in colorsys.hls_to_rgb(h % 1, l, s))
    m = re.fullmatch(r"oklch\((.*)\)", v)
    if m:
        p = nums(m.group(1))[:3]
        if len(p) < 3:
            return None
        L = float(p[0][:-1]) / 100 if p[0].endswith("%") else float(p[0])
        C = float(p[1][:-1]) * 0.004 if p[1].endswith("%") else float(p[1])
        hh = math.radians(float(p[2].replace("deg", "")))
        aa, bb = C * math.cos(hh), C * math.sin(hh)
        l_ = (L + 0.3963377774 * aa + 0.2158037573 * bb) ** 3
        m_ = (L - 0.1055613458 * aa - 0.0638541728 * bb) ** 3
        s_ = (L - 0.0894841775 * aa - 1.2914855480 * bb) ** 3
        lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        g = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0) ** (1 / 2.4) - 0.055
        return tuple(max(0, min(255, g(c) * 255)) for c in lin)
    return None


def css_vars(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = {}
    for block in re.findall(r":root[^{]*\{([^}]*)\}", text):
        for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);?", block):
            out[name] = val.strip()
    for _ in range(5):                                  # resolve var(--x)
        for k, v in out.items():
            out[k] = re.sub(r"var\((--[\w-]+)(?:\s*,\s*([^)]+))?\)", lambda m: out.get(m.group(1), m.group(2) or ""), v)
    return out


def style_from_css(path, st):
    p = path_arg(path)
    if not p.is_file():
        die(f"no CSS file at {p}")
    vs = css_vars(p.read_text(encoding="utf-8", errors="replace"))
    cols = {k: parse_color(v) for k, v in vs.items()}
    cols = {k: c for k, c in cols.items() if c}
    if not cols:
        say("NOTE no colours found in :root of that file; the safe default stays")
        return st, []
    import colorsys
    sat = lambda c: colorsys.rgb_to_hsv(*(x / 255 for x in c))[1]
    pick = lambda pat: [k for k in cols if re.search(pat, k)]
    inks = pick(r"ink|text|fg|foreground|dark|black|night|umbra|deep") or list(cols)
    ink_k = min(inks, key=lambda k: lum(cols[k]))
    ink = cols[ink_k] if lum(cols[ink_k]) < 0.2 else (17, 17, 17)
    brands = pick(r"primary|brand|accent|main|highlight|secondary") or [k for k in cols if sat(cols[k]) > 0.3]
    brand_k = max(brands, key=lambda k: sat(cols[k])) if brands else None
    why = []
    white = (255, 255, 255)
    if brand_k and contrast(white, cols[brand_k]) >= 4.5:
        st.update(box=rgbhex(cols[brand_k]), color="#ffffff", outline=None, shadow=False)
        why.append(f"white letters on a box of {brand_k} {rgbhex(cols[brand_k])} (contrast {contrast(white, cols[brand_k]):.1f})")
    elif brand_k and contrast(ink, cols[brand_k]) >= 4.5:
        st.update(box=rgbhex(cols[brand_k]), color=rgbhex(ink), outline=None, shadow=False)
        why.append(f"{ink_k} {rgbhex(ink)} letters on a box of {brand_k} {rgbhex(cols[brand_k])} (contrast {contrast(ink, cols[brand_k]):.1f})")
    else:
        st.update(box=None, color="#ffffff", outline=rgbhex(ink), shadow=True)
        why.append(f"white letters with an outline of {ink_k} {rgbhex(ink)}"
                   + (f"; {brand_k} is too light for letters to read on it" if brand_k else ""))
    fams = " ".join(v for k, v in vs.items() if "font" in k)
    for fam in FONTS:
        if fam.lower() in fams.lower():
            st["font"] = fam
            why.append(f"the brief's font {fam}, which has Hebrew letters")
            break
    else:
        if fams.strip():
            why.append("the brief's font is not one the engine can burn safely in Hebrew; the Hebrew font stays")
    return st, why


def cmd_style(a):
    video = video_arg(a)
    jd = job_dir(video)
    st, src = load_style(None if "--reset" in a else opt(a, "--style"), None if "--reset" in a else jd)
    why = []
    if opt(a, "--from-css"):
        st, why = style_from_css(opt(a, "--from-css"), st)
    fnt = opt(a, "--font")
    if fnt:
        if fnt in FONTS:
            st["font"] = fnt
        else:
            p = path_arg(fnt)
            if not p.is_file():
                die(f"no font {fnt}. Use one of: {', '.join(FONTS)}, or the path of a .ttf or .otf file")
            if not has_hebrew(p):
                die(f"{p.name} has no Hebrew letters, so it cannot carry Hebrew captions")
            dest = STUDIO / "fonts" / "custom" / safe_name(p.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            st["font"] = f"custom/{dest.name}"
    for flagname, key in (("--color", "color"), ("--outline", "outline"), ("--box", "box")):
        v = opt(a, flagname)
        if v is not None:
            if v.lower() in ("none", "no", "off"):
                st[key] = None
            else:
                c = parse_color(v)
                if not c:
                    die(f"{flagname} needs a colour like #ffffff")
                st[key] = rgbhex(c)
            if key == "box" and st["box"]:
                st["shadow"] = False
    for flagname, key, lo, hi in (("--size", "size", 30, 160), ("--position", "position", 20, 95),
                                  ("--words", "max_words", 1, 12), ("--weight", "weight", 300, 900)):
        v = opt(a, flagname)
        if v is not None:
            try:
                x = float(v)
            except ValueError:
                die(f"{flagname} needs a number")
            st[key] = int(x) if key in ("size", "max_words", "weight") else x
            if not lo <= x <= hi:
                die(f"{flagname} must be between {lo} and {hi}")
    font_file(st["font"])
    if not has_hebrew(font_file(st["font"])):
        die(f"the font {st['font']} has no Hebrew letters")
    sp = jd / "style.json"
    save_json(sp, st)
    for w in why:
        say(f"from the brief: {w}")
    preview = style_preview(video, jd, st, a)
    say(f"STYLE {sp}")
    say(f"PREVIEW {preview}")
    say("Look at the preview: every test line must read right to left, English and numbers in their place.")


def style_preview(video, jd, st, a):
    from PIL import Image, ImageDraw
    plan = Plan(video, [x for x in a if x not in ("--reset",)])
    plan.style = st
    chunks = plan.make_chunks()
    t = chunks[0]["s"] + 0.05 if chunks else plan.total * 0.3
    fr = plan.frame(t)
    W, H = plan.W, plan.H
    k = 960 / H
    left = fr.resize((max(1, int(W * k)), 960), Image.LANCZOS)
    tests = ["בלי WordPress ובלי Wix", "3 שעות ביום", "(בסוגריים) 100%", "שאלה? תשובה!", "גרסה GPT-4 עלתה ב-2025"]
    col = Image.new("RGBA", (900, 960), (60, 60, 64, 255))
    for i, s in enumerate(tests):
        cap, box = draw_caption([s], st, "reel", 1080, 1920)
        crop = cap.crop(cap.getbbox() or (0, 0, 1, 1))
        if crop.width > 860:
            crop = crop.resize((860, max(1, int(crop.height * 860 / crop.width))), Image.LANCZOS)
        col.alpha_composite(crop, dest=((900 - crop.width) // 2, 40 + i * 185 + max(0, (150 - crop.height) // 2)))
    col = col.convert("RGB")
    sheet = Image.new("RGB", (left.width + 900 + 20, 960), (30, 30, 30))
    sheet.paste(left, (0, 0))
    sheet.paste(col, (left.width + 20, 0))
    p = jd / "style-preview.png"
    sheet.save(p)
    return p


# ----------------------------------------------------------------------------- sheet and frames

def cmd_sheet(a):
    from PIL import Image, ImageDraw
    video = video_arg(a)
    plan = Plan(video, a)
    fit = plan.decide_fit()
    plan.make_chunks()
    segs = plan.segs
    n = min(24, max(8, len(segs)))
    ts = []
    if len(segs) >= n:
        idx = [int(i * len(segs) / n) for i in range(n)]
    else:
        idx = list(range(len(segs)))
    for k in idx:
        off, ln = plan.offsets[k], segs[k][1] - segs[k][0]
        inside = [c for c in plan.chunks if off <= c["s"] < off + ln]
        ts.append(min(off + ln - 0.5 / plan.F, (inside[0]["s"] + min(inside[0]["e"], off + ln)) / 2) if inside else off + ln / 2)
    while len(ts) < n:                               # few pieces: more frames from the longest gaps
        pts = sorted([0.0] + ts + [plan.total])
        g = max(range(len(pts) - 1), key=lambda i: pts[i + 1] - pts[i])
        ts.append((pts[g] + pts[g + 1]) / 2)
    ts = sorted(ts)
    tw = 270 if plan.H >= plan.W else 384
    th = int(tw * plan.H / plan.W)
    cols = 6 if plan.H >= plan.W else 4
    rows = math.ceil(len(ts) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(ts):
        fr = draw_safe(plan.frame(t), plan.fmt).resize((tw, th), Image.BILINEAR)
        x, y = (i % cols) * tw, (i // cols) * (th + 26)
        sheet.paste(fr, (x, y + 26))
        k = next((j for j, off in enumerate(plan.offsets) if off <= t < off + segs[j][1] - segs[j][0]), len(segs) - 1)
        d.text((x + 6, y + 7), f"{fmt_t(t)}  part {k + 1}", fill=(255, 255, 255))
    p = plan.jd / "sheet.png"
    sheet.save(p)
    say(f"format {plan.fmt} {plan.W}x{plan.H}, fit {fit['mode']}, {len(segs)} kept parts, {plan.total:.1f} s, "
        f"captions {'from the transcript' if plan.chunks else 'none (no transcript)'}, style {plan.style_src or 'default'}")
    say(f"SHEET {p}")
    say("Red shading is what the app covers; captions must sit inside the red frame.")


def cmd_frames(a):
    video = video_arg(a)
    ts = []
    for x in a[1:]:
        if x.startswith("--"):
            break
        try:
            ts.append(parse_t(x))
        except ValueError:
            die(f"cannot read the time {x}")
    if not ts:
        die("give one or more times in seconds of the edit, like: frames <video> 1.5 12 40")
    plan = Plan(video, a)
    plan.decide_fit()
    plan.make_chunks()
    outd = plan.jd / "frames"
    outd.mkdir(exist_ok=True)
    for t in ts:
        t = min(max(0.0, t), max(0.0, plan.total - 0.5 / plan.F))
        im = plan.frame(t)
        if "--safe" in a:
            im = draw_safe(im, plan.fmt)
        p = outd / f"e_{t:07.2f}.png"
        im.save(p)
        c = plan.chunk_at(t)
        say(f"FRAME {p}" + (f"  caption: {' / '.join(c['lines'])}" if c else ""))


# ----------------------------------------------------------------------------- sound

def loudness(path, extra=()):
    """Integrated loudness (LUFS) and true peak (dBTP), measured by ffmpeg's EBU R128 meter."""
    p = ff("-nostats", *extra, "-i", path, "-vn", "-filter_complex", "ebur128=peak=true", "-f", "null", "-").stderr
    tail = p[p.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    f = lambda m: float(m.group(1)) if m and m.group(1) != "-inf" else -99.0
    return f(i), f(tp)


def loudnorm_to(src, dst, target):
    ffx = ffmpeg_exe()
    p1 = ff("-i", src, "-af", f"loudnorm=I={target}:TP={TRUE_PEAK}:LRA=11:print_format=json", "-f", "null", "-").stderr
    try:
        m = json.loads(p1[p1.rfind("{"):p1.rfind("}") + 1])
        if "inf" in str(m["input_i"]) or float(m["input_i"]) < -70:
            raise ValueError
    except Exception:
        shutil.copyfile(src, dst)
        return False
    af = (f"loudnorm=I={target}:TP={TRUE_PEAK}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"aresample={SR}")
    r = subprocess.run([ffx, "-hide_banner", "-nostdin", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR),
                        "-c:a", "pcm_s16le", str(dst)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        die("loudness step failed: " + r.stderr.strip()[-300:])
    return True


def build_audio(plan, tmp, music, duck, target):
    """The edited sound, with the music bed and ducking, at the target loudness. Returns (wav or None, report lines)."""
    has_voice = plan.info["has_audio"]
    if not has_voice and not music:
        return None, ["no sound in the source and no music: the video is silent"]
    rep = []
    total = plan.total
    L = []
    if has_voice:
        lv, _ = loudness(plan.video)
        gv = max(-20.0, min(25.0, -16.0 - lv)) if lv > -70 else 0.0
        for i, (a0, b0) in enumerate(plan.segs):
            d = b0 - a0
            f = min(0.008, d / 4)
            L.append(f"[0:a]atrim=start={a0:.6f}:end={b0:.6f},asetpts=PTS-STARTPTS,"
                     f"aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"afade=t=in:d={f:.4f},afade=t=out:st={max(0.0, d - f):.6f}:d={f:.4f}[a{i}];")
        n = len(plan.segs)
        L.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,volume={gv:.2f}dB[voice];")
    inputs = ["-i", str(plan.video)]
    outs = []
    if music:
        lm, _ = loudness(music, ("-t", "180"))
        if lm < -70:
            die("the music file is silent or unreadable")
        under = MUSIC_UNDER_DUCKED if (duck and has_voice) else MUSIC_UNDER_STATIC
        gm = max(-60.0, min(20.0, (-16.0 - under) - lm)) if has_voice else 0.0
        mi = 1
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        L.append(f"[{mi}:a]aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo,volume={gm:.2f}dB,"
                 f"atrim=end={total:.6f},asetpts=PTS-STARTPTS[m0];")
        fade = f"afade=t=out:st={max(0.0, total - MUSIC_FADE):.3f}:d={MUSIC_FADE}"
        if has_voice:
            if duck:
                L.append(f"[voice]asplit=2[vk][vm];[m0][vk]sidechaincompress={DUCK}[md];")
            else:
                L.append("[voice]anull[vm];[m0]anull[md];")
            L.append(f"[md]{fade},asplit=2[mf][mo];[vm][mf]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]")
            outs = [("[mix]", tmp / "raw.wav"), ("[mo]", tmp / "music-only.wav")]
        else:
            L.append(f"[m0]{fade}[mix]")
            outs = [("[mix]", tmp / "raw.wav")]
    else:
        L[-1] = L[-1].replace("[voice];", "[mix]")
        outs = [("[mix]", tmp / "raw.wav")]
    fa = tmp / "audio-graph.txt"
    write_text(fa, "\n".join(L) + "\n")
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-v", "error", "-y", *inputs, filter_script_flag(), str(fa)]
    for label, path in outs:
        cmd += ["-map", label, "-c:a", "pcm_f32le", "-ar", str(SR), str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        die("the sound step failed: " + r.stderr.strip()[-400:])
    if music and has_voice:
        lvoice, _ = loudness(tmp / "raw.wav")
        lmus, _ = loudness(tmp / "music-only.wav")
        rep.append(f"music bed {lvoice - lmus:.1f} LU under the voice on average"
                   + (" (lower still while someone talks: ducking)" if duck else " (no ducking)"))
    final = tmp / "audio.wav"
    if not loudnorm_to(tmp / "raw.wav", final, target):
        rep.append("the sound is silent; loudness left as it is")
    return final, rep


# ----------------------------------------------------------------------------- render

def out_path(video, a, fmtname):
    o = opt(a, "--out")
    if o:
        p = path_arg(o)
        if p.suffix.lower() != ".mp4":
            p = p.with_suffix(".mp4")
        p = p.resolve() if p.parent.exists() else p
        if p.exists():
            q = free_name(p)
            say(f"NOTE {p.name} already exists and is never overwritten: writing {q.name}")
            p = q
        return p
    d = video.parent
    try:
        t = d / f".write-test-{os.getpid()}"
        t.write_bytes(b"")
        t.unlink()
    except Exception:
        d = STUDIO / "out"
        d.mkdir(parents=True, exist_ok=True)
        say(f"NOTE the folder of the video is read-only: the new version goes to {d}")
    stem = video.stem
    pat = re.compile(re.escape(stem) + r"-edit-v(\d+)\.mp4$")
    nums = [int(m.group(1)) for f in d.iterdir() if (m := pat.match(f.name))]
    return d / f"{stem}-edit-v{(max(nums) + 1) if nums else 1}.mp4"


def write_srt(path, chunks):
    def ts(t):
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    rlm = "\u200f"
    out = []
    for i, c in enumerate(chunks, 1):
        body = "\n".join((rlm + l) if any(_cls(ch) == "R" for ch in l) else l for l in c["lines"])
        out.append(f"{i}\n{ts(c['s'])} --> {ts(c['e'])}\n{body}\n")
    write_text(path, "\n".join(out))


def cmd_render(a):
    from PIL import Image
    video = video_arg(a)
    t_start = time.time()
    captions = opt(a, "--captions", "burn")
    if captions not in ("burn", "soft", "none"):
        die("--captions is one of burn, soft, none")
    music = opt(a, "--music")
    if music:
        music = path_arg(music)
        if not music.is_file():
            die(f"no music file at {music}")
        music = music.resolve()
    duck = "--duck" in a
    plan = Plan(video, a)
    if captions != "none" and not plan.words:
        if not plan.info["has_audio"]:
            say("NOTE the video has no sound, so there are no captions")
            captions = "none"
        else:
            die("captions come from the transcript, and there is none yet. Run transcribe first, or add --captions none")
    fit = plan.decide_fit()
    W, H = plan.W, plan.H
    lufs = fnum(a, "--lufs", LUFS_LONG if plan.total > 300 else LUFS_SOCIAL)
    out = out_path(video, a, plan.fmt)
    if out.resolve() == video.resolve():
        die("the output would be the original video. The original is never overwritten; choose another name.")
    jd = plan.jd
    for old in jd.glob("render-*"):          # work folders left by an interrupted render, after six hours
        try:
            if time.time() - old.stat().st_mtime > 6 * 3600:
                shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass
    tmp = jd / f"render-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    tmp.mkdir(parents=True)
    say(f"rendering {plan.total:.1f} s ({len(plan.segs)} pieces{'' if plan.has_edl else ', no edit list: the whole video'}) "
        f"as {plan.fmt} {W}x{H} at {plan.fstr} fps, fit {fit['mode']}, captions {captions}"
        + (f", music{' ducked' if duck else ''}" if music else ""))
    # 1. captions
    chunks = plan.make_chunks() if captions != "none" else []
    cap_list = None
    boxes = []
    if chunks:
        say(f"drawing {len(chunks)} captions")
        blank = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        blank.save(tmp / "blank.png")
        entries, t = [], 0.0
        for i, c in enumerate(chunks):
            im, box = draw_caption(c["lines"], plan.style, plan.fmt, W, H)
            boxes.append({"s": c["s"], "e": c["e"], "text": " / ".join(c["lines"]), "box": box})
            if captions == "burn":
                name = f"c{i:05d}.png"
                im.save(tmp / name, compress_level=3)
                if c["s"] - t > 0.0005:
                    entries.append(("blank.png", c["s"] - t))
                entries.append((name, c["e"] - c["s"]))
                t = c["e"]
        if captions == "burn":
            entries.append(("blank.png", max(0.5, plan.total - t + 1)))
            lines = ["ffconcat version 1.0"]
            for name, d in entries:
                lines += [f"file '{name}'", f"duration {d:.6f}"]
            lines.append("file 'blank.png'")
            cap_list = tmp / "captions.txt"
            write_text(cap_list, "\n".join(lines) + "\n")
    srt_tmp = None
    if chunks:
        srt_tmp = tmp / "captions.srt"
        write_srt(srt_tmp, chunks)
    # 2. sound
    say("building the sound: the cuts, " + ("the music, " if music else "") + f"loudness {lufs:g} LUFS")
    wav, rep = build_audio(plan, tmp, music, duck, lufs)
    for r_ in rep:
        say("  " + r_)
    # 3. picture
    n = len(plan.segs)
    half = 0.5 / plan.F
    G = [f"[0:v]{plan.rotate_chain()}{plan.hdr_chain()}fps={plan.fstr},split={n}" + "".join(f"[s{i}]" for i in range(n)) + ";" if n > 1
         else f"[0:v]{plan.rotate_chain()}{plan.hdr_chain()}fps={plan.fstr}[s0];"]
    for i, (a0, b0) in enumerate(plan.segs):
        G.append(f"[s{i}]trim=start={max(0.0, a0 - half):.6f}:end={b0 - half:.6f},setpts=PTS-STARTPTS[v{i}];")
    if n > 1:
        G.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[cat];")
    else:
        G.append("[v0]null[cat];")
    G.append(f"[cat]{plan.fit_chain()}[fit];")
    if cap_list:
        G.append("[1:v]format=rgba[cap];[fit][cap]overlay=0:0:eof_action=pass:format=auto,scale=out_range=tv,format=yuv420p[outv]")
    else:
        G.append("[fit]scale=out_range=tv,format=yuv420p[outv]")
    fv = tmp / "video-graph.txt"
    write_text(fv, "\n".join(G) + "\n")
    # a phone video filmed upright carries a rotation flag. A complex filtergraph does not turn the picture by
    # itself, and the flag would be copied onto the finished file: turn it here and drop the flag
    rot_in = ["-display_rotation:v:0", "0"] if plan.rotate_chain() else []
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-y", *rot_in, "-i", str(video)]
    idx = 1
    if cap_list:
        cmd += ["-f", "concat", "-safe", "0", "-i", str(cap_list)]
        idx += 1
    ai = si = None
    if wav:
        cmd += ["-i", str(wav)]
        ai, idx = idx, idx + 1
    if captions == "soft" and srt_tmp:
        cmd += ["-i", str(srt_tmp)]
        si, idx = idx, idx + 1
    cmd += [filter_script_flag(), str(fv), "-map", "[outv]"]
    if ai is not None:
        cmd += ["-map", f"{ai}:a", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR)]
    if si is not None:
        cmd += ["-map", f"{si}:s", "-c:s", "mov_text", "-metadata:s:s:0", "language=heb"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-r", plan.fstr, "-color_range", "tv", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart", "-metadata", "comment=video-editor", "-progress", "pipe:1", "-nostats",
            "-f", "mp4"]
    part = out.with_name(out.name + ".part")
    if part.exists():
        part.unlink()
    cmd.append(str(part))
    log_p = tmp / "encode.log"
    say(f"encoding the picture ({W}x{H})")
    with open(log_p, "w", encoding="utf-8", newline="\n") as log:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8", errors="replace")
        last, t0 = 0.0, time.time()
        for line in p.stdout:
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    tsec = int(line.split("=")[1]) / 1e6
                except ValueError:
                    continue
                if time.time() - last > 8:
                    last = time.time()
                    pct = min(99.0, 100 * tsec / max(plan.total, 0.1))
                    el = time.time() - t0
                    left = f"left about {el / max(pct, 1) * (100 - pct) / 60:.1f} min" if pct > 3 else "estimating time left"
                    say(f"render {pct:.0f}%  elapsed {el / 60:.1f} min  {left}")
        p.wait()
    if p.returncode != 0:
        tail = log_p.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-6:]
        part.unlink(missing_ok=True)
        die("the encoder failed: " + " | ".join(tail) + f" (full log {log_p})")
    got = probe(part)
    if not got["has_video"] or got["duration"] < plan.total - 1.0:
        part.unlink(missing_ok=True)
        die(f"the encoded file is incomplete ({got['duration']:.1f} s of {plan.total:.1f} s); render again")
    final = free_name(out)
    os.replace(part, final)
    srt_out = None
    if srt_tmp:
        srt_out = free_name(final.with_suffix(".srt"))
        shutil.copyfile(srt_tmp, srt_out)
    (jd / "renders").mkdir(exist_ok=True)
    save_json(jd / "renders" / f"{final.name}.json", {
        "out": str(final), "source": str(video), "format": plan.fmt, "W": W, "H": H, "fps": plan.F, "fps_str": plan.fstr,
        "duration": round(plan.total, 3), "segments": [[round(x, 6), round(y, 6)] for x, y in plan.segs],
        "captions": captions, "chunks": boxes, "safe": list(safe_rect(plan.fmt, W, H)), "style": plan.style,
        "lufs_target": lufs, "has_audio": wav is not None, "music": str(music) if music else None, "duck": duck,
        "fit": fit, "made": time.strftime("%Y-%m-%d %H:%M:%S")})
    shutil.rmtree(tmp, ignore_errors=True)
    say(f"took {(time.time() - t_start) / 60:.1f} min. The original is untouched: {video}")
    if srt_out:
        say(f"SUBTITLES {srt_out}")
    say(f"DONE {final}")


# ----------------------------------------------------------------------------- verify

def moov_before_mdat(p):
    order = []
    with open(p, "rb") as f:
        pos = 0
        size_total = os.path.getsize(p)
        while pos < size_total and len(order) < 50:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size, typ = int.from_bytes(hdr[:4], "big"), hdr[4:8]
            if size == 1:
                size = int.from_bytes(f.read(8), "big")
            order.append(typ)
            if size == 0:
                break
            pos += size
    return b"moov" in order and b"mdat" in order and order.index(b"moov") < order.index(b"mdat")


def find_sidecar(out):
    out = str(Path(out).resolve())
    for p in (STUDIO / "jobs").glob("*/renders/*.json"):
        d = load_json(p, {})
        if d.get("out") == out:
            return d, p
    return None, None


def cmd_verify(a):
    import numpy as np
    from PIL import Image, ImageDraw
    video = video_arg(a, "rendered video")
    info = probe(video)
    meta, mp = find_sidecar(video)
    rows, ok = [], True

    def row(name, res, detail):
        nonlocal ok
        rows.append((name, res, detail))
        if res == "FAIL":
            ok = False

    say("checking the delivered file itself: it opens, its length, its streams, loudness, captions")
    dec = ff("-v", "error", "-i", video, "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-")
    errs = [l for l in dec.stderr.splitlines() if l.strip()]
    row("plays", "PASS" if dec.returncode == 0 and not errs else "FAIL",
        "decoded to the end with no errors" if dec.returncode == 0 and not errs else (errs[:1] or ["decoder failed"])[0][:90])
    if meta:
        exp = meta["duration"]
        tol = max(0.1, 2.0 / float(meta.get("fps") or 30))
        row("length", "PASS" if abs(info["duration"] - exp) <= tol else "FAIL",
            f"{info['duration']:.2f} s, the edit is {exp:.2f} s")
    else:
        row("length", "WARN", f"{info['duration']:.2f} s (no render record found, so not compared with an edit)")
    p = ff("-i", video).stderr
    v_ok = info["vcodec"] == "h264" and info["pix_fmt"] == "yuv420p"
    size_ok = not meta or (info["width"], info["height"]) == (meta["W"], meta["H"])
    row("video", "PASS" if v_ok and size_ok else "FAIL",
        f"{info['vcodec']} {info['width']}x{info['height']} {info['pix_fmt']} {info['fps']} fps")
    want_audio = meta["has_audio"] if meta else True
    if info["has_audio"]:
        row("audio", "PASS" if info["acodec"] == "aac" and info["audio_rate"] == SR else "WARN",
            f"{info['acodec']} {info['audio_rate']} Hz")
        li, tp = loudness(video)
        target = float(meta["lufs_target"]) if meta else LUFS_SOCIAL
        res = "PASS" if abs(li - target) <= 1.0 else ("WARN" if abs(li - target) <= 2.0 else "FAIL")
        row("loudness", res, f"{li:.1f} LUFS (target {target:g})")
        row("peak", "PASS" if tp <= -1.0 else "FAIL", f"true peak {tp:.1f} dBTP (at most -1)")
    else:
        row("audio", "FAIL" if want_audio else "PASS", "no sound track" + ("" if want_audio else ", as the source had none"))
    row("faststart", "PASS" if moov_before_mdat(video) else "WARN",
        "starts playing before it fully downloads" if moov_before_mdat(video) else "the index is at the end of the file")
    outd = (Path(mp).parent.parent if mp else STUDIO / "verify") / "delivered" / safe_name(video.stem)
    outd.mkdir(parents=True, exist_ok=True)
    W, H = info["width"], info["height"]

    def grab(t):
        raw = ff_bytes("-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-")
        if len(raw) < W * H * 3:
            return None
        return Image.fromarray(np.frombuffer(raw[:W * H * 3], np.uint8).reshape(H, W, 3).copy())

    shots = []
    fmtname = meta["format"] if meta else fmt_of("", W, H)
    if meta and meta.get("captions") == "burn" and meta.get("chunks"):
        ch = meta["chunks"]
        pick = [ch[int(i * (len(ch) - 1) / 5)] for i in range(min(6, len(ch)))] if len(ch) > 1 else ch
        col = np.array(hexrgb(meta["style"].get("color") or "#ffffff"), np.float32)
        seen = 0
        for c in pick:
            t = (c["s"] + c["e"]) / 2
            im = grab(t)
            if im is None:
                continue
            x0, y0, x1, y1 = c["box"]
            reg = np.asarray(im, np.float32)[y0:y1, x0:x1]
            frac = float((np.linalg.norm(reg - col, axis=2) < 60).mean()) if reg.size else 0.0
            seen += frac >= 0.02
            shots.append((t, im, c["text"]))
        row("captions", "PASS" if pick and seen >= max(1, int(0.8 * len(pick))) else "FAIL",
            f"{seen} of {len(pick)} sampled captions found in the picture")
        sx0, sy0, sx1, sy1 = meta["safe"]
        outside = [c for c in ch if c["box"][0] < sx0 or c["box"][1] < sy0 or c["box"][2] > sx1 or c["box"][3] > sy1]
        row("safe zone", "PASS" if not outside else "FAIL",
            f"every caption inside x {sx0}-{sx1}, y {sy0}-{sy1}" if not outside
            else f"{len(outside)} captions reach where the app covers, first at {fmt_t(outside[0]['s'])}")
    elif meta and meta.get("captions") == "soft":
        row("captions", "PASS" if info["has_subtitles"] else "FAIL",
            "a Hebrew subtitle track the player can switch off" if info["has_subtitles"] else "no subtitle track")
    elif meta:
        row("captions", "PASS", "none, as asked")
    while len(shots) < 6:
        t = info["duration"] * (len(shots) + 0.5) / 6
        im = grab(t)
        if im is None:
            break
        shots.append((t, im, ""))
    tw = 270 if H >= W else 384
    th = int(tw * H / W)
    sheet = Image.new("RGB", (tw * min(6, len(shots)) or tw, (th + 26) * math.ceil(max(1, len(shots)) / 6)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, (t, im, txt) in enumerate(shots):
        im.save(outd / f"d_{t:07.2f}.png")
        x, y = (i % 6) * tw, (i // 6) * (th + 26)
        sheet.paste(draw_safe(im, fmtname).resize((tw, th)), (x, y + 26))
        d.text((x + 6, y + 7), fmt_t(t), fill=(255, 255, 255))
    sp = outd / "sheet.png"
    sheet.save(sp)
    say("")
    say(f"{'CHECK':<11}{'RESULT':<8}DETAIL")
    for name, res, detail in rows:
        say(f"{name:<11}{res:<8}{detail}")
    say("")
    say(f"DELIVERED FRAMES {sp}")
    say("FILE OK" if ok else "FILE HAS PROBLEMS")


# ----------------------------------------------------------------------------- waiting and opening

def cmd_wait(a):
    """Wait for a background job: returns within about 90 seconds, its latest line, then one word:
    READY when the marker appears, FAILED on a problem, STUCK when the log has not changed for 5 minutes,
    STILL RUNNING otherwise (run the same wait again)."""
    if len(a) < 2:
        die("wait <log> <marker>")
    log, marker = path_arg(a[0]), a[1]
    t0, last = time.time(), ""
    while time.time() - t0 < 90:
        if log.exists():
            txt = log.read_text(encoding="utf-8", errors="replace")
            lines = [l for l in txt.replace("\r", "\n").split("\n") if l.strip()]
            last = lines[-1] if lines else ""
            if marker in txt:
                say(last)
                say("READY")
                return
            if "Traceback" in txt or "PROBLEM" in txt:
                say("\n".join(lines[-5:]))
                say("FAILED")
                sys.exit(2)
            if time.time() - log.stat().st_mtime > 300:
                say(last)
                say("STUCK")
                sys.exit(3)
        time.sleep(5)
    if last:
        say(last)
    say("STILL RUNNING")


def cmd_open(a):
    if not a:
        die("open <path>")
    p = path_arg(a[0]).resolve()
    if not p.exists():
        die(f"nothing at {p}")
    if IS_WIN:
        os.startfile(str(p))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(p)])
    else:
        subprocess.run(["xdg-open", str(p)])
    say(f"OPENED {p}")


COMMANDS = {
    "doctor": cmd_doctor, "model": cmd_model, "info": cmd_info, "transcribe": cmd_transcribe, "silences": cmd_silences,
    "fillers": cmd_fillers, "edl": cmd_edl, "style": cmd_style, "sheet": cmd_sheet, "frames": cmd_frames,
    "render": cmd_render, "verify": cmd_verify, "wait": cmd_wait, "open": cmd_open,
}

if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
