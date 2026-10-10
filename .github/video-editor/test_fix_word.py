#!/usr/bin/env python3
"""Tests for `edit.py fix-word`, the supported way to correct a misheard word.

Runs with any Python 3.10+ and no libraries: fix-word touches only words.json and transcript.txt.
Usage: python test_fix_word.py <path to edit.py>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

EDIT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "skills/video-editor/edit.py")
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail and not cond else ""))
    fails += 0 if cond else 1


def w(text, s, e, seg):
    return {"w": text, "s": s, "e": e, "p": 0.9, "seg": seg}


WORDS = [
    # line 1
    w("בניתי", 0.0, 0.4, 1), w("את", 0.45, 0.6, 1), w("מייקר,", 0.65, 1.1, 1), w("היום.", 1.15, 1.6, 1),
    # line 2
    w("באתר", 2.5, 2.9, 2), w("וורד", 3.0, 3.3, 2), w("פרס", 3.35, 3.8, 2), w("של", 3.85, 4.0, 2), w("מייקר", 4.05, 4.5, 2),
    # line 3
    w("שאלתי", 5.5, 5.9, 3), w("את", 5.95, 6.1, 3), w("צ'אטג'יפיטי", 6.15, 7.0, 3), w("וזהו.", 7.05, 7.5, 3),
]


def fresh(tmp):
    studio = Path(tmp) / "סטודיו עם רווח"
    video = Path(tmp) / "סרטון בדיקה.mp4"
    video.write_bytes(b"not really a video, fix-word never opens it" * 100)
    env = dict(os.environ, REEL_STUDIO=str(studio), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    # the job folder is created by the engine itself, the same way info and transcribe create it
    code = ("import sys, importlib.util; s = importlib.util.spec_from_file_location('e', sys.argv[1]); "
            "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.job_dir(m.Path(sys.argv[2]).resolve()))")
    jd = Path(subprocess.run([sys.executable, "-c", code, str(EDIT), str(video)], env=env, capture_output=True,
                             text=True, encoding="utf-8").stdout.strip())
    words = json.loads(json.dumps(WORDS))
    lines = []
    for n, (w0, w1) in enumerate([(0, 3), (4, 8), (9, 12)], 1):
        lines.append({"n": n, "start": words[w0]["s"], "end": words[w1]["e"],
                      "text": " ".join(x["w"] for x in words[w0:w1 + 1]), "w0": w0, "w1": w1})
        for i in range(w0, w1 + 1):
            words[i]["line"] = n
    (jd / "words.json").write_text(json.dumps({"model": "small", "lang": "he", "words": words, "lines": lines},
                                              ensure_ascii=False), encoding="utf-8")
    return video, jd, env


def run(video, env, *args):
    p = subprocess.run([sys.executable, str(EDIT), "fix-word", str(video), *args], env=env, capture_output=True,
                       text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


def load(jd):
    return json.loads((jd / "words.json").read_text(encoding="utf-8"))


with tempfile.TemporaryDirectory() as tmp:
    video, jd, env = fresh(tmp)
    before = load(jd)

    rc, out = run(video, env, "מייקר", "MAKERS")
    d = load(jd)
    check("one word, every place: exit 0 and FIXED in 2 places", rc == 0 and "in 2 places" in out, out)
    check("the punctuation after the word is kept", d["words"][2]["w"] == "MAKERS,", d["words"][2]["w"])
    check("the second place is fixed too", d["words"][8]["w"] == "MAKERS", d["words"][8]["w"])
    check("times did not move", [(x["s"], x["e"]) for x in d["words"]] == [(x["s"], x["e"]) for x in before["words"]])
    tt = (jd / "transcript.txt").read_bytes()
    check("transcript.txt is written again, LF only", b"\r" not in tt and "MAKERS," in tt.decode("utf-8"))
    check("transcript.txt keeps the numbering and the times",
          "  1) [0:00.0-0:01.6] בניתי את MAKERS, היום." in tt.decode("utf-8"), tt.decode("utf-8")[:300])

    rc, out = run(video, env, "וורד פרס", "WordPress")
    d = load(jd)
    L = {x["n"]: x for x in d["lines"]}
    wp = [x for x in d["words"] if x["w"] == "WordPress"]
    check("two words into one: exit 0", rc == 0, out)
    check("two words into one: one word from the start of the first to the end of the second",
          len(wp) == 1 and wp[0]["s"] == 3.0 and wp[0]["e"] == 3.8, wp)
    check("two words into one: line 2 text", L[2]["text"] == "באתר WordPress של MAKERS", L[2]["text"])
    check("two words into one: the line after it moved its word indexes",
          (L[3]["w0"], L[3]["w1"]) == (8, 11) and d["words"][L[3]["w0"]]["w"] == "שאלתי", (L[3]["w0"], L[3]["w1"]))
    check("line numbers, starts and ends unchanged",
          [(x["n"], x["start"], x["end"]) for x in d["lines"]] == [(x["n"], x["start"], x["end"]) for x in before["lines"]])
    check("every word carries its line", all(d["words"][i]["line"] == x["n"] for x in d["lines"]
                                             for i in range(x["w0"], x["w1"] + 1)))

    rc, out = run(video, env, "צ'אטג'יפיטי", "Chat GPT", "--line", "3")
    d = load(jd)
    i = next(k for k, x in enumerate(d["words"]) if x["w"] == "Chat")
    a, b = d["words"][i], d["words"][i + 1]
    check("one word into two, with --line: exit 0", rc == 0, out)
    check("one word into two: shares the same span, in order",
          a["s"] == 6.15 and b["e"] == 7.0 and a["s"] < a["e"] == b["s"] < b["e"], (a, b))
    check("one word into two: line 3 text", d["lines"][2]["text"] == "שאלתי את Chat GPT וזהו.", d["lines"][2]["text"])

    rc, out = run(video, env, "את", "אֶת", "--line", "1")
    d = load(jd)
    check("--line changes only that line", rc == 0 and d["words"][1]["w"] == "אֶת"
          and d["words"][L[3]["w0"] + 1]["w"] == "את", out)

    snap = (jd / "words.json").read_bytes()
    rc, out = run(video, env, "וורדפרס", "WordPress")
    check("not in the transcript: refused with PROBLEM, nothing written",
          rc == 2 and "PROBLEM" in out and (jd / "words.json").read_bytes() == snap, out)
    rc, out = run(video, env, "היום. באתר", "היום באתר")
    check("a phrase across two lines: refused", rc == 2 and "runs across lines 1 and 2" in out, out)
    rc, out = run(video, env, "MAKERS", "")
    check("an empty correction: refused (that is a cut)", rc == 2 and "is a cut" in out, out)
    rc, out = run(video, env, "MAKERS", "x", "--line", "9")
    check("a line that does not exist: refused", rc == 2 and "no line 9" in out, out)
    rc, out = run(video, env, "MAKERS")
    check("one argument only: refused with the usage", rc == 2 and "fix-word <video>" in out, out)
    check("after the refusals words.json is unchanged", (jd / "words.json").read_bytes() == snap)

print("FIX-WORD TESTS " + ("ALL PASS" if not fails else f"{fails} FAILED"))
sys.exit(1 if fails else 0)
