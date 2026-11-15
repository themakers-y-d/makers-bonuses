#!/usr/bin/env python3
"""build_map.py: turns map.json into one designed HTML page, the owner's agent map.

Usage:
  python3 build_map.py map.json [--out DIR] [--open]

Only the Python standard library. Works on Mac, Windows and Linux, and in the
Claude app's code sandbox. The fonts sit next to this script (../fonts), so
nothing is downloaded except the display font, which the page loads from
themakers.co.il when it is online and falls back to Assistant when it is not.

The script, not the model, computes the hours. The model gives the hours the
owner said per task (hours_now) and the autonomy mode; the saving is a fixed
share of that number, so the same answers always give the same estimate.

Prints one JSON report. "ok": true means the file was written and every check
passed. Otherwise "issues" says what to fix in map.json, and nothing is written.
"""
import argparse
import base64
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "assets", "map.html")
FONTS = os.path.join(ROOT, "fonts")

# share of the owner's own hours that comes back, by how much the agent does alone
MODES = {
    "alone":   {"label": "עובד לבד",        "level": 3, "share": (0.6, 0.8),
                "how": "הוא עושה את זה לבד, ואתם מציצים בתוצאה"},
    "approve": {"label": "מכין, אתם מאשרים", "level": 2, "share": (0.4, 0.6),
                "how": "הוא מכין, ואתם מאשרים לפני שזה יוצא"},
    "assist":  {"label": "עוזר לכם",         "level": 1, "share": (0.2, 0.4),
                "how": "הוא מכין את החומר, והעבודה עצמה נשארת שלכם"},
}
LIMITS = {"business": 40, "serves": 140, "answer": 170, "name": 34, "does": 180,
          "replaces": 160, "hours_said": 70, "first_step": 230, "kickoff": 420, "why": 760}
FORBIDDEN = [
    ("long_dash", re.compile("[–—―־]")),
    ("spaced_hyphen", re.compile(r"\s-\s")),
    ("angle_bracket", re.compile("[<>]")),
    ("emoji_or_symbol", re.compile("[←-⇿☀-➿⬀-⯿\U0001f000-\U0001faff️]")),
    ("markdown", re.compile(r"\*\*|__|^#", re.M)),
]
LATIN_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.,:%+&'/ ]*[A-Za-z0-9%]|[A-Za-z0-9]")


def out(report, code=0):
    # ASCII-safe JSON: a Windows console in cp1252 cannot print Hebrew, and a crash here looks like a failed build
    print(json.dumps(report, ensure_ascii=True, indent=1))
    sys.exit(code)


def esc(s):
    return html.escape(str(s), quote=True)


def display(s):
    """Escape, and set Latin letters and digits in Assistant, because Caspomat has no Latin glyphs."""
    parts, last = [], 0
    for m in LATIN_RUN.finditer(s):
        parts.append(esc(s[last:m.start()]))
        parts.append('<span class="lat">' + esc(m.group(0)) + "</span>")
        last = m.end()
    parts.append(esc(s[last:]))
    return "".join(parts)


def half(x):
    return round(x * 2) / 2


def num(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def hours_words(x):
    words = {0.5: "חצי שעה", 1: "שעה", 1.5: "שעה וחצי", 2: "שעתיים"}
    return words.get(x, num(x) + " שעות")


def span_words(lo, hi):
    if lo == hi:
        return hours_words(lo)
    if hi <= 2:
        return hours_words(lo) + " עד " + hours_words(hi)
    return num(lo) + " עד " + num(hi) + " שעות"


def font_faces():
    def b64(name):
        with open(os.path.join(FONTS, name), "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    heb = "U+0590-05FF,U+200C-2010,U+20AA,U+25CC,U+FB1D-FB4F"
    lat = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2212,U+FEFF"
    faces = [
        "@font-face{font-family:'Assistant';font-weight:400 700;font-display:swap;"
        "src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:%s}" % (b64("assistant-hebrew.woff2"), heb),
        "@font-face{font-family:'Assistant';font-weight:400 700;font-display:swap;"
        "src:url(data:font/woff2;base64,%s) format('woff2');unicode-range:%s}" % (b64("assistant-latin.woff2"), lat),
    ]
    # the display font of MAKERS, loaded from the site (it allows any origin). Offline, the headings fall back to Assistant.
    for w in (300, 400):
        faces.append("@font-face{font-family:'Caspomat';font-weight:%d;font-display:swap;"
                     "src:url(https://themakers.co.il/fonts/caspomat-%d.woff2) format('woff2');"
                     "unicode-range:U+0020-002F,U+003A-0040,U+005B-0060,U+007B-007E,U+0590-05FF,U+FB1D-FB4F}" % (w, w))
    return "\n".join(faces)


def check(spec):
    issues = []

    def text(where, value, limit_key, required=True):
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                issues.append({"where": where, "problem": "missing"})
            return
        if not isinstance(value, str):
            issues.append({"where": where, "problem": "must_be_text"})
            return
        lim = LIMITS[limit_key]
        if len(value) > lim:
            issues.append({"where": where, "problem": "too_long", "length": len(value), "limit": lim})
        for name, rx in FORBIDDEN:
            if rx.search(value):
                issues.append({"where": where, "problem": name})

    text("business", spec.get("business"), "business")
    text("serves", spec.get("serves"), "serves")
    answers = spec.get("answers")
    if not isinstance(answers, list) or len(answers) != 6:
        issues.append({"where": "answers", "problem": "need_exactly_6"})
    else:
        for i, a in enumerate(answers):
            text("answers[%d]" % i, a, "answer")
    agents = spec.get("agents")
    if not isinstance(agents, list) or len(agents) != 3:
        issues.append({"where": "agents", "problem": "need_exactly_3"})
        agents = []
    names = set()
    for i, a in enumerate(agents):
        w = "agents[%d]" % i
        if not isinstance(a, dict):
            issues.append({"where": w, "problem": "must_be_object"})
            continue
        for k in ("name", "does", "replaces", "first_step"):
            text(w + "." + k, a.get(k), k)
        n = (a.get("name") or "").strip()
        if n in names:
            issues.append({"where": w + ".name", "problem": "duplicate_name"})
        names.add(n)
        if a.get("mode") not in MODES:
            issues.append({"where": w + ".mode", "problem": "mode_must_be_alone_approve_or_assist"})
        h = a.get("hours_now")
        if h is not None:
            if not isinstance(h, (int, float)) or isinstance(h, bool) or not (0 < h <= 80):
                issues.append({"where": w + ".hours_now", "problem": "number_between_0_and_80_or_null"})
            text(w + ".hours_said", a.get("hours_said"), "hours_said")
    text("kickoff", spec.get("kickoff"), "kickoff")
    text("why", spec.get("why"), "why")
    return issues


def build(spec):
    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()
    date = spec.get("date") or datetime.date.today().strftime("%d.%m.%Y")
    stations, tot_lo, tot_hi, counted, est = [], 0.0, 0.0, 0, []
    for i, a in enumerate(spec["agents"], 1):
        m = MODES[a["mode"]]
        h = a.get("hours_now")
        if h is None:
            save = '<span class="save">לא הערכתי</span><span class="math">לא נתתם מספר שעות למשימה הזאת, ולכן אין כאן הערכה.</span>'
            est.append(None)
        else:
            lo, hi = half(h * m["share"][0]), half(h * m["share"][1])
            lo = max(lo, 0.5)
            hi = max(hi, lo)
            tot_lo += lo; tot_hi += hi; counted += 1
            est.append([lo, hi])
            save = ('<span class="save">בערך %s בשבוע</span><span class="math">אמרתם: %s. %s, ולכן זו ההערכה. '
                    'היא נגזרת רק מהמספר שלכם.</span>') % (esc(span_words(lo, hi)), esc(a["hours_said"]), esc(m["how"]))
        stations.append(
            '      <li class="st">\n'
            '        <div class="pin" aria-hidden="true">%d</div>\n'
            '        <article class="card">\n%s'
            '          <div class="card-head"><h3>%s</h3>'
            '<span class="auto"><span class="meter" data-level="%d"><i></i><i></i><i></i></span>%s</span></div>\n'
            '          <p class="does">%s</p>\n'
            '          <dl class="rows">\n'
            '            <div><dt>מה זה מחליף</dt><dd>%s</dd></div>\n'
            '            <div><dt>זמן שחוזר אליכם</dt><dd>%s</dd></div>\n'
            '          </dl>\n'
            '          <div class="first"><span class="tag">הצעד הראשון, היום</span><p>%s</p></div>\n'
            '        </article>\n'
            '      </li>' % (i, ('          <span class="start">מתחילים כאן</span>\n' if i == 1 else ''), display(a["name"]), m["level"], esc(m["label"]), esc(a["does"]),
                             esc(a["replaces"]), save, esc(a["first_step"])))
    if counted:
        rng = num(tot_lo) if tot_lo == tot_hi else num(tot_lo) + " עד " + num(tot_hi)
        note = "שעות בשבוע שחוזרות אליכם, הערכה לפי המספרים שלכם"
        if tot_lo == tot_hi and tot_lo <= 1:
            rng = "חצי" if tot_lo == 0.5 else "1"
            note = "שעה בשבוע שחוזרת אליכם, הערכה לפי המספרים שלכם"
        if counted < 3:
            note += ", רק במשימות שנתתם להן מספר"
        total = '<b>%s</b><span>%s</span>' % (esc(rng), note)
    else:
        total = '<b class="words">בלי ניחושים</b><span>לא נתתם מספרי שעות, ולכן לא הערכתי כמה זמן חוזר</span>'
    first = spec["agents"][0]
    nxt = (
        '        <li><span class="when">היום</span><p><strong>%s.</strong> %s</p></li>\n'
        '        <li><span class="when">מחר</span><p><strong>פותחים שיחה חדשה עם Claude</strong> ומדביקים את המשפט הזה, '
        'יחד עם מה שאספתם היום:</p></li>\n'
        '        <li><span class="when" aria-hidden="true"></span><div class="copy"><p id="kickoff">%s</p>'
        '<button type="button" data-copy="kickoff">העתקה</button><span class="done" aria-live="polite"></span></div></li>\n'
        '        <li><span class="when">יום אחרי</span><p><strong>מריצים אותו על מקרה אמיתי אחד</strong>, ומתקנים אותו במילים שלכם '
        'עד שהתוצאה נראית כמו שלכם. רק כשהוא עובד, עוברים לסוכן 2.</p></li>'
    ) % (esc(first["name"]), esc(first["first_step"]), esc(spec["kickoff"]))
    why = "\n".join('      <p>%s</p>' % esc(p.strip()) for p in spec["why"].split("\n") if p.strip())
    labels = ["העסק ולמי הוא משרת", "מה חוזר כל שבוע", "לאן הולך רוב הזמן",
              "מה הכי שנוא", "הכלים שכבר יש", "מה היה קורה לבד"]
    told = "\n".join('      <div><dt>%s</dt><dd>%s</dd></div>' % (esc(l), esc(a)) for l, a in zip(labels, spec["answers"]))
    biz = spec["business"].strip()
    fill = {
        "{{TITLE}}": esc("המפה של " + biz),
        "{{EYEBROW}}": esc("המפה שלכם · " + date),
        "{{H1}}": display("שלושת הסוכנים הראשונים של " + biz),
        "{{LEAD}}": esc(spec["serves"]),
        "{{TOTAL}}": total,
        "{{STATIONS}}": "\n".join(stations),
        "{{WHY}}": why,
        "{{NEXT}}": nxt,
        "{{TOLD}}": told,
        "{{FOOT}}": esc("נבנה ב-" + date + " מהתשובות שלכם בלבד. הזמנים הם הערכה לפי המספרים שנתתם, לא הבטחה."),
        "{{FONTS}}": font_faces(),
    }
    for k, v in fill.items():
        page = page.replace(k, v)
    left = re.findall(r"\{\{[A-Z]+\}\}", page)
    return page, left, ([tot_lo, tot_hi] if counted else None), est


def open_file(path):
    if os.environ.get("AGENT_MAP_NO_OPEN"):
        return "skipped"
    try:
        if sys.platform == "darwin" and shutil.which("open"):
            subprocess.Popen([shutil.which("open"), path]); return "opened"
        if os.name == "nt":
            os.startfile(path); return "opened"  # noqa
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return "opened"
    except Exception as e:  # opening is a courtesy; the file is already written
        return "failed: " + str(e)[:120]
    return "no_opener"


def main():
    ap = argparse.ArgumentParser(description="Builds the agent map page from map.json.")
    ap.add_argument("spec", help="path to map.json (UTF-8)")
    ap.add_argument("--out", default="agent-map", help="folder for the page (default: ./agent-map)")
    ap.add_argument("--open", action="store_true", help="open the page in the browser after writing it")
    args = ap.parse_args()
    try:
        with open(args.spec, encoding="utf-8-sig") as f:
            spec = json.load(f)
    except (OSError, ValueError) as e:
        out({"ok": False, "error": "cannot read map.json: " + str(e)[:200]}, 1)
    if not isinstance(spec, dict):
        out({"ok": False, "error": "map.json must be one JSON object"}, 1)
    issues = check(spec)
    if issues:
        out({"ok": False, "issues": issues}, 2)
    page, left, total, est = build(spec)
    if left:
        out({"ok": False, "error": "template placeholders left: " + ",".join(left)}, 1)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.abspath(os.path.join(args.out, "my-agent-map.html"))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    keep = os.path.abspath(os.path.join(args.out, "map.json"))
    if os.path.abspath(args.spec) != keep:
        shutil.copyfile(args.spec, keep)
    rep = {"ok": True, "file": path, "answers_saved": keep, "hours_total": total, "hours_per_agent": est}
    if args.open:
        rep["open"] = open_file(path)
    out(rep)


if __name__ == "__main__":
    main()
