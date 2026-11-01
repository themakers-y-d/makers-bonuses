#!/usr/bin/env python3
"""Samples the colours that repeat across the owner's own photos, and measures contrast.

Usage:  python3 colors.py photo1.jpg photo2.png ... [--keep 6]

Each photo is shrunk and reduced to its eight main colours. Colours that are close to
each other across photos are merged, and a colour is kept only if it shows up in at
least two photos (or in the only photo given). Prints a JSON report:
  colors:  up to --keep colours, the most common first, each with its hex code, its
           share of the pixels and how many photos it appears in
  accents: up to three strong colours that cover only a small part of the photos (a
           logo, a button, a glaze). Brand colours often live here, so show them too
  pairs:   the contrast ratio of every two kept colours. 4.5 and up reads as text on
           that background; below that, the pair is for surfaces and small marks only
Needs only Pillow. Nothing is downloaded.
"""
import colorsys, json, os, sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is missing. Run: pip install pillow  (or: python3 -m pip install --user pillow)")

CLOSE = 30  # two colours closer than this (RGB distance) count as one


def lum(c):
    ch = [v / 255 for v in c]
    ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(c1, c2):
    hi, lo = sorted((lum(c1), lum(c2)), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def main_colors(path):
    img = Image.open(path)
    if img.format == "JPEG":
        img.draft("RGB", (400, 400))  # decode a small version, so a huge photo does not fill the memory
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        # transparent pixels would turn black; lay the image on white, like a logo on a page
        rgba = img.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(white, rgba)
    img = img.convert("RGB")
    img.thumbnail((200, 200))
    q = img.quantize(colors=16, method=0)  # 0 = median cut, works on old and new Pillow
    pal = q.getpalette()
    counts = q.getcolors() or []
    total = sum(n for n, _ in counts) or 1
    return [(tuple(pal[i * 3:i * 3 + 3]), n / total) for n, i in counts]


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    keep = 6
    if "--keep" in args:
        k = args.index("--keep")
        if k + 1 >= len(args) or not args[k + 1].isdigit():
            sys.exit("--keep needs a number, like --keep 6")
        keep = int(args[k + 1])
        args = args[:k] + args[k + 2:]
    clusters, errors, used = [], [], 0
    for p in args:
        try:
            found = main_colors(p)
        except Exception as e:
            errors.append("%s: %s" % (os.path.basename(p), e))
            continue
        used += 1
        for rgb, share in found:
            for c in clusters:
                if dist(c["rgb"], rgb) < CLOSE:
                    w = c["share"] + share
                    c["rgb"] = tuple(round((a * c["share"] + b * share) / w) for a, b in zip(c["rgb"], rgb))
                    c["share"] = w
                    c["photos"].add(p)
                    break
            else:
                clusters.append({"rgb": rgb, "share": share, "photos": {p}})
    if not used:
        sys.exit("No photo could be read. " + "; ".join(errors))
    need = 2 if used > 1 else 1
    # a colour must also cover about 1% of a photo, so JPEG edges and anti-aliasing do not count as colours
    kept = sorted([c for c in clusters if len(c["photos"]) >= need and c["share"] / used >= 0.01],
                  key=lambda c: -c["share"])[:keep]
    def strong(c):
        h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c["rgb"]])
        return s > 0.35 and v > 0.2
    rest = [c for c in clusters if c not in kept and strong(c) and c["share"] / used >= 0.005]
    accents = [{"hex": "#%02X%02X%02X" % c["rgb"], "share": round(c["share"] / used, 3), "photos": len(c["photos"])}
               for c in sorted(rest, key=lambda c: -c["share"])[:3]]
    hexes = ["#%02X%02X%02X" % c["rgb"] for c in kept]
    colors = [{"hex": h, "share": round(c["share"] / used, 3), "photos": len(c["photos"])} for h, c in zip(hexes, kept)]
    pairs = []
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            r = contrast(kept[i]["rgb"], kept[j]["rgb"])
            pairs.append({"a": hexes[i], "b": hexes[j], "ratio": r, "text_ok": r >= 4.5})
    pairs.sort(key=lambda p: -p["ratio"])
    print(json.dumps({"photos_read": used, "colors": colors, "accents": accents, "pairs": pairs, "errors": errors},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
