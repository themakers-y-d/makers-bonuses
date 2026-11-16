#!/usr/bin/env python3
"""Pictures of what was on the screen, so the video can be read with the eyes and not only the ears.

Usage:  bash run.sh frames.py VIDEO --out FOLDER [--max 24] [--start M:SS] [--end M:SS]

Picks the moments where the picture changes most (a new screen, a new slide, a new caption), and fills the gaps
evenly, then lays them out six to a sheet, each with its time in the corner. Writes sheet-1.jpg, sheet-2.jpg ...
into FOLDER and prints, last:  FRAMES READY <n> frames on <k> sheets in <folder>
Nothing downloads and nothing leaves the computer. Needs av and Pillow (install-tools.sh base).
"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def die(msg):
    print("PROBLEM " + msg, flush=True)
    sys.exit(1)


def secs(v):
    if v is None:
        return None
    p = [float(x) for x in str(v).split(":")]
    return sum(x * 60 ** i for i, x in enumerate(reversed(p)))


def stamp(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    try:
        import av
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        die("the picture tools are not installed. Run install-tools.sh base, then this again.")

    def opt(name, default=None):
        if name in a:
            i = a.index(name)
            return a[i + 1] if i + 1 < len(a) else default
        return default

    src = Path(a[0]).expanduser()
    if not src.is_file():
        die(f"no video at {src}")
    out = Path(opt("--out", str(src.parent / "frames")))
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("sheet-*.jpg"):
        old.unlink()
    most = max(6, min(48, int(opt("--max", "24"))))

    try:
        box = av.open(str(src))
    except Exception as e:
        die(f"cannot open {src.name} ({type(e).__name__})")
    if not box.streams.video:
        die("this file has no picture, only sound. Continue with the words alone.")
    vs = box.streams.video[0]
    dur = float(box.duration / 1e6) if box.duration else float(vs.duration * vs.time_base) if vs.duration else 0
    t0 = secs(opt("--start")) or 0.0
    t1 = min(dur, secs(opt("--end")) or dur) if dur else (secs(opt("--end")) or 0)
    if t1 - t0 < 1:
        die("the video is too short, or the times are outside it.")

    # one small picture every `step` seconds, decoded in a single pass (no seeking, so it works on any file)
    step = max(0.5, (t1 - t0) / 240)
    thumbs, nxt = [], t0
    for frame in box.decode(vs):
        t = float(frame.pts * vs.time_base) if frame.pts is not None else None
        if t is None or t < nxt:
            continue
        if t > t1:
            break
        img = frame.to_image()
        thumbs.append((t, img.convert("L").resize((48, 27)), img))
        nxt = t + step
        if len(thumbs) > 400:
            break
    box.close()
    if not thumbs:
        die("no pictures could be read from this video.")

    # change from the previous picture; a big change is a new screen
    def diff(x, y):
        return sum(abs(p - q) for p, q in zip(x.getdata(), y.getdata())) / (48 * 27)

    scored = [(diff(thumbs[i - 1][1], thumbs[i][1]) if i else 255.0, i) for i in range(len(thumbs))]
    gap = (t1 - t0) / (most * 1.5)
    chosen = []
    for score, i in sorted(scored, reverse=True):
        if score < 12 or len(chosen) >= most * 2 // 3:
            break
        if all(abs(thumbs[i][0] - thumbs[j][0]) >= gap for j in chosen):
            chosen.append(i)
    # fill the quiet stretches evenly, so a long screen with small changes is still seen
    n = len(thumbs)
    for k in range(most):
        if len(chosen) >= most:
            break
        i = min(n - 1, int(k * n / most))
        if all(abs(thumbs[i][0] - thumbs[j][0]) >= gap / 2 for j in chosen):
            chosen.append(i)
    chosen = sorted(set(chosen))[:most]

    font = ImageFont.load_default(size=26) if hasattr(ImageFont, "load_default") else None
    tw = 640
    sheets = 0
    for s in range(0, len(chosen), 6):
        group = chosen[s:s + 6]
        tiles = []
        for i in group:
            t, _g, img = thumbs[i]
            th = int(img.height * tw / img.width)
            tile = img.convert("RGB").resize((tw, th))
            d = ImageDraw.Draw(tile)
            label = stamp(t)
            d.rectangle([0, 0, 92, 36], fill=(0, 0, 0))
            d.text((10, 4), label, fill=(255, 255, 255), font=font)
            tiles.append(tile)
        th = max(t.height for t in tiles)
        cols = 3
        if th > 900:  # tall phone video: shrink so a sheet stays readable
            tiles = [t.resize((int(t.width * 900 / t.height), 900)) for t in tiles]
            th = 900
        cw = tiles[0].width
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw + (cols - 1) * 6, rows * th + (rows - 1) * 6), (255, 255, 255))
        for k, tile in enumerate(tiles):
            sheet.paste(tile, ((k % cols) * (cw + 6), (k // cols) * (th + 6)))
        if sheet.width > 2000:
            sheet = sheet.resize((2000, int(sheet.height * 2000 / sheet.width)))
        sheets += 1
        sheet.save(out / f"sheet-{sheets}.jpg", quality=82)
    print(f"FRAMES READY {len(chosen)} frames on {sheets} sheets in {out}", flush=True)


if __name__ == "__main__":
    main()
