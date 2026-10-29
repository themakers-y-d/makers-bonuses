#!/usr/bin/env python3
"""Draws an Instagram carousel (1080x1350 PNG per slide) from a JSON spec, right to left.

Usage:  python3 render.py spec.json --out FOLDER
        python3 render.py spec.json --out FOLDER --preview   (the first slide in all five looks, looks.png)

Needs only Pillow. The bidi code (python-bidi 0.4.2, LGPL, unmodified) and six are in
vendor/, and the Assistant font (OFL) is in ../fonts/, so nothing is downloaded.
Pillow's BASIC layout is used on purpose: it does not need libraqm, and Hebrew has no
joining letters, so bidi reordering is all that is needed.

The spec (every key but "slides" is optional):
{
  "style": "editorial" | "night" | "poster" | "retro" | "riso",
  "colors": {"bg": "#hex", "ink": "#hex", "soft": "#hex", "accent": "#hex", "accent2": "#hex"},
  "handle": "@name",
  "swipe": "החליקו",
  "photo": "path/to/image.jpg",          (cover slide only)
  "slides": [{"title": "...", "text": "..."}, ...]
}
Wrap one or two words of a title in *stars* to colour them.

Prints a JSON report: one line per slide with the font sizes used and any problem.
A slide whose text does not fit even at the smallest size is reported as "too_long";
the images are still written so the owner can see them, and the caller must shorten it.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "vendor"))
from bidi.algorithm import get_display  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is missing. Run: pip install pillow  (or: python3 -m pip install --user pillow)")

FONTS = os.path.join(os.path.dirname(HERE), "fonts")
W, H, PAD = 1080, 1350, 96
FLOOR = 1180  # nothing but the footer goes below this line
WEIGHTS = {400: "Regular", 600: "SemiBold", 700: "Bold", 800: "ExtraBold"}

STYLES = {
    # editorial page: ivory paper, a big ghost number behind the text, page number at the foot
    "editorial": {"bg": "#F4F0E8", "ink": "#171717", "soft": "#6B655C", "accent": "#C2410C", "accent2": "#ECE6DB"},
    # night: near black with grain, white heavy titles, the marked word sits on a glowing highlighter
    "night": {"bg": "#121212", "ink": "#F7F4EE", "soft": "#A8A39A", "accent": "#FFD34D", "accent2": "#2A2A2A"},
    # poster: huge type that fills the page, background swaps between two colours slide by slide
    "poster": {"bg": "#F2EDE3", "ink": "#111111", "soft": "#3A3A3A", "accent": "#E4472B", "accent2": "#111111"},
    # retro seventies: cream paper, three warm stripes that bend around a corner
    "retro": {"bg": "#F3E6CC", "ink": "#3B1F12", "soft": "#7A5A44", "accent": "#C2501A", "accent2": "#E3A72F"},
    # riso print: two inks slightly out of register, halftone dots and paper grain
    "riso": {"bg": "#F5F0E6", "ink": "#1D3F8C", "soft": "#4A5D8C", "accent": "#E0306F", "accent2": "#1D3F8C"},
}


def hexrgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


_font_cache = {}


def font(size, weight=700):
    key = (int(size), weight)
    if key not in _font_cache:
        path = os.path.join(FONTS, "Assistant-%s.ttf" % WEIGHTS[weight])
        _font_cache[key] = ImageFont.truetype(path, int(size), layout_engine=ImageFont.Layout.BASIC)
    return _font_cache[key]


def is_ltr(word):
    return not any("֐" <= c <= "׿" for c in word) and any(c.isalnum() for c in word)


def tokens(text):
    """Words in logical order, each with a highlight flag. Neighbouring Latin words become one
    unit, so "Claude Code" keeps its order inside a right to left line."""
    out, hi, glue = [], False, False
    for seg in str(text).split("*"):
        words = seg.split()
        for k, w in enumerate(words):
            if k == 0 and glue and out and not seg[:1].isspace():
                out[-1][0] += w  # no space between the star and this text: same word
            else:
                out.append([w, hi])
        if words:
            glue = not seg[-1:].isspace()
        elif seg:
            glue = False
        hi = not hi
    merged = []
    for w, h in out:
        # "Claude Code", and also "ו-GPT 5": a Latin run continues into the next Latin word
        if merged and merged[-1][1] == h and is_ltr(w) and merged[-1][0][-1:].isascii() and merged[-1][0][-1:].isalnum():
            merged[-1][0] += " " + w
        else:
            merged.append([w, h])
    return [(get_display(w, base_dir="R"), h, w) for w, h in merged]


def wrap(toks, f, maxw):
    sp = f.getlength(" ")
    lines, cur, cw = [], [], 0
    for vis, hi, logical in toks:
        wd = f.getlength(vis)
        nw = cw + sp + wd if cur else wd
        if cur and nw > maxw:
            lines.append(cur)
            cur, cw = [(vis, hi, wd, logical)], wd
        else:
            cur.append((vis, hi, wd, logical))
            cw = nw
    if cur:
        lines.append(cur)
    widest = max([sum(t[2] for t in l) + sp * (len(l) - 1) for l in lines] or [0])
    return lines, sp, widest


def fit(text, weight, big, small, maxw, max_lines, lh, room):
    toks = tokens(text)
    for s in range(big, small - 1, -2):
        f = font(s, weight)
        lines, sp, widest = wrap(toks, f, maxw)
        if len(lines) <= max_lines and widest <= maxw and len(lines) * s * lh <= room:
            return {"f": f, "size": s, "lines": lines, "sp": sp, "lh": lh, "ok": True}
    f = font(small, weight)
    lines, sp, _ = wrap(toks, f, maxw)
    return {"f": f, "size": small, "lines": lines, "sp": sp, "lh": lh, "ok": False}


def bidi_ok(b):
    """True when every line, drawn word by word, reads exactly like the full bidi algorithm
    would order it. A mismatch means a mixed Hebrew and Latin line the word layout cannot
    reproduce; the caller rephrases that line."""
    for line in b["lines"]:
        ours = " ".join(t[0] for t in reversed(line))
        full = get_display(" ".join(t[3] for t in line), base_dir="R")
        if ours != full:
            return False
    return True


def height(b):
    return len(b["lines"]) * b["size"] * b["lh"] if b else 0


def draw_block(d, b, y, x_right, maxw, align, ink, acc, mark=None):
    """Lays words right to left. align: right | center | justify (last line stays right)."""
    f, s = b["f"], b["size"]
    for i, line in enumerate(b["lines"]):
        words = sum(t[2] for t in line)
        natural = words + b["sp"] * (len(line) - 1)
        gap = b["sp"]
        x = x_right
        if align == "justify" and i < len(b["lines"]) - 1 and len(line) > 1 and natural > maxw * 0.88:
            gap = (maxw - words) / (len(line) - 1)
        if align == "center":
            x = x_right - (maxw - natural) / 2
        top = y + i * s * b["lh"]
        placed, run = [], None
        for vis, hi, wd, _ in line:
            placed.append((vis, hi, x))
            if hi:
                run = [x - wd, run[1] if run else x]  # neighbouring marked words share one mark
            elif run:
                mark and mark(d, run[0], top, run[1], top + s * 1.12, s)
                run = None
            x -= wd + gap
        if run and mark:
            mark(d, run[0], top, run[1], top + s * 1.12, s)
        for vis, hi, xr in placed:
            d.text((xr, top), vis, font=f, fill=acc if hi else ink, anchor="ra")
    return height(b)


# ---------- textures ----------

def grain(img, amount):
    noise = Image.effect_noise(img.size, 64).convert("L")
    noise = ImageOps.autocontrast(noise)
    layer = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, layer, amount)


def halftone(d, box, color, step=22, max_r=9, direction=1):
    x0, y0, x1, y1 = box
    rows = int((y1 - y0) / step) + 1
    for r in range(rows):
        y = y0 + r * step
        frac = r / max(1, rows - 1)
        rad = max_r * (frac if direction > 0 else 1 - frac)
        if rad < 0.8:
            continue
        off = step / 2 if r % 2 else 0
        x = x0 + off
        while x < x1:
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=color)
            x += step


def stripes(d, colors, corner="br"):
    """Three thick concentric quarter rings in a corner, a seventies sign."""
    cx, cy = (W, H) if corner == "br" else (0, 0)
    r = 330
    for c in colors:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
        r -= 56
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=STYLE["bg"])


# ---------- slides ----------

STYLE = {}


def footer(d, i, n, handle, first):
    f = font(30, 600)
    if handle:
        d.text((W - PAD, H - 78), get_display(handle, base_dir="L"), font=f, fill=STYLE["soft"], anchor="ra")
    if first and STYLE.get("swipe"):
        d.text((PAD, H - 78), get_display(STYLE["swipe"], base_dir="R"), font=f, fill=STYLE["accent_text"], anchor="la")
    elif not first and i < n - 1:
        d.text((PAD, H - 78), "%d / %d" % (i + 1, n), font=f, fill=STYLE["soft"], anchor="la")


def make_mark(kind):
    if kind == "glow":
        def mark(d, x0, y0, x1, y1, s):
            pad = s * 0.08
            d.rounded_rectangle((x0 - pad, y0 + s * 0.10, x1 + pad, y1 + s * 0.04), radius=int(s * 0.10),
                                fill=STYLE["accent2_rgb"])
        return mark
    if kind == "under":
        def mark(d, x0, y0, x1, y1, s):
            d.rectangle((x0, y1 - s * 0.02, x1, y1 + s * 0.07), fill=STYLE.get("mark_rgb", STYLE["accent_rgb"]))
        return mark
    return None


def render_slide(slide, i, n, handle, photo):
    st = STYLE["name"]
    first, last = i == 0, i == n - 1 and n > 1
    bg, ink, soft = STYLE["bg_rgb"], STYLE["ink_rgb"], STYLE["soft_rgb"]
    acc = STYLE["accent_rgb"]
    if st == "poster" and not first and i % 2 == 1:
        bg, ink, soft, acc = STYLE["accent_rgb"], STYLE["bg_rgb"], STYLE["bg_rgb"], STYLE["accent2_rgb"]
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    maxw = W - 2 * PAD
    title, text = slide.get("title", ""), slide.get("text", "")
    mark = None

    if st == "night":
        glow = Image.new("RGB", (W, H), bg)
        gd = ImageDraw.Draw(glow)
        gd.ellipse((W * 0.35, -300, W * 1.4, 500), fill=STYLE["accent2_rgb"])
        img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)
        d = ImageDraw.Draw(img)
        STYLE["accent2_rgb"] = hexrgb(STYLE["accent"])
        mark = make_mark("glow")
        acc = bg  # the marked word is cut out of the yellow highlighter
    elif st == "poster":
        STYLE["mark_rgb"] = acc  # on an inverted slide the accent is the background, so the line takes the word's colour
        mark = make_mark("under")
    elif st == "retro":
        stripes(d, [hexrgb(STYLE["accent"]), hexrgb(STYLE["accent2"]), hexrgb(STYLE["ink"])], "tl")
    elif st == "riso":
        halftone(d, (0, 24, W, 140), STYLE["accent_rgb"], direction=-1)
    elif st == "editorial" and not first and not last:
        gf = font(560, 800)
        d.text((PAD - 30, -70), "%02d" % (i + 1), font=gf, fill=STYLE["accent2_rgb"], anchor="la")

    if photo and first:
        try:
            ph = ImageOps.fit(ImageOps.exif_transpose(Image.open(photo)).convert("RGB"), (W, H))
            img.paste(ph, (0, 0))
            shade = Image.linear_gradient("L").resize((W, H))
            dark = Image.new("RGB", (W, H), (0, 0, 0))
            img = Image.composite(dark, img, shade.point(lambda v: int(min(255, 40 + v * 1.1) * 0.85)))
            d = ImageDraw.Draw(img)
            ink, soft, mark, acc = (255, 255, 255), (230, 230, 230), make_mark("under"), STYLE["accent_rgb"]
            STYLE["mark_rgb"] = acc
        except Exception as e:  # a bad photo never stops the carousel
            STYLE["photo_error"] = str(e)
            photo = None

    if first:
        big = 168 if st == "poster" else 144
        t = fit(title, 800 if st in ("poster", "night") else 700, big, 72, maxw, 6, 1.06, 780)
        b = fit(text, 400, 56, 36, maxw, 3, 1.36, 270) if text else None
        gap = 44 if b else 0
        block = height(t) + gap + height(b)
        top = (H - 140 - block) if photo else max(170, (H - block) / 2 - 30)
        if st == "riso":
            off = dict(t)
            draw_block(d, off, top + 7, W - PAD + 7, maxw, "right", STYLE["accent_rgb"], STYLE["accent_rgb"])
        if not photo and st in ("editorial", "night"):
            d.rectangle((W - PAD - 120, top - 54, W - PAD, top - 40), fill=STYLE["accent_rgb"])
        y = top + draw_block(d, t, top, W - PAD, maxw, "right", ink, acc, mark) + gap
        if b:
            draw_block(d, b, y, W - PAD, maxw, "right", soft, acc)
    elif last:
        t = fit(title, 800 if st == "poster" else 700, 120, 60, maxw, 5, 1.1, 580)
        b = fit(text, 600, 60, 36, maxw, 4, 1.36, 330) if text else None
        gap = 56 if b else 0
        block = height(t) + gap + height(b)
        top = max(180, (H - block) / 2 - 40)
        y = top + draw_block(d, t, top, W - PAD, maxw, "center", ink, acc, mark) + gap
        if b:
            pill_acc = STYLE["accent_rgb"] if st != "poster" or i % 2 == 0 else STYLE["accent2_rgb"]
            draw_block(d, b, y, W - PAD, maxw, "center", pill_acc, pill_acc)
    else:
        big = 124 if st == "poster" else 104
        t = fit(title, 800 if st == "poster" else 700, big, 56, maxw, 4, 1.1, 500)
        room = FLOOR - 230 - height(t) - 48
        b = fit(text, 400, 58, 34, maxw, 9, 1.45, room) if text else None
        gap = 48 if b else 0
        block = height(t) + gap + height(b)
        top = max(230, (H - block) / 2 - 20)
        if st == "riso":
            draw_block(d, dict(t), top + 6, W - PAD + 6, maxw, "right", STYLE["accent_rgb"], STYLE["accent_rgb"])
        y = top + draw_block(d, t, top, W - PAD, maxw, "right", ink, acc, mark) + gap
        if b:
            draw_block(d, b, y, W - PAD, maxw, "justify", ink if st != "night" else soft, acc)

    STYLE["accent_text"] = (255, 255, 255) if photo and first else STYLE["accent_rgb"]
    if st in ("night", "riso"):
        img = grain(img, 0.06 if st == "night" else 0.08)
        d = ImageDraw.Draw(img)
    saved_soft = STYLE["soft"]
    if (st == "poster" and not first and i % 2 == 1) or (photo and first):
        STYLE["soft"] = ink
    footer(d, i, n, handle, first)
    STYLE["soft"] = saved_soft
    problems = []
    if not bidi_ok(t) or (b is not None and not bidi_ok(b)):
        problems.append("mixed_direction: reword the line that mixes Hebrew and English or numbers")
    if not t["ok"]:
        problems.append("title_too_long")
    if b is not None and not b["ok"]:
        problems.append("text_too_long")
    return img, {"slide": i + 1, "title_size": t["size"], "text_size": b["size"] if b else None,
                 "problems": problems}


def contrast(c1, c2):
    def lum(c):
        ch = [v / 255 for v in c]
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    hi, lo = sorted((lum(c1), lum(c2)), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)


def sheet(paths, out):
    thumbs = [Image.open(p).resize((270, 338)) for p in paths]
    cols = min(5, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    s = Image.new("RGB", (cols * 280 + 10, rows * 348 + 10), (128, 128, 128))
    for k, t in enumerate(thumbs):
        c = cols - 1 - (k % cols)  # first slide on the right, the way a Hebrew reader scans
        s.paste(t, (10 + c * 280, 10 + (k // cols) * 348))
    s.save(out)


HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
LOOK_NAMES = {"night": "לילה", "poster": "פוסטר", "editorial": "עורכתי", "retro": "רטרו", "riso": "ריזו"}


def fail(msg):
    """A clear one-line error for the caller, never a traceback."""
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(2)


def setup(name, colors):
    STYLE.clear()
    STYLE.update(STYLES[name])
    for k, v in (colors or {}).items():
        if k in ("bg", "ink", "soft", "accent", "accent2") and v:
            STYLE[k] = v
    STYLE["name"] = name
    for k in ("bg", "ink", "soft", "accent", "accent2"):
        STYLE[k + "_rgb"] = hexrgb(STYLE[k])


def contrast_warnings():
    """Every colour pair the slides really draw, with the WCAG threshold for its text size."""
    pairs = [("text on background", STYLE["ink_rgb"], STYLE["bg_rgb"], 4.5),
             ("soft text on background", STYLE["soft_rgb"], STYLE["bg_rgb"], 3),
             ("accent on background", STYLE["accent_rgb"], STYLE["bg_rgb"], 3)]
    if STYLE["name"] == "night":
        pairs = pairs[:2] + [("marked word on the highlighter", STYLE["bg_rgb"], STYLE["accent_rgb"], 3)]
    if STYLE["name"] == "poster":
        pairs += [("text on the inverted slides", STYLE["bg_rgb"], STYLE["accent_rgb"], 3),
                  ("marked word on the inverted slides", STYLE["accent2_rgb"], STYLE["accent_rgb"], 3)]
    out = []
    for label, fg, bg, need in pairs:
        c = contrast(fg, bg)
        if c < need:
            out.append("low_contrast: %s is %.2f, needs %s" % (label, c, need))
    return out


def preview(spec, out):
    """The owner's own cover slide in all five looks, side by side, so they choose by looking.
    The owner's colours apply only when the spec has them (a saved brief)."""
    first = next((s for s in spec.get("slides", []) if isinstance(s, dict) and (s.get("title") or s.get("text"))), None)
    if not first:
        fail("No slides in the spec.")
    handle = (spec.get("handle") or "").strip()
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    tiles = []
    for name in ("night", "poster", "editorial", "retro", "riso"):
        setup(name, spec.get("colors"))
        STYLE["swipe"] = spec.get("swipe", "החליקו")
        STYLE["accent2_rgb"] = hexrgb(STYLE["accent2"])
        img, _ = render_slide(first, 0, 8, handle, None)
        tiles.append((name, img.resize((360, 450), Image.LANCZOS)))
    sheet_img = Image.new("RGB", (5 * 372 + 12, 450 + 80), (245, 245, 245))
    d = ImageDraw.Draw(sheet_img)
    for k, (name, t) in enumerate(tiles):
        x = 12 + (4 - k) * 372  # number 1 on the right, the way a Hebrew reader scans
        sheet_img.paste(t, (x, 12))
        label = "%d  %s" % (k + 1, LOOK_NAMES[name])
        d.text((x + 180, 450 + 46), get_display(label, base_dir="R"), font=font(34, 700), fill=(20, 20, 20), anchor="mm")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "looks.png")
    sheet_img.save(path, optimize=True)
    print(json.dumps({"ok": True, "preview": os.path.abspath(path),
                      "order": ["%d %s" % (k + 1, n) for k, (n, _) in enumerate(tiles)]}, ensure_ascii=False, indent=1))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    spec_path = sys.argv[1]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv and sys.argv.index("--out") + 1 < len(sys.argv) else "carousel"
    try:
        with open(spec_path, encoding="utf-8") as fh:
            spec = json.load(fh)
    except Exception as e:
        fail("Cannot read the spec %s: %s" % (spec_path, e))
    if not isinstance(spec, dict):
        fail("The spec must be a JSON object.")
    bad = [k + "=" + str(v) for k, v in (spec.get("colors") or {}).items() if v and not HEX.match(str(v))]
    if bad:
        fail("Colours must be hex codes like #2C3140. Fix: " + ", ".join(bad))
    raw = spec.get("slides", [])
    if not isinstance(raw, list) or any(not isinstance(s, dict) for s in raw):
        fail('slides must be a list of objects like {"title": "...", "text": "..."}.')
    if "--preview" in sys.argv:
        preview(spec, out)
        return
    name = spec.get("style", "editorial")
    if name not in STYLES:
        fail("Unknown style %r. Use one of: %s" % (name, ", ".join(STYLES)))
    setup(name, spec.get("colors"))
    STYLE["swipe"] = spec.get("swipe", "החליקו")
    slides = [s for s in raw if (s.get("title") or s.get("text"))]
    warnings = []
    if len(slides) > 10:
        warnings.append("too_many_slides: Instagram takes 10 at most here, only the first 10 were drawn")
        slides = slides[:10]
    if not slides:
        fail("No slides in the spec.")
    handle = (spec.get("handle") or "").strip()
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    photo = spec.get("photo")
    if photo and not os.path.exists(photo):
        photo = None
    os.makedirs(out, exist_ok=True)
    paths, report = [], []
    for i, s in enumerate(slides):
        STYLE["accent2_rgb"] = hexrgb(STYLE["accent2"])
        STYLE.pop("mark_rgb", None)
        img, r = render_slide(s, i, len(slides), handle, photo)
        p = os.path.join(out, "slide-%02d.png" % (i + 1))
        img.save(p, optimize=True)
        paths.append(p)
        report.append(r)
    sheet(paths, os.path.join(out, "all-slides.png"))
    STYLE["accent2_rgb"] = hexrgb(STYLE["accent2"])
    warnings += contrast_warnings()
    if STYLE.get("photo_error"):
        warnings.append("photo_error: " + STYLE["photo_error"])
    if spec.get("photo") and not photo:
        warnings.append("photo_not_found: " + str(spec.get("photo")))
    print(json.dumps({"style": name, "folder": os.path.abspath(out), "slides": report,
                      "warnings": warnings, "ok": not warnings and not any(r["problems"] for r in report)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
