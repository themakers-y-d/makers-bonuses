#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""style-maker kit: the tested plumbing for animation and sound over a talking-head reel.

Always run it with the Python inside the studio folder:
  mac      ~/reel-studio/.venv/bin/python        kit.py <command> ...
  windows  ~/reel-studio/.venv/Scripts/python.exe kit.py <command> ...

Commands
  doctor                         check that every tool is in place
  font [--hand]                  get the Hebrew font(s) and draw a test image
  model <ivrit|medium|small>     download a transcription model (large, run in background)
  info <video>                   duration, size, fps, audio
  sheet <video>                  12 frames with a percent ruler
  frames <video> <t> [<t> ...]   full frames at given seconds, with ruler and face box
  face <video> [--manual x0 y0 x1 y1]   find the face box, write face.json
  band <video> [--mode full|split|window] [--captions-top P] [--headline P0 P1]   the safe band, band.json
  palette <image>                5 colors from a logo, with roles and contrast
  transcribe <video> [--model ivrit|medium|small]      word timings, write words.json/words.txt
  strip <video> <from> <to> <y0%> <y1%> [--step 0.1]   caption strip to verify word timings
  scaffold <video>               write a starting scenes.py into the job folder
  sfx                            synthesize the sound library into the studio
  mix <video> <cues.json>        place sounds, add the bed, set loudness, write mix.wav
  render <video> --check t [t ...]   stills of the composite, with rule checks
  render <video> [--audio mix.wav] [--out file.mp4]  the full render (long, run in background)
  verify <video.mp4> [--at t ...]    check the delivered file and pull frames from it
  remux <video.mp4> <mix.wav>    replace only the sound of a rendered file (after a sound note)
  wait <log> <marker>            wait up to 90 s for a background job, print its latest line
  open <path>                    open a file with the system viewer

Every frame is a function of time only (no clock, no unseeded randomness).
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

W, H, FPS, SS = 1080, 1920, 30, 2          # output canvas, frame rate, supersampling for drawing
SR = 48000                                 # audio sample rate
STUDIO = Path(os.environ.get("REEL_STUDIO", Path.home() / "reel-studio"))
KIT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(STUDIO / "models"))       # keep every download inside the studio folder
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

MODEL_REVISIONS = {"ivrit-ai/whisper-large-v3-turbo-ct2": "72ad623a37947395efcc3933132353790e5a12f5"}
MODELS = {
    "ivrit": "ivrit-ai/whisper-large-v3-turbo-ct2",   # Hebrew fine-tune, about 1.6 GB
    "medium": "medium",                               # multilingual, about 1.5 GB
    "small": "small",                                 # multilingual, about 0.5 GB, faster, less accurate
}
FONT_URLS = {
    "main": "https://github.com/google/fonts/raw/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/ofl/assistant/Assistant%5Bwght%5D.ttf",
    "hand": "https://github.com/google/fonts/raw/23e54b51ddffbc7713c583748e3bd86f62b1fa4a/ofl/playpensanshebrew/PlaypenSansHebrew%5Bwght%5D.ttf",
}


# ----------------------------------------------------------------------------- basics

def say(*a):
    print(*a, flush=True)


def die(msg, code=2):
    say("PROBLEM " + msg)
    sys.exit(code)


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        p = shutil.which("ffmpeg")
        if p:
            return p
    die("ffmpeg not found. Run the install stage again.")


def job_dir(video):
    d = STUDIO / "jobs" / Path(video).stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ssl_ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def download(url, dest):
    import urllib.request
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, context=ssl_ctx(), timeout=60) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(dest)


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


# ----------------------------------------------------------------------------- easing (rule 11: exact 0 before, exact 1 after)

def clamp01(x):
    return 0.0 if x <= 0 else 1.0 if x >= 1 else float(x)


def seg(t, a, b):
    """Progress of t across [a, b]. Exactly 0 before a, exactly 1 after b."""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    return (t - a) / (b - a)


def ease_out_cubic(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in_cubic(x):
    x = clamp01(x)
    return x ** 3


def ease_in_out_cubic(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def expo_in(x):
    x = clamp01(x)
    return 0.0 if x == 0 else 1.0 if x == 1 else 2 ** (10 * x - 10)


def back(x, s=2.4):
    """Overshoot entrance. s=2.4 peaks about 18% above the final size."""
    x = clamp01(x)
    if x in (0.0, 1.0):
        return x
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x, dur=0.6, zeta=0.6, hz=2.2):
    """Damped spring over dur seconds. x is progress 0..1."""
    x = clamp01(x)
    if x in (0.0, 1.0):
        return x
    t = x * dur
    w = 2 * math.pi * hz
    return 1 - math.exp(-zeta * w * t) * math.cos(w * math.sqrt(1 - zeta ** 2) * t)


def bezier(x1, y1, x2, y2):
    """cubic-bezier(x1, y1, x2, y2) as a function of progress, like CSS."""
    def f(x):
        x = clamp01(x)
        if x in (0.0, 1.0):
            return x
        lo, hi = 0.0, 1.0
        for _ in range(40):
            u = (lo + hi) / 2
            bx = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u ** 2 * x2 + u ** 3
            if bx < x:
                lo = u
            else:
                hi = u
        u = (lo + hi) / 2
        return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3
    return f


def rand(seed, i=0):
    """Deterministic pseudo random in [0, 1) from two integers."""
    v = math.sin(seed * 12.9898 + i * 78.233) * 43758.5453
    return v - math.floor(v)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ----------------------------------------------------------------------------- Hebrew text

HEB = range(0x0590, 0x0600)
MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<"}


def _is_rtl_char(ch):
    return ord(ch) in HEB


def _is_ltr_char(ch):
    return ch.isascii() and ch.isalnum()


def visual(s):
    """Logical Hebrew string to left-to-right drawing order, for a right-to-left line.

    Pillow here draws without a bidi engine (no libraqm), so we reorder ourselves.
    Hebrew words are reversed, runs of Latin letters and digits keep their order,
    brackets are mirrored. Good for plain Hebrew without niqqud, mixed with English
    words and numbers. Always check the font test image once per machine.
    """
    tokens, cur, kind = [], "", None
    for ch in s:
        k = "ltr" if _is_ltr_char(ch) else ("rtl" if _is_rtl_char(ch) else "n")
        if k == "n" and ch in ".,%:-/'" and kind == "ltr":
            k = "ltr"          # 3.5, 100%, 10:30, e-mail stay inside the Latin/number run
        if kind is None or k == kind:
            cur += ch
        else:
            tokens.append((kind, cur))
            cur = ch
        kind = k
    if cur:
        tokens.append((kind, cur))
    # merge neutral runs that sit between two LTR runs into the LTR run (e.g. "Word Press")
    merged = []
    for i, (k, txt) in enumerate(tokens):
        if k == "n" and merged and merged[-1][0] == "ltr" and i + 1 < len(tokens) and tokens[i + 1][0] == "ltr" and txt.strip() == "":
            merged[-1] = ("ltr", merged[-1][1] + txt)
            continue
        if k == "ltr" and merged and merged[-1][0] == "ltr":
            merged[-1] = ("ltr", merged[-1][1] + txt)
            continue
        merged.append((k, txt))
    out = []
    for k, txt in reversed(merged):
        if k == "ltr":
            out.append(txt)
        else:
            out.append("".join(MIRROR.get(c, c) for c in reversed(txt)))
    return "".join(out)


_font_cache = {}


def font(size, weight=700, which="main"):
    from PIL import ImageFont
    key = (size, weight, which)
    if key in _font_cache:
        return _font_cache[key]
    path = STUDIO / "fonts" / ("Assistant.ttf" if which == "main" else "PlaypenSansHebrew.ttf")
    if not path.exists():
        die(f"font missing at {path}. Run: kit.py font" + (" --hand" if which == "hand" else ""))
    f = ImageFont.truetype(str(path), int(size), layout_engine=ImageFont.Layout.BASIC)
    try:
        axes = f.get_variation_axes()
        lo, hi = axes[0]["minimum"], axes[0]["maximum"]
        f.set_variation_by_axes([max(lo, min(hi, weight))])
    except Exception:
        pass
    _font_cache[key] = f
    return f


# ----------------------------------------------------------------------------- the drawing canvas

class Canvas:
    """Everything above the video. Coordinates are in the 1080x1920 output space.

    Drawing happens at 2x and is scaled down, so edges are smooth.
    Each element is drawn on its own small tile and blended, so alpha works.
    """

    def __init__(self):
        self.S = SS
        self._img = None       # created on the first drawing, so empty frames cost nothing
        self.dirty = False
        self.glow = False      # set c.glow = True for the dark glowing look (slower)

    @property
    def img(self):
        if self._img is None:
            from PIL import Image
            self._img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        return self._img

    # -- internals
    def _tile(self, x0, y0, x1, y1, pad=4):
        from PIL import Image, ImageDraw
        S = self.S
        X0, Y0 = int(math.floor(x0 * S)) - pad * S, int(math.floor(y0 * S)) - pad * S
        X1, Y1 = int(math.ceil(x1 * S)) + pad * S, int(math.ceil(y1 * S)) + pad * S
        tile = Image.new("RGBA", (max(1, X1 - X0), max(1, Y1 - Y0)), (0, 0, 0, 0))
        return tile, ImageDraw.Draw(tile), X0, Y0

    def _put(self, tile, X0, Y0, alpha):
        if alpha <= 0:
            return
        if alpha < 1:
            a = tile.getchannel("A").point(lambda v: int(v * alpha))
            tile.putalpha(a)
        # clip to canvas
        cx0, cy0 = max(0, X0), max(0, Y0)
        cx1, cy1 = min(self.img.width, X0 + tile.width), min(self.img.height, Y0 + tile.height)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        part = tile.crop((cx0 - X0, cy0 - Y0, cx1 - X0, cy1 - Y0))
        self.img.alpha_composite(part, dest=(cx0, cy0))
        self.dirty = True

    @staticmethod
    def _c(col, a=255):
        if isinstance(col, str):
            col = hexrgb(col)
        return tuple(col[:3]) + (a,)

    # -- primitives
    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0, radius=0, alpha=1.0):
        S = self.S
        tile, d, X0, Y0 = self._tile(x0, y0, x1, y1)
        box = (x0 * S - X0, y0 * S - Y0, x1 * S - X0, y1 * S - Y0)
        d.rounded_rectangle(box, radius=radius * S, fill=self._c(fill) if fill else None,
                            outline=self._c(outline) if outline else None, width=int(width * S))
        self._put(tile, X0, Y0, alpha)

    def card(self, x0, y0, x1, y1, fill, border=5, ink="#1a1a1a", radius=21, shadow=None,
             shadow_fill=None, scale=1.0, alpha=1.0):
        """A filled card. border=0 means no outline. shadow=(dx, dy) adds a block shadow of the same shape.
        scale grows or shrinks the card around its center (use it for entrances)."""
        if scale <= 0 or alpha <= 0:
            return
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = (x1 - x0) / 2 * scale, (y1 - y0) / 2 * scale
        x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh, cy + hh
        r, b = radius * scale, border * scale
        line = ink if border > 0 else None
        if shadow:
            dx, dy = shadow[0] * scale, shadow[1] * scale
            self.rect(x0 + dx, y0 + dy, x1 + dx, y1 + dy, fill=shadow_fill or ink, outline=line, width=b, radius=r, alpha=alpha)
        self.rect(x0, y0, x1, y1, fill=fill, outline=line, width=b, radius=r, alpha=alpha)

    def circle(self, cx, cy, r, fill=None, outline=None, width=0, alpha=1.0):
        if r <= 0:
            return
        S = self.S
        tile, d, X0, Y0 = self._tile(cx - r, cy - r, cx + r, cy + r)
        d.ellipse((cx * S - r * S - X0, cy * S - r * S - Y0, cx * S + r * S - X0, cy * S + r * S - Y0),
                  fill=self._c(fill) if fill else None, outline=self._c(outline) if outline else None,
                  width=int(width * S))
        self._put(tile, X0, Y0, alpha)

    def line(self, points, color, width=3, progress=1.0, alpha=1.0):
        """Polyline with round caps. progress 0..1 draws it on along its length."""
        progress = clamp01(progress)
        if progress <= 0 or len(points) < 2:
            return
        lens = [math.dist(points[i], points[i + 1]) for i in range(len(points) - 1)]
        total, want, pts = sum(lens), sum(lens) * progress, [points[0]]
        for i, L in enumerate(lens):
            if want >= L:
                pts.append(points[i + 1])
                want -= L
            else:
                if L > 0 and want > 0:
                    a, b = points[i], points[i + 1]
                    pts.append((a[0] + (b[0] - a[0]) * want / L, a[1] + (b[1] - a[1]) * want / L))
                break
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        S = self.S
        tile, d, X0, Y0 = self._tile(min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width)
        sp = [(x * S - X0, y * S - Y0) for x, y in pts]
        col = self._c(color)
        if len(sp) >= 2:
            d.line(sp, fill=col, width=int(width * S), joint="curve")
        rr = width * S / 2
        for x, y in (sp[0], sp[-1]):
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)
        self._put(tile, X0, Y0, alpha)

    def hand_ellipse(self, cx, cy, rx, ry, color, width=9, progress=1.0, turns=2.0, jitter=6, seed=1, alpha=1.0):
        """Marker circle drawn by hand: two slightly different turns, drawn on with progress."""
        n = int(90 * turns)
        pts = []
        for i in range(n + 1):
            a = -math.pi / 2 + 2 * math.pi * turns * i / n
            j = (rand(seed, i // 6) - 0.5) * 2 * jitter
            k = 1 + 0.04 * (i / n)
            pts.append((cx + (rx + j) * k * math.cos(a), cy + (ry + j) * k * math.sin(a)))
        self.line(pts, color, width, progress, alpha)

    def text(self, x, y, s, size, fill, weight=700, anchor="mm", stroke=0, stroke_fill=None,
             tracking=0, which="main", alpha=1.0, reveal=None, rotate=0, wipe=None):
        """Hebrew-safe text. s is in normal (logical) order. anchor like Pillow: 'mm', 'rm', 'lm', 'mt'...
        reveal=n shows only the first n characters in reading order (typing effect).
        rotate=degrees turns the text around its anchor point (positive is counter-clockwise).
        wipe=0..1 reveals the line from the right edge (reading direction), 1 = fully shown.
        Returns the (x0, y0, x1, y1) box in output space."""
        if reveal is not None:
            s = s[:max(0, int(reveal))]
        if not s or size * self.S < 2 or alpha <= 0:
            return (x, y, x, y)
        S = self.S
        f = font(size * S, weight, which)
        vs = visual(s)
        if tracking:
            widths = [f.getlength(ch) + tracking * S for ch in vs]
            tw = sum(widths) - tracking * S
        else:
            tw = f.getlength(vs)
        asc, desc = f.getmetrics()
        th = asc + desc
        ax = {"l": 0, "m": tw / 2, "r": tw}[anchor[0]]
        ay = {"t": 0, "m": th / 2, "b": th, "a": asc, "s": asc}.get(anchor[1], th / 2)
        X, Y = x * S - ax, y * S - ay
        pad = int(stroke * S) + 4 * S
        from PIL import Image, ImageDraw
        tile = Image.new("RGBA", (int(tw + 2 * pad) + 1, int(th + 2 * pad) + 1), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        kw = dict(font=f, fill=self._c(fill))
        if stroke:
            kw.update(stroke_width=int(stroke * S), stroke_fill=self._c(stroke_fill or "#1a1a1a"))
        if tracking:
            cx = pad
            for ch, wch in zip(vs, widths):
                d.text((cx, pad), ch, **kw)
                cx += wch
        else:
            d.text((pad, pad), vs, **kw)
        if wipe is not None:
            wipe = clamp01(wipe)
            if wipe <= 0:
                return ((X) / S, (Y) / S, (X + tw) / S, (Y + th) / S)
            cut = int(tile.width * (1 - wipe))
            if cut > 0:
                a = tile.getchannel("A")
                a.paste(0, (0, 0, cut, tile.height))
                tile.putalpha(a)
        if rotate:
            ox, oy = x * S - (X - pad), y * S - (Y - pad)       # anchor inside the tile
            big = Image.new("RGBA", (tile.width * 2 + 2 * int(abs(ox)), tile.height * 2 + 2 * int(abs(oy))), (0, 0, 0, 0))
            cx0, cy0 = big.width // 2, big.height // 2
            big.paste(tile, (int(cx0 - ox), int(cy0 - oy)))
            big = big.rotate(rotate, resample=Image.BICUBIC)
            self._put(big, int(x * S - cx0), int(y * S - cy0), alpha)
        else:
            self._put(tile, int(X) - pad, int(Y) - pad, alpha)
        return ((X) / S, (Y) / S, (X + tw) / S, (Y + th) / S)

    def text_width(self, s, size, weight=700, which="main"):
        return font(size * self.S, weight, which).getlength(visual(s)) / self.S

    def image(self, path, cx, cy, w, alpha=1.0, scale=1.0):
        from PIL import Image
        im = Image.open(path).convert("RGBA")
        w2 = max(1, int(w * scale * self.S))
        h2 = max(1, int(im.height * w2 / im.width))
        im = im.resize((w2, h2), Image.LANCZOS)
        self._put(im, int(cx * self.S - w2 / 2), int(cy * self.S - h2 / 2), alpha)

    def result(self):
        """RGBA numpy array at 1080x1920, or None if nothing was drawn."""
        if not self.dirty:
            return None
        import numpy as np
        from PIL import Image, ImageFilter
        im = self.img.resize((W, H), Image.BOX)
        if self.glow:
            # two blurred copies added on top: sigma 8 at 0.6 and sigma 60 at 0.5 (the big one at half size)
            base = np.asarray(im, dtype=np.float32)
            g1 = np.asarray(im.filter(ImageFilter.GaussianBlur(8)), dtype=np.float32)
            small = im.resize((W // 2, H // 2), Image.BOX).filter(ImageFilter.GaussianBlur(30))
            g2 = np.asarray(small.resize((W, H), Image.BILINEAR), dtype=np.float32)
            rgb = base[..., :3] * base[..., 3:4] / 255 + 0.6 * g1[..., :3] * g1[..., 3:4] / 255 + 0.5 * g2[..., :3] * g2[..., 3:4] / 255
            a = np.clip(base[..., 3] + 0.6 * g1[..., 3] + 0.5 * g2[..., 3], 0, 255)
            rgb = np.where(a[..., None] > 0, rgb * 255 / np.maximum(a[..., None], 1), 0)
            return np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8)
        return np.asarray(im, dtype=np.uint8)


# ----------------------------------------------------------------------------- video io

def vf_fit():
    return (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,"
            f"crop={W}:{H},setsar=1,format=rgb24")


def grab(video, t):
    """One composited-size frame (1080x1920 RGB numpy) at time t."""
    import numpy as np
    cmd = [ffmpeg_exe(), "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(video), "-frames:v", "1",
           "-vf", vf_fit(), "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    if len(raw) < W * H * 3:
        # past the end of the video (a closing that runs after the last word): use the last frame
        cmd[4] = f"{max(0, min(t, probe(video)['duration']) - 0.1):.3f}"
        raw = subprocess.run(cmd, capture_output=True).stdout
    if len(raw) < W * H * 3:
        return np.zeros((H, W, 3), np.uint8)
    return np.frombuffer(raw[:W * H * 3], np.uint8).reshape(H, W, 3).copy()


def probe(video):
    import re
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    err = p.stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if not m:
        die(f"could not read the video: {video}")
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    v = re.search(r"Stream #.*Video: .*?(\d{2,5})x(\d{2,5})", err)
    fps = re.search(r"([\d.]+) fps", err)
    rot = re.search(r"rotation of (-?[\d.]+)", err) or re.search(r"rotate\s*:\s*(-?\d+)", err)
    w, h = (int(v.group(1)), int(v.group(2))) if v else (0, 0)
    if rot and abs(abs(float(rot.group(1))) - 90) < 1:
        w, h = h, w
    return {
        "duration": round(dur, 3), "width": w, "height": h,
        "fps": float(fps.group(1)) if fps else None,
        "has_audio": "Audio:" in err,
        "aspect": round(w / h, 4) if h else None,
    }


def ruler(img, step=10, face=None):
    """Draw a percent ruler (and the forbidden face box) on a PIL RGB image."""
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    w, h = img.size
    try:
        lf = ImageFont.load_default(size=max(12, w // 36))
    except Exception:
        lf = None
    for p in range(step, 100, step):
        y = int(h * p / 100)
        d.line((0, y, w, y), fill=(255, 0, 180), width=1 if p % 10 else 2)
        d.text((4, y - (w // 30)), f"{p}%", fill=(255, 0, 180), font=lf)
    if face:
        k = w / W
        x0, y0, x1, y1 = [v * k for v in face]
        d.rectangle((x0, y0, x1, y1), outline=(255, 40, 40), width=3)
    return img


# ----------------------------------------------------------------------------- commands: setup

def cmd_doctor(a):
    ok = True
    say(f"python   {sys.version.split()[0]}  {sys.executable}")
    say(f"kit      {Path(__file__).resolve()}")
    say(f"studio   {STUDIO}")
    import importlib.util
    for mod in ("numpy", "PIL", "cv2", "faster_whisper", "imageio_ffmpeg", "certifi"):
        # find_spec, not import: cv2 and faster_whisper must never load in the same process
        if importlib.util.find_spec(mod):
            say(f"OK       {mod}")
        else:
            ok = False
            say(f"MISSING  {mod}")
    try:
        import cv2
        if not hasattr(cv2, "CascadeClassifier"):
            ok = False
            say("PROBLEM  opencv 5 has no face finder. Install opencv-python-headless<5")
    except Exception:
        pass
    try:
        ff = ffmpeg_exe()
        v = subprocess.run([ff, "-hide_banner", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        say(f"OK       ffmpeg  {v[:40]}  x264={'yes' if 'libx264' in enc else 'NO'}")
        ok &= "libx264" in enc
    except SystemExit:
        ok = False
    for which, name in (("main", "Assistant.ttf"), ("hand", "PlaypenSansHebrew.ttf")):
        p = STUDIO / "fonts" / name
        state = "OK      " if p.exists() else ("LATER   " if which == "main" else "OPTIONAL")
        say(f"{state} font {name}" + ("  (the font step downloads it)" if which == "main" else "  (only for the handwriting style)"))
    mdir = STUDIO / "models"
    have = [k for k, v in MODELS.items() if any(mdir.glob(f"models--*{v.split('/')[-1]}*"))] if mdir.exists() else []
    say(f"{'OK      ' if have else 'MISSING '} transcription model  {', '.join(have) or 'none yet'}")
    free = shutil.disk_usage(STUDIO if STUDIO.exists() else Path.home()).free / 1e9
    say(f"disk     {free:.1f} GB free")
    say("ALL GOOD" if ok and have else "NOT READY")
    if ok and not have:
        say("tools are in place; only the transcription model is missing (kit model ivrit)")


def cmd_font(a):
    from PIL import Image
    want = ["main"] + (["hand"] if "--hand" in a else [])
    for which in want:
        dest = STUDIO / "fonts" / ("Assistant.ttf" if which == "main" else "PlaypenSansHebrew.ttf")
        if not dest.exists():
            say(f"downloading {dest.name} (free Google font, OFL license)")
            download(FONT_URLS[which], dest)
        say(f"OK font {dest}")
    c = Canvas()
    c.rect(0, 0, W, 900, fill=(255, 251, 241))
    lines = ["שלום עולם", "3 שעות ביום", "בלי WordPress ובלי Wix", "(בסוגריים) 100%", "שאלה? תשובה!"]
    for i, s in enumerate(lines):
        c.text(W - 60, 110 + i * 150, s, 80, (26, 26, 26), 700, anchor="rm")
    if "hand" in want:
        c.text(W - 60, 850, "כתב יד בעברית", 70, (242, 108, 76), 500, anchor="rm", which="hand")
    out = STUDIO / "fonts" / "test.png"
    Image.fromarray(c.result()).crop((0, 0, W, 920)).save(out)
    say(f"TEST IMAGE {out}")
    say("Look at it. Each line must read correctly right to left:")
    for s in lines:
        say("   " + s)


def cmd_model(a):
    import threading
    name = a[0] if a else "ivrit"
    if name not in MODELS:
        die(f"unknown model {name}. Use one of {', '.join(MODELS)}")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    mdir = STUDIO / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    stop = False

    def watch():
        while not stop:
            size = sum(f.stat().st_size for f in mdir.rglob("*") if f.is_file()) / 1e9
            say(f"downloaded so far {size:.2f} GB")
            time.sleep(10)

    th = threading.Thread(target=watch, daemon=True)
    th.start()
    from faster_whisper.utils import download_model
    path = download_model(MODELS[name], cache_dir=str(mdir), revision=MODEL_REVISIONS.get(MODELS[name]))
    stop = True
    say(f"MODEL READY {name} at {path}")


# ----------------------------------------------------------------------------- commands: intake

def cmd_info(a):
    video = Path(a[0])
    info = probe(video)
    fit = "vertical 9:16" if info["aspect"] and abs(info["aspect"] - 9 / 16) < 0.02 else "NOT 9:16 (will be cropped to fill 1080x1920)"
    info["render"] = f"{W}x{H} @ {FPS}fps"
    info["note"] = fit
    save_json(job_dir(video) / "info.json", info)
    say(json.dumps(info, ensure_ascii=False))
    if info["width"] > 1080:
        say("NOTE source is larger than 1080x1920; frames are scaled down for speed and the output is 1080x1920.")
    if not info["has_audio"]:
        say("NOTE the video has no audio track.")
    if info["duration"] > 90:
        say("NOTE longer than 90 seconds: the first render will take longer than the usual estimate.")
    say(f"JOB FOLDER {job_dir(video)}")


def cmd_sheet(a):
    import numpy as np
    from PIL import Image, ImageDraw
    video = Path(a[0])
    info = probe(video)
    n, tw, th = 12, 270, 480
    ts = [0.3 + (info["duration"] - 0.6) * i / (n - 1) for i in range(n)]
    face = (load_json(job_dir(video) / "face.json") or {}).get("forbid")
    sheet = Image.new("RGB", (tw * 6, (th + 24) * 2), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(ts):
        fr = Image.fromarray(grab(video, t)).resize((tw, th), Image.BILINEAR)
        ruler(fr, 10, face)
        x, y = (i % 6) * tw, (i // 6) * (th + 24)
        sheet.paste(fr, (x, y + 24))
        d.text((x + 6, y + 6), f"{t:.1f}s", fill=(255, 255, 255))
    out = job_dir(video) / "sheet.png"
    sheet.save(out)
    say(f"SHEET {out}")
    say("Read it for: where the face is, burned-in captions (y range in %), a burned-in headline, hard cuts, screens or B-roll.")


def cmd_frames(a):
    from PIL import Image
    video, ts = Path(a[0]), [float(x) for x in a[1:]]
    face = (load_json(job_dir(video) / "face.json") or {}).get("forbid")
    outd = job_dir(video) / "frames"
    outd.mkdir(exist_ok=True)
    for t in ts:
        im = ruler(Image.fromarray(grab(video, t)), 5, face)
        p = outd / f"f_{t:07.2f}.png"
        im.save(p)
        say(f"FRAME {p}")


def cmd_face(a):
    import numpy as np
    import cv2
    video = Path(a[0])
    jd = job_dir(video)
    if "--manual" in a:
        i = a.index("--manual")
        box = [float(v) for v in a[i + 1:i + 5]]
        found = 1.0
        med = box
    else:
        info = probe(video)
        casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
        boxes, times = [], []
        n = 30
        say("looking for the face in 30 frames")
        for k in range(n):
            if k and k % 10 == 0:
                say(f"  {k}/30 frames checked")
            t = 0.2 + (info["duration"] - 0.4) * k / (n - 1)
            fr = grab(video, t)
            g = cv2.cvtColor(cv2.resize(fr, (W // 2, H // 2)), cv2.COLOR_RGB2GRAY)
            fs = casc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(70, 70))
            if len(fs):
                x, y, w, h = max(fs, key=lambda b: b[2] * b[3])
                boxes.append([x * 2, y * 2, (x + w) * 2, (y + h) * 2])
                times.append(t)
        found = len(boxes) / n
        if not boxes:
            cmd_frames([str(video), f"{info['duration'] / 2:.2f}"])
            say("NO FACE FOUND automatically. Open the frame above (5% ruler lines), measure the face and run:")
            say("  kit face <video> --manual x0 y0 x1 y1   (pixels on 1080x1920; x from the left, y from the top)")
            sys.exit(3)
        arr = np.array(boxes, float)
        med = list(np.median(arr, axis=0))
        mw = med[2] - med[0]
        mc = ((med[0] + med[2]) / 2, (med[1] + med[3]) / 2)
        cx, cy = (arr[:, 0] + arr[:, 2]) / 2, (arr[:, 1] + arr[:, 3]) / 2
        keep = arr[(np.abs((arr[:, 2] - arr[:, 0]) - mw) < 0.35 * mw) & (np.hypot(cx - mc[0], cy - mc[1]) < 0.5 * mw)]
        if len(keep) == 0:
            keep = arr
        # the face as it moves while talking: 10th to 90th percentile of the steady detections
        box = [np.percentile(keep[:, 0], 10), np.percentile(keep[:, 1], 10),
               np.percentile(keep[:, 2], 90), np.percentile(keep[:, 3], 90)]
    bw, bh = box[2] - box[0], box[3] - box[1]
    forbid = [max(0, box[0] - 0.12 * bw), max(0, box[1] - 0.12 * bh), min(W, box[2] + 0.12 * bw), min(H, box[3] + 0.12 * bh)]
    data = {"box": [round(v) for v in box], "median": [round(v) for v in med], "forbid": [round(v) for v in forbid],
            "center": [round((box[0] + box[2]) / 2), round((box[1] + box[3]) / 2)], "found_in": round(found, 2),
            "note": "pixels on the 1080x1920 canvas; forbid = face box grown by 12%, nothing may be drawn there"}
    save_json(jd / "face.json", data)
    say(json.dumps(data, ensure_ascii=False))
    if found < 0.3:
        say("LOW CONFIDENCE the face was found in few frames. Check frames/ and correct with --manual if needed.")
    say(f"face spans y {forbid[1] / H * 100:.0f}% to {forbid[3] / H * 100:.0f}% of the height")
    # show a frame where the face was actually found (not a screen recording in the middle)
    ft = times[len(times) // 2] if "--manual" not in a and times else probe(video)["duration"] / 2
    cmd_frames([str(video), f"{ft:.2f}"])


def cmd_band(a):
    video = Path(a[0])
    jd = job_dir(video)
    mode = a[a.index("--mode") + 1] if "--mode" in a else "full"
    if mode in ("split", "window"):
        # the animation lives on its own panel, the face does not limit it
        if mode == "split":
            band, cap_y = [1056 + 60, H - 320], 1056
        else:
            band, cap_y = [900, H - 320], 830
        data = {"mode": mode, "band": band, "band_pct": round((band[1] - band[0]) / H * 100, 1),
                "rule": "panel: the whole panel is free for the animation; captions sit at captions_y",
                "captions_y": cap_y, "instagram_safe": {"top": 108, "bottom": H - 320, "right": W - 120}}
        save_json(jd / "band.json", data)
        say(json.dumps(data, ensure_ascii=False))
        return
    face = load_json(jd / "face.json")
    if not face:
        die("run face first")
    cap_top = None
    head = None
    if "--captions-top" in a:
        cap_top = float(a[a.index("--captions-top") + 1]) / 100 * H
    if "--headline" in a:
        i = a.index("--headline")
        head = [float(a[i + 1]) / 100 * H, float(a[i + 2]) / 100 * H]
    top = max(face["forbid"][3], face["box"][3] + 0.06 * H)
    if head and head[0] > face["box"][3]:
        top = max(top, head[1] + 40)
    bottom = H - 320
    if cap_top:
        bottom = min(bottom, cap_top - 40)
    h = max(0, bottom - top)
    pct = h / H * 100
    if pct >= 18:
        rule = "normal: elements up to 22% of H inside the band"
    elif pct >= 10:
        rule = "narrow: one element at a time, no taller than the band; big ideas go to full-screen moments (or side margins if the style never hides the speaker)"
    else:
        rule = "none: nothing on camera under the face; visuals only in full-screen moments or side margins"
    side = {}
    for k, (x0, x1) in {"left": (int(0.04 * W), int(face["forbid"][0]) - 20), "right": (int(face["forbid"][2]) + 20, W - 120)}.items():
        side[k] = [x0, x1] if x1 - x0 >= 0.18 * W else "too narrow"
    data = {"mode": "full", "band": [round(top), round(bottom)], "band_pct": round(pct, 1), "rule": rule, "side_margins_x": side,
            "captions_top": round(cap_top) if cap_top else None, "headline": [round(v) for v in head] if head else None,
            "instagram_safe": {"top": 108, "bottom": H - 320, "right": W - 120}}
    save_json(jd / "band.json", data)
    say(json.dumps(data, ensure_ascii=False))


def cmd_palette(a):
    import numpy as np
    from PIL import Image
    im = Image.open(a[0]).convert("RGBA")
    im.thumbnail((300, 300))
    px = np.asarray(im).reshape(-1, 4).astype(float)
    px = px[px[:, 3] > 200][:, :3]
    px = px[~np.all(px > 240, axis=1)]
    if len(px) < 10:
        die("the image has almost no colored pixels")
    k = min(5, len(np.unique(px.astype(int), axis=0)))
    cent = px[np.linspace(0, len(px) - 1, k).astype(int)]
    for _ in range(25):
        lab = np.argmin(((px[:, None, :] - cent[None]) ** 2).sum(-1), 1)
        cent = np.array([px[lab == j].mean(0) if np.any(lab == j) else cent[j] for j in range(k)])
    cols = [tuple(int(v) for v in c) for c in cent]

    def lum(c):
        r = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * r[0] + 0.7152 * r[1] + 0.0722 * r[2]

    def sat(c):
        mx, mn = max(c), min(c)
        return 0 if mx == 0 else (mx - mn) / mx

    def contrast(c1, c2):
        l1, l2 = sorted((lum(c1), lum(c2)), reverse=True)
        return (l1 + 0.05) / (l2 + 0.05)

    hexs = lambda c: "#%02x%02x%02x" % c
    bg = max(cols, key=lum)
    if lum(bg) < 0.6:
        bg = (255, 251, 241)
    import colorsys
    hue = lambda c: colorsys.rgb_to_hsv(*(v / 255 for v in c))[0]
    by_sat = sorted(cols, key=sat, reverse=True)
    primary = by_sat[0]
    # the accent must look different from the primary: another hue, or else a light tint of the primary
    others = [c for c in by_sat[1:] if min(abs(hue(c) - hue(primary)), 1 - abs(hue(c) - hue(primary))) > 0.08 and sat(c) > 0.25]
    accent = others[0] if others else tuple(int(v + (255 - v) * 0.6) for v in primary)
    ink = min(cols, key=lum)
    if contrast(ink, bg) < 4.5:
        ink = (17, 17, 17) if lum(bg) > 0.4 else (255, 255, 255)
    def warm_score(c):
        h, l, sv = colorsys.rgb_to_hls(*(v / 255 for v in c))
        return sv if (h < 0.17 or h > 0.92) and sv > 0.35 else -1
    warm = max(cols, key=warm_score)
    warm = warm if warm_score(warm) > 0 else (255, 108, 76)
    res = {"all": [hexs(c) for c in cols], "bg": hexs(bg), "ink": hexs(ink), "primary": hexs(primary), "accent": hexs(accent),
           "warm": hexs(warm), "contrast_ink_on_bg": round(contrast(ink, bg), 2)}
    say(json.dumps(res))


# ----------------------------------------------------------------------------- commands: words

def cmd_transcribe(a):
    video = Path(a[0])
    name = a[a.index("--model") + 1] if "--model" in a else "ivrit"
    lang = a[a.index("--lang") + 1] if "--lang" in a else "he"
    jd = job_dir(video)
    wav = jd / "voice16k.wav"
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    from faster_whisper import WhisperModel
    say(f"loading model {name} (first time on this computer it downloads, see the model command)")
    model = WhisperModel(MODELS[name], device="cpu", compute_type="int8", download_root=str(STUDIO / "models"),
                         revision=MODEL_REVISIONS.get(MODELS[name]))
    say("transcribing, one line per sentence as it finishes")
    segs, info = model.transcribe(str(wav), language=None if lang == "auto" else lang, beam_size=5,
                                  word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
    words, lines = [], []
    for s in segs:
        say(f"[{s.start:6.2f} -> {s.end:6.2f}] {s.text.strip()}")
        lines.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for w in s.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)})
    save_json(jd / "words.json", {"model": name, "words": words, "lines": lines})
    (jd / "words.txt").write_text("\n".join(f"{w['s']:7.2f} {w['e']:7.2f}  {w['w']}" for w in words), encoding="utf-8")
    if words:
        span = words[-1]["e"] - words[0]["s"]
        say(f"TRANSCRIBED {len(words)} words ({len(words) / max(span, 0.1):.1f} words per second), saved to {jd / 'words.json'}")
    else:
        say("PROBLEM the model heard no speech. Check that the video has sound, or try --lang auto")
        sys.exit(2)


def cmd_strip(a):
    from PIL import Image, ImageDraw
    video, t0, t1, y0, y1 = Path(a[0]), float(a[1]), float(a[2]), float(a[3]), float(a[4])
    step = float(a[a.index("--step") + 1]) if "--step" in a else 0.1
    ts, t = [], t0
    while t <= t1 + 1e-6 and len(ts) < 40:
        ts.append(round(t, 2))
        t += step
    Y0, Y1 = int(y0 / 100 * H), int(y1 / 100 * H)
    rh = Y1 - Y0
    k = 540 / W
    out = Image.new("RGB", (540 + 90, int(rh * k) * len(ts)), (0, 0, 0))
    d = ImageDraw.Draw(out)
    for i, t in enumerate(ts):
        fr = Image.fromarray(grab(video, t)).crop((0, Y0, W, Y1)).resize((540, int(rh * k)))
        out.paste(fr, (90, i * int(rh * k)))
        d.text((6, i * int(rh * k) + 4), f"{t:.2f}s", fill=(255, 255, 0))
    p = job_dir(video) / f"strip_{t0:.2f}-{t1:.2f}.png"
    out.save(p)
    say(f"STRIP {p}  (one row per {step}s; the time a word first appears is its real onset)")


# ----------------------------------------------------------------------------- compositing

class Layouter:
    """Turns the scene's layout(t) answer into a base frame (the video where it should be)."""

    def __init__(self):
        import numpy as np
        self.np = np
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(np.float32)

    def base(self, frame, L):
        np = self.np
        bg = np.array(Canvas._c(L.get("bg", (255, 251, 241)))[:3], np.float32)
        mode = L.get("mode", "full")
        if mode == "full":
            z = float(L.get("zoom", 1.0))
            if z <= 1.0:
                return frame.astype(np.float32), ("full", 1.0, 0.0, 0.0)
            import cv2
            fx, fy = L.get("focus", (W / 2, H / 2))
            cw, ch = W / z, H / z
            sx = min(max(fx - cw / 2, 0), W - cw)
            sy = min(max(fy - ch / 2, 0), H - ch)
            crop = frame[int(sy):int(sy + ch), int(sx):int(sx + cw)]
            return cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32), ("full", z, sx, sy)
        out = np.empty((H, W, 3), np.float32)
        out[:] = bg
        if mode == "hidden":
            return out, None
        if mode == "iris":
            cx, cy, r = L["cx"], L["cy"], L["r"]
            vis = L.get("alpha", 1.0)
            if r <= 0 or vis <= 0:
                return out, None
            d = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
            m = np.clip(r - d + 0.5, 0, 1)[..., None] * vis
            out = out * (1 - m) + frame.astype(np.float32) * m
            ring = L.get("ring", 6)
            if ring and r < max_radius(cx, cy) - 1:
                ink = np.array(Canvas._c(L.get("ink", (26, 26, 26)))[:3], np.float32)
                rm = (np.clip(ring / 2 - np.abs(d - r) + 0.5, 0, 1) * vis)[..., None]
                out = out * (1 - rm) + ink * rm
            return out, ("circle", cx, cy, r)
        if mode == "split":
            h = int(L.get("h", 1056))
            fy = L.get("focus_y", H / 2)
            y0 = int(min(max(fy - h / 2, 0), H - h))
            out[:h] = frame[y0:y0 + h]
            return out, ("window", 0, 0, W, h, 0, y0, W, h)
        if mode == "window":
            import cv2
            x, y, w, h = int(L["x"]), int(L["y"]), int(L["w"]), int(L["h"])
            fx, fy = L.get("focus", (W / 2, H / 2))
            if w / h < W / H:
                src_h, src_w = H, H * w / h
            else:
                src_w, src_h = W, W * h / w
            z = max(1.0, L.get("zoom", 1.0))
            src_w, src_h = max(1, int(src_w / z)), max(1, int(src_h / z))
            sx = int(min(max(fx - src_w / 2, 0), W - src_w))
            sy = int(min(max(fy - src_h / 2, 0), H - src_h))
            crop = cv2.resize(frame[sy:sy + src_h, sx:sx + src_w], (w, h), interpolation=cv2.INTER_AREA)
            rad = L.get("radius", 32)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            dx = np.maximum(np.maximum(rad - xx, xx - (w - 1 - rad)), 0)
            dy = np.maximum(np.maximum(rad - yy, yy - (h - 1 - rad)), 0)
            m = np.clip(rad - np.sqrt(dx ** 2 + dy ** 2) + 0.5, 0, 1)[..., None]
            region = out[y:y + h, x:x + w]
            out[y:y + h, x:x + w] = region * (1 - m) + crop.astype(np.float32) * m
            return out, ("window", x, y, w, h, sx, sy, src_w, src_h)
        die(f"unknown layout mode {mode}")


def max_radius(cx, cy):
    return max(math.dist((cx, cy), c) for c in ((0, 0), (W, 0), (0, H), (W, H))) + 2


def iris(t, hide_at, show_at, face_c, dot, bg, ink=(26, 26, 26), ring=6):
    """The iris transition numbers, ready to return from layout(t).

    hide_at: the word where the full-screen scene starts. The circle starts closing 0.20 s before,
             shrinks to a 38 px dot over 0.45 s while its center travels from the face to dot (x, y),
             the empty spot where the full-screen scene's first element will appear, usually (540, 900),
             the dot holds 0.30 s and fades.
    show_at: the word where the speaker comes back. The circle opens from 38 px, 0.15 s before,
             over 0.45 s, around the face.
    show_at=None: the circle closes and never reopens (the closing: dot, then the logo in draw).
    Outside [hide_at - 0.2, show_at + 0.3] the answer is simply full screen.
    """
    c0 = hide_at - 0.20
    c1 = c0 + 0.45
    o0 = show_at - 0.15 if show_at is not None else float("inf")
    o1 = o0 + 0.45
    rf = max_radius(*face_c)
    if t < c0 or t >= o1:
        return {"mode": "full", "bg": bg}
    if t < c1:
        p = seg(t, c0, c1)
        k = 0.6 * expo_in(p) + 0.4 * ease_in_out_cubic(p)
        cx = face_c[0] + (dot[0] - face_c[0]) * ease_in_out_cubic(p)
        cy = face_c[1] + (dot[1] - face_c[1]) * ease_in_out_cubic(p)
        return {"mode": "iris", "cx": cx, "cy": cy, "r": rf + (38 - rf) * k, "bg": bg, "ink": ink, "ring": ring}
    if t < c1 + 0.30 + 0.15:
        fade = 1 - seg(t, c1 + 0.30, c1 + 0.45)
        return {"mode": "iris", "cx": dot[0], "cy": dot[1], "r": 38, "alpha": fade, "bg": bg, "ink": ink, "ring": ring}
    if t < o0:
        return {"mode": "hidden", "bg": bg}
    p = ease_in_out_cubic(seg(t, o0, o1))
    return {"mode": "iris", "cx": face_c[0], "cy": face_c[1], "r": 38 + (rf - 38) * p, "bg": bg, "ink": ink, "ring": ring}


def current_word(t, words, max_hold=0.9):
    """The word on screen at time t for one-word captions: from its onset until the next onset, at most max_hold."""
    cur = None
    for i, w in enumerate(words):
        if w["s"] <= t:
            nxt = words[i + 1]["s"] if i + 1 < len(words) else w["e"] + max_hold
            if t < min(nxt, w["s"] + max_hold):
                cur = w
        else:
            break
    return cur


def caption_chunks(words, max_words=3, max_gap=0.35):
    """Group words into caption chunks of up to max_words, breaking on pauses longer than max_gap.
    Each chunk: {"text", "s", "e", "words"}. Draw the chunk whose s <= t < e."""
    out = []
    for w in words:
        if out and len(out[-1]["words"]) < max_words and w["s"] - out[-1]["e"] < max_gap:
            out[-1]["words"].append(w)
            out[-1]["e"] = w["e"]
        else:
            out.append({"words": [w], "s": w["s"], "e": w["e"]})
    for ch in out:
        ch["text"] = " ".join(x["w"] for x in ch["words"])
    return out


def load_scenes(video):
    import importlib.util
    jd = job_dir(video)
    p = jd / "scenes.py"
    if not p.exists():
        die(f"no scenes.py in {jd}. Run: kit.py scaffold <video>")
    sys.path.insert(0, str(KIT_DIR))
    spec = importlib.util.spec_from_file_location("scenes", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for need in ("layout", "draw"):
        if not hasattr(mod, need):
            die(f"scenes.py must define {need}(t, ...)")
    return mod


def compose(frame, t, scenes, lay):
    """Return (rgb uint8 frame, overlay alpha array or None, video placement)."""
    import numpy as np
    L = scenes.layout(t)
    base, placement = lay.base(frame, L)
    c = Canvas()
    scenes.draw(t, c)
    ov = c.result()
    if ov is not None:
        a = ov[..., 3:4].astype(np.float32) / 255
        base = base * (1 - a) + ov[..., :3].astype(np.float32) * a
        alpha = ov[..., 3]
    else:
        alpha = None
    return np.clip(base + 0.5, 0, 255).astype(np.uint8), alpha, placement


def face_hits(alpha, placement, face):
    """Rule 1: count overlay pixels on the face where the face is actually visible, in every layout mode."""
    import numpy as np
    if alpha is None or not face or placement is None:
        return 0
    fx0, fy0, fx1, fy1 = face["forbid"]
    kind = placement[0]
    if kind == "full":
        _, z, sx, sy = placement
        box = [(fx0 - sx) * z, (fy0 - sy) * z, (fx1 - sx) * z, (fy1 - sy) * z]
        clip = [0, 0, W, H]
    elif kind == "circle":
        box, clip = [fx0, fy0, fx1, fy1], [0, 0, W, H]
    elif kind == "window":
        _, x, y, w, h, sx, sy, sw, sh = placement
        box = [x + (fx0 - sx) * w / sw, y + (fy0 - sy) * h / sh, x + (fx1 - sx) * w / sw, y + (fy1 - sy) * h / sh]
        clip = [x + 8, y + 8, x + w - 8, y + h - 8]     # a frame drawn on the window edge is not "on the face"
    else:
        return 0
    x0, y0 = int(max(box[0], clip[0])), int(max(box[1], clip[1]))
    x1, y1 = int(min(box[2], clip[2])), int(min(box[3], clip[3]))
    if x1 <= x0 or y1 <= y0:
        return 0
    region = alpha[y0:y1, x0:x1] > 25
    if kind == "circle":
        _, cx, cy, r = placement
        yy, xx = np.mgrid[y0:y1, x0:x1]
        region &= (xx - cx) ** 2 + (yy - cy) ** 2 < r * r
    return int(region.sum())


def cmd_render(a):
    import numpy as np
    from PIL import Image, ImageDraw
    video = Path(a[0])
    jd = job_dir(video)
    scenes = load_scenes(video)
    face = load_json(jd / "face.json")
    lay = Layouter()
    if "--check" in a:
        ts = [float(x) for x in a[a.index("--check") + 1:] if not x.startswith("--")]
        cd = jd / "checks"
        cd.mkdir(exist_ok=True)
        thumbs, bad = [], 0
        for t in ts:
            fr, alpha, pl = compose(grab(video, t), t, scenes, lay)
            hits = face_hits(alpha, pl, face)
            p = cd / f"check_{t:07.2f}.png"
            Image.fromarray(fr).save(p)
            flag = f"  FACE COVERED ({hits} px) rule 1" if hits > 50 else ""
            bad += hits > 50
            say(f"STILL {p}{flag}")
            thumbs.append((t, Image.fromarray(fr).resize((270, 480)), hits > 50))
        cols = min(6, len(thumbs))
        rows = math.ceil(len(thumbs) / cols)
        sh = Image.new("RGB", (270 * cols, 504 * rows), (20, 20, 20))
        d = ImageDraw.Draw(sh)
        for i, (t, im, b) in enumerate(thumbs):
            x, y = (i % cols) * 270, (i // cols) * 504
            sh.paste(im, (x, y + 24))
            d.text((x + 6, y + 6), f"{t:.2f}s" + ("  FACE!" if b else ""), fill=(255, 80, 80) if b else (255, 255, 255))
        sp = cd / "sheet.png"
        sh.save(sp)
        say(f"CHECK SHEET {sp}")
        say("RULE 1 OK no overlay on the face" if not bad else f"RULE 1 BROKEN in {bad} stills")
        return
    info = probe(video)
    end = float(getattr(scenes, "END", info["duration"]))
    nframes = int(round(end * FPS))
    audio = a[a.index("--audio") + 1] if "--audio" in a else None
    out = Path(a[a.index("--out") + 1]) if "--out" in a else STUDIO / "out" / (video.stem + "-animated.mp4")
    if out.resolve() == Path(video).resolve():
        die("the output path is the original video. Choose another name, the original is never overwritten.")
    out = free_name(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg_exe()
    dec = subprocess.Popen([ff, "-v", "error", "-i", str(video), "-vf", vf_fit(), "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    enc_cmd = [ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio:
        enc_cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a"]
    elif info["has_audio"]:
        enc_cmd += ["-i", str(video), "-map", "0:v", "-map", "1:a:0"]
    if "--grain" in a:
        enc_cmd += ["-vf", "noise=alls=4:allf=t", "-tune", "grain"]
    enc_cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-t", f"{end:.3f}", "-movflags", "+faststart", str(out)]
    log = open(jd / "encode.log", "w")
    enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, stderr=log)
    size = W * H * 3
    last = np.zeros((H, W, 3), np.uint8)
    face_frames, lum_prev, jumps, frozen = [], None, [], 0
    t_start = time.time()
    say(f"rendering {nframes} frames to {out}")
    for i in range(nframes):
        raw = dec.stdout.read(size)
        if raw and len(raw) == size:
            last = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        t = i / FPS
        fr, alpha, pl = compose(last, t, scenes, lay)
        if t > info["duration"] + 0.05 and pl is not None:
            frozen += 1
        if face_hits(alpha, pl, face) > 50:
            face_frames.append(round(t, 2))
        lum = float(fr[::8, ::8].mean())
        if lum_prev is not None and abs(lum - lum_prev) > 40:
            jumps.append(round(t, 2))
        lum_prev = lum
        enc.stdin.write(fr.tobytes())
        if i % FPS == 0 or i == nframes - 1:
            el = time.time() - t_start
            eta = el / (i + 1) * (nframes - i - 1)
            left = f"left about {eta / 60:.1f} min" if i >= nframes * 0.05 else "estimating time left"
            say(f"frame {i + 1}/{nframes}  {100 * (i + 1) / nframes:.0f}%  elapsed {el / 60:.1f} min  {left}")
    enc.stdin.close()
    enc.wait()
    dec.kill()
    log.close()
    if enc.returncode != 0:
        die(f"the encoder failed, see {jd / 'encode.log'}")
    flashes = [t for t in jumps if sum(1 for u in jumps if t <= u < t + 1) > 3]
    say("RULE 1 OK no overlay on the face" if not face_frames else f"RULE 1 BROKEN at {face_frames[:20]}")
    say("RULE 8 OK no flashing" if not flashes else f"RULE 8 CHECK brightness jumps at {sorted(set(flashes))[:20]}")
    if frozen:
        say(f"CHECK the source video ends at {info['duration']:.2f}s but {frozen} later frames still show it (a frozen picture). "
            "Make layout return hidden or a closed iris after the last word.")
    if jumps and not flashes:
        say(f"NOTE single brightness jumps (cuts in the source or iris edges) at {jumps[:10]}")
    say(f"DONE {out}")


def cmd_scaffold(a):
    video = Path(a[0])
    jd = job_dir(video)
    p = jd / "scenes.py"
    if p.exists():
        say(f"EXISTS {p} (not overwritten)")
        return
    p.write_text(SCAFFOLD, encoding="utf-8")
    say(f"WROTE {p}")


SCAFFOLD = '''# -*- coding: utf-8 -*-
# scenes.py: the story of this reel as code. Every color, size, curve and duration comes from the
# style file (the tokens block). Every time comes from words.json (after checking it against burned captions).
# Rules the kit checks for you: nothing on the face (rule 1), no flashing (rule 8).
import json
from pathlib import Path
from kit import (Canvas, W, H, clamp01, seg, back, ease_out_cubic, ease_in_cubic, ease_in_out_cubic, expo_in,
                 bezier, spring, iris, current_word, caption_chunks, rand, hexrgb)

JOB = Path(__file__).parent
FACE = json.loads((JOB / "face.json").read_text(encoding="utf-8"))
BAND = json.loads((JOB / "band.json").read_text(encoding="utf-8"))["band"]      # [top, bottom] in px
WORDS = json.loads((JOB / "words.json").read_text(encoding="utf-8"))["words"]   # [{"w","s","e"}]

# ---- tokens: copy them from the style file (the tokens block), nowhere else
BG = hexrgb("#fffbf1")
INK = hexrgb("#1a1a1a")
PRIMARY = hexrgb("#b9a7f0")
ACCENT = hexrgb("#efd9a8")
WARM = hexrgb("#ff6c4c")
RADIUS = 21        # the style's corner radius
BORDER = 0         # the style's outline width, 0 = no outline
SHADOW = None      # (-14, 14) only if the style has block shadows

# END = 30.0   # set this only if the closing needs time after the last word (seconds)

# ---- the story table, one row per idea. t = the onset of the word the visual lands on.
# (fill from the approved story table; one idea at a time, clean face between ideas)
SCENES = [
    # dict(name="card", t=2.20, until=3.40),
]
FULLSCREEN = [
    # (hide_at, show_at, (540, 900))   moments where the speaker is hidden and the screen explains.
    # hide_at and show_at are word onsets. The third value is the dot where the iris closes.
]
# Styles that never hide the speaker, when band.json says "none": a clean cut instead of the iris,
# return {"mode": "hidden", "bg": BG} between hide_at and show_at.


def layout(t):
    """Where the video is at time t. See the style file for which modes this style uses."""
    for hide_at, show_at, dot in FULLSCREEN:
        if hide_at - 0.25 <= t < show_at + 0.35:
            return iris(t, hide_at, show_at, FACE["center"], dot, BG, INK)
    return {"mode": "full", "bg": BG}


def draw(t, c):
    """Everything above the video at time t. c is a Canvas (1080x1920 coordinates)."""
    top, bottom = BAND
    mid = (top + bottom) / 2
    for s in SCENES:
        if s["t"] - 0.4 <= t < s["until"] + 0.4:
            p_in = seg(t, s["t"] - 0.15, s["t"] + 0.25)          # enters just before its word
            p_out = seg(t, s["until"], s["until"] + 0.27)         # leaves faster than it came
            k = back(p_in) * (1 - expo_in(p_out))
            if k > 0:
                # an example element; replace with the visual from the story table
                c.card(240, mid - 70, 840, mid + 70, fill=PRIMARY, ink=INK, border=BORDER, radius=RADIUS,
                       shadow=SHADOW, shadow_fill=ACCENT, scale=k)
                c.text(540, mid, "מילה", 56, INK, 600)
'''


# ----------------------------------------------------------------------------- sound

def _pink(n, seed):
    import numpy as np
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.arange(len(X))
    f[0] = 1
    y = np.fft.irfft(X / np.sqrt(f), n)
    return y / (np.abs(y).max() + 1e-9)


def _svf_bandpass(x, fc, q=1.2):
    """State variable band-pass with a per-sample center frequency array."""
    import numpy as np
    low = band = 0.0
    out = np.empty_like(x)
    damp = 1.0 / q
    for i in range(len(x)):
        f = 2 * math.sin(math.pi * min(fc[i], SR / 6) / SR)
        high = x[i] - low - damp * band
        band += f * high
        low += f * band
        out[i] = band
    return out


def _norm(x, peak_db=-3.0):
    import numpy as np
    m = np.abs(x).max()
    return x / m * (10 ** (peak_db / 20)) if m > 0 else x


def synth(name):
    """Returns (mono float array at SR, peak offset in seconds). All sounds made in code, no licenses."""
    import numpy as np
    t = lambda d: np.arange(int(d * SR)) / SR
    if name == "whoosh":
        d = 0.8; tt = t(d); p = tt / d
        fc = np.where(p < 0.5, 300 * (2500 / 300) ** (p / 0.5), 2500 * (900 / 2500) ** ((p - 0.5) / 0.5))
        y = _svf_bandpass(_pink(len(tt), 1), fc, 1.4) * np.sin(np.pi * p) ** 2
        return _norm(y), 0.4
    if name == "riser":
        d = 1.5; tt = t(d); p = tt / d
        fc = 200 * (6000 / 200) ** p
        y = _svf_bandpass(_pink(len(tt), 2), fc, 2.0) * p ** 2
        y[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
        return _norm(y), d
    if name == "sub":
        d = 0.6; tt = t(d)
        f = 70 * (32 / 70) ** np.clip(tt / 0.45, 0, 1)
        ph = 2 * np.pi * np.cumsum(f) / SR
        env = np.minimum(tt / 0.005, 1) * np.exp(-tt / 0.15)
        return _norm(np.sin(ph) * env), 0.005
    if name == "tick":
        tt = t(0.06)
        y = (np.sin(2 * np.pi * 900 * tt) + 0.25 * np.sin(2 * np.pi * 1800 * tt)) * np.exp(-tt / 0.012)
        return _norm(y), 0.0
    if name == "tick-high":
        tt = t(0.06)
        y = (np.sin(2 * np.pi * 1350 * tt) + 0.25 * np.sin(2 * np.pi * 2700 * tt)) * np.exp(-tt / 0.012)
        return _norm(y), 0.0
    if name == "knock":
        tt = t(0.12)
        y = np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.025)
        y[:int(0.01 * SR)] += _pink(int(0.01 * SR), 3) * 0.5
        return _norm(y), 0.0
    if name == "pop":
        tt = t(0.09)
        f = 500 + 600 * np.clip(tt / 0.07, 0, 1)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.025)
        return _norm(y), 0.01
    if name == "click":
        tt = t(0.02)
        y = _pink(len(tt), 4) * np.exp(-tt / 0.003) + 0.3 * np.sin(2 * np.pi * 2000 * tt) * np.exp(-tt / 0.004)
        return _norm(y), 0.0
    if name == "chime":
        tt = t(1.0)
        y = sum(a * np.sin(2 * np.pi * f * tt) for f, a in ((1320, 1), (1980, 0.5), (2640, 0.25)))
        return _norm(y * np.minimum(tt / 0.003, 1) * np.exp(-tt / 0.3)), 0.003
    if name == "scratch":
        d = 0.35; tt = t(d)
        fc = 1500 + 2000 * (0.5 + 0.5 * np.sin(2 * np.pi * 18 * tt))
        y = _svf_bandpass(_pink(len(tt), 5), fc, 1.5) * np.sin(np.pi * tt / d) ** 0.5
        return _norm(y), 0.05
    if name == "stamp":
        tt = t(0.3)
        f = 90 * (50 / 90) ** np.clip(tt / 0.2, 0, 1)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.07)
        n = _pink(len(tt), 6) * np.exp(-tt / 0.02)
        return _norm(y + 0.4 * n), 0.0
    die(f"unknown sound {name}")


SOUNDS = ["whoosh", "riser", "sub", "tick", "tick-high", "knock", "pop", "click", "chime", "scratch", "stamp"]


def cmd_sfx(a):
    import numpy as np
    import wave
    d = STUDIO / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    index = {}
    for n in SOUNDS:
        y, pk = synth(n)
        with wave.open(str(d / f"{n}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
        index[n] = {"peak": pk, "dur": round(len(y) / SR, 3)}
        say(f"SOUND {n:10s} {len(y) / SR:.2f}s  peak at {pk:.3f}s")
    save_json(d / "index.json", index)
    say(f"LIBRARY {d}  (listen: kit.py open {d / 'whoosh.wav'})")


def _read_audio(path, dur=None):
    import numpy as np
    cmd = [ffmpeg_exe(), "-v", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy() if raw else np.zeros((0, 2), np.float32)
    if dur is not None:
        n = int(dur * SR)
        x = x[:n] if len(x) >= n else np.vstack([x, np.zeros((n - len(x), 2), np.float32)])
    return x


def _write_wav(path, x):
    import numpy as np
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP), measured by ffmpeg's EBU R128 meter."""
    import re
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    tail = p[p.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    f = lambda m: float(m.group(1)) if m and m.group(1) != "-inf" else -99.0
    return f(i), f(tp)


def _pad(dur, chord_every=4.8, swell_at=None, swell_db=6, swell_s=2.0):
    import numpy as np
    tt = np.arange(int(dur * SR)) / SR
    chords = [(220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 261.63, 329.63)]
    y = np.zeros_like(tt)
    for k in range(int(dur / chord_every) + 1):
        a, b = k * chord_every, (k + 1) * chord_every + 1.0
        m = (tt >= a) & (tt < b)
        if not m.any():
            continue
        lt = tt[m] - a
        env = np.minimum(lt / 1.0, 1) * np.minimum(np.maximum((b - tt[m]) / 1.0, 0), 1)
        for f in chords[k % len(chords)]:
            y[m] += env * (np.sin(2 * np.pi * f * tt[m]) + 0.3 * np.sin(2 * np.pi * f * 2.003 * tt[m])) / 3
    if swell_at is not None:
        g = 10 ** (swell_db / 20)
        ramp = np.clip((tt - swell_at) / max(swell_s, 0.1), 0, 1)
        y *= 1 + (g - 1) * ramp
    return np.stack([y, y * 0.98], 1).astype(np.float32)


def cmd_mix(a):
    import numpy as np
    video, cues_p = Path(a[0]), Path(a[1])
    jd = job_dir(video)
    spec = load_json(cues_p)
    info = probe(video)
    dur = float(spec.get("end", info["duration"]))
    lib = STUDIO / "sfx"
    if not (lib / "index.json").exists():
        cmd_sfx([])
    index = load_json(lib / "index.json")
    say("reading the voice, placing the sounds, measuring loudness (under a minute)")
    voice = _read_audio(video, dur)
    seen, problems = {}, []
    sfx = np.zeros_like(voice)
    for c in spec.get("cues", []):
        layers = c.get("layers") or [{"sound": c["sound"]}]
        sig = json.dumps(sorted((L["sound"], L.get("repeat", 1), L.get("pitch", 0)) for L in layers))
        if sig in seen and not spec.get("allow_repeat"):
            problems.append(f"rule 6: '{c.get('name', sig)}' repeats the sound of '{seen[sig]}'. Make each beat its own sound.")
        seen[sig] = c.get("name", sig)
        for L in layers:
            y, pk = synth(L["sound"])
            st = float(L.get("pitch", 0))
            if st:
                # a different pitch is a different sound (rich styles): resample by 2^(semitones/12)
                import numpy as np
                r = 2 ** (st / 12)
                idx = np.arange(0, len(y) - 1, r)
                y, pk = np.interp(idx, np.arange(len(y)), y), pk / r
            g = 10 ** (L.get("db", -10) / 20)
            n_rep, every = int(L.get("repeat", 1)), float(L.get("every", 0.045))
            for r in range(n_rep):
                start = c["t"] + L.get("offset", 0) + r * every - pk
                i0 = int(round(start * SR))
                j0 = max(0, -i0)
                i0 = max(0, i0)
                n = min(len(y) - j0, len(sfx) - i0)
                if n > 0:
                    sfx[i0:i0 + n] += (y[j0:j0 + n] * g)[:, None]
    bed_spec = spec.get("bed", {"type": "pad", "under_lu": 17})
    tmp = jd / "_voice.wav"
    _write_wav(tmp, voice)
    lv, _ = loudness(tmp)
    bed = np.zeros_like(voice)
    lb = -99.0
    if bed_spec.get("type", "pad") != "none":
        bed = _pad(dur, bed_spec.get("chord_every", 4.8), bed_spec.get("swell_after"), bed_spec.get("swell_db", 6), bed_spec.get("swell_s", 2.0))
        _write_wav(tmp, bed * 0.5)
        lb0, _ = loudness(tmp)
        target = lv - float(bed_spec.get("under_lu", 17))
        bed = bed * 0.5 * 10 ** ((target - lb0) / 20)
        _write_wav(tmp, bed)
        lb, _ = loudness(tmp)
    raw = voice + sfx + bed
    rawp = jd / "_mix_raw.wav"
    _write_wav(rawp, raw * 0.5)
    ff = ffmpeg_exe()
    p1 = subprocess.run([ff, "-hide_banner", "-i", str(rawp), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = json.loads(p1[p1.rfind("{"):p1.rfind("}") + 1])
    out = jd / "mix.wav"
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"aresample={SR}")
    subprocess.run([ff, "-v", "error", "-y", "-i", str(rawp), "-af", af, "-ar", str(SR), str(out)], check=True)
    li, tp = loudness(out)
    tmp.unlink(missing_ok=True)
    gap = lv - lb if lb > -98 else None
    say(f"voice {lv:.1f} LUFS   bed {lb:.1f} LUFS   gap {gap:.1f} LU" if gap is not None else f"voice {lv:.1f} LUFS   no bed")
    say(f"final {li:.1f} LUFS   true peak {tp:.1f} dBTP   cues {len(spec.get('cues', []))} in {dur:.1f}s")
    if gap is not None and gap < 12:
        problems.append(f"rule 10: the bed is only {gap:.1f} LU under the voice, it must be at least 12")
    if tp > -1.0:
        problems.append(f"rule 10: true peak {tp:.1f} dBTP is above -1. Lower the loudest cue db and mix again")
    for pr in problems:
        say("PROBLEM " + pr)
    if problems:
        say("MIX NOT READY: fix the problems above in cues.json and run mix again")
        sys.exit(2)
    say(f"MIX {out}")


# ----------------------------------------------------------------------------- delivery

def cmd_verify(a):
    from PIL import Image, ImageDraw
    import numpy as np
    video = Path(a[0])
    info = probe(video)
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    ok = True
    say("checking the delivered file (size, codec, loudness, frames)")
    say(f"file {video}  {video.stat().st_size / 1e6:.1f} MB  {info['duration']:.2f}s  {info['width']}x{info['height']}")
    if (info["width"], info["height"]) != (W, H):
        ok = False; say("PROBLEM size is not 1080x1920")
    if "h264" not in p:
        ok = False; say("PROBLEM video is not h264")
    if not info["has_audio"]:
        ok = False; say("PROBLEM no audio in the delivered file")
    else:
        li, tp = loudness(video)
        say(f"loudness {li:.1f} LUFS   true peak {tp:.1f} dBTP")
        if tp > -1.0:
            ok = False; say("PROBLEM true peak above -1 dBTP")
    ts = [float(x) for x in a[a.index("--at") + 1:]] if "--at" in a else [info["duration"] * k / 7 for k in range(1, 7)]
    outd = Path(STUDIO / "jobs" / re.sub(r"-animated(-\d+)?$", "", video.stem) / "delivered")
    outd.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (270 * min(6, len(ts)), 504 * math.ceil(len(ts) / 6)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(ts):
        cmd = [ffmpeg_exe(), "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        raw = subprocess.run(cmd, capture_output=True).stdout
        if len(raw) >= info["width"] * info["height"] * 3:
            im = Image.fromarray(np.frombuffer(raw[:info["width"] * info["height"] * 3], np.uint8).reshape(info["height"], info["width"], 3))
            im.save(outd / f"d_{t:07.2f}.png")
            x, y = (i % 6) * 270, (i // 6) * 504
            sheet.paste(im.resize((270, 480)), (x, y + 24))
            d.text((x + 6, y + 6), f"{t:.2f}s", fill=(255, 255, 255))
    sp = outd / "sheet.png"
    sheet.save(sp)
    say(f"DELIVERED FRAMES {sp}")
    say("FILE OK" if ok else "FILE HAS PROBLEMS")


def cmd_remux(a):
    """Swap only the sound of an already rendered MP4 (after a sound note), without rendering the video again."""
    out, mix = Path(a[0]), Path(a[1])
    tmp = out.with_name(out.stem + ".remux.mp4")
    r = subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-i", str(out), "-i", str(mix), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(tmp)])
    if r.returncode != 0 or not tmp.exists():
        die("could not replace the sound")
    tmp.replace(out)
    say(f"NEW SOUND IN {out}")


def cmd_wait(a):
    """Wait for a background job: returns within about 90 seconds with its latest line.
    Prints READY when the marker appears, STUCK when the log has not changed for 5 minutes."""
    log, marker = Path(a[0]).expanduser(), a[1]
    t0 = time.time()
    last = ""
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
                say("STUCK: nothing new in the log for 5 minutes")
                sys.exit(3)
        time.sleep(5)
    say(last)
    say("STILL RUNNING (run the same wait command again)")


def cmd_open(a):
    p = str(Path(a[0]).resolve())
    if sys.platform.startswith("win"):
        os.startfile(p)
    elif sys.platform == "darwin":
        subprocess.run(["open", p])
    else:
        subprocess.run(["xdg-open", p])
    say(f"OPENED {p}")


COMMANDS = {
    "doctor": cmd_doctor, "font": cmd_font, "model": cmd_model, "info": cmd_info, "sheet": cmd_sheet,
    "frames": cmd_frames, "face": cmd_face, "band": cmd_band, "palette": cmd_palette, "transcribe": cmd_transcribe,
    "strip": cmd_strip, "scaffold": cmd_scaffold, "render": cmd_render, "sfx": cmd_sfx, "mix": cmd_mix,
    "verify": cmd_verify, "remux": cmd_remux, "wait": cmd_wait, "open": cmd_open,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    COMMANDS[sys.argv[1]](sys.argv[2:])
