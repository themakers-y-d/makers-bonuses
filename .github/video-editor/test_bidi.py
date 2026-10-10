#!/usr/bin/env python3
"""Tests for the Hebrew line reordering both gifts draw captions and on-screen words with.

Pillow draws without a bidi engine, so the video editor (`bidi_visual` in edit.py) and the reel style builder
(`visual` in kit.py) reorder a logical Hebrew line into left-to-right drawing order themselves. Each case below
is the drawing order a right-to-left reader must get: English words and numbers keep their own order, and the
punctuation after them belongs to the Hebrew sentence. A comma after an English word sits on the English word's
left, toward the rest of the Hebrew sentence (",CapCut את לי"), never between the English word and the Hebrew
word before it ("CapCut, את לי", the bug a live run showed on screen).

Runs with any Python 3.8+ and no libraries.
Usage: python test_bidi.py [<path to edit.py> [<path to kit.py>]]
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDIT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "skills/video-editor/edit.py"
KIT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "skills/style-maker/kit.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# (logical line, drawing order from left to right)
CASES = [
    # an English word, then a comma: at the end of the line, and before more Hebrew
    ("לי את CapCut,", ",CapCut תא יל"),
    ("לי את CapCut, ואז", "זאו ,CapCut תא יל"),
    # an English word, then a period, after a Hebrew prefix with a hyphen
    ("עברתי ל-CapCut.", ".CapCut-ל יתרבע"),
    ("כתבו לי ב-Node.js, זה עובד", "דבוע הז ,Node.js-ב יל ובתכ"),
    # an English word, then a question mark
    ("מה זה GPT?", "?GPT הז המ"),
    ("מה זה GPT? תשובה", "הבושת ?GPT הז המ"),
    # an English word with a number, then a comma
    ("iPhone 15, הדגם", "םגדה ,iPhone 15"),
    ("GPT-4 עולה 20$.", ".20$ הלוע GPT-4"),
    # numbers in Hebrew, with their own punctuation and after it
    ("יש 3 דרכים, ו-2 טובות.", ".תובוט 2-ו ,םיכרד 3 שי"),
    ("זה עולה 20$.", ".20$ הלוע הז"),
    ("בשעה 10:30, אחרי", "ירחא ,10:30 העשב"),
    ("3.5 מיליון צפיות", "תויפצ ןוילימ 3.5"),
    ("הנחה של 100%!", "!100% לש החנה"),
    # the lines of the font test image
    ("שאלה? תשובה!", "!הבושת ?הלאש"),
    ("בלי WordPress ובלי Wix", "Wix ילבו WordPress ילב"),
    ("(בסוגריים) 100%", "100% (םיירגוסב)"),
]

fails = 0
for label, fn in (("edit.py bidi_visual", load("edit_under_test", EDIT).bidi_visual),
                  ("kit.py visual", load("kit_under_test", KIT).visual)):
    for logical, want in CASES:
        got = fn(logical)
        ok = got == want
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + f"{label}: {logical!r}" + ("" if ok else f"  got {got!r}, want {want!r}"))

# the two engines draw every line the same way, so a caption and an animated word never disagree
edit_fn, kit_fn = load("edit_same", EDIT).bidi_visual, load("kit_same", KIT).visual
for logical, _ in CASES:
    if edit_fn(logical) != kit_fn(logical):
        fails += 1
        print(f"FAIL the two engines differ on {logical!r}")

print(("ALL BIDI TESTS PASSED" if not fails else f"{fails} BIDI TESTS FAILED"))
sys.exit(1 if fails else 0)
