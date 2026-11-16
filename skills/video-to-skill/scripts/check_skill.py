#!/usr/bin/env python3
"""Checks a skill folder before it is installed: the mistakes that make a skill silently never run.

Usage:  python3 check_skill.py FOLDER [--app]        (or: bash run.sh check_skill.py FOLDER)
  --app   the skill will be uploaded to the Claude app, where the description is limited to 200 characters

Prints each problem on its own line, then  CHECK OK  or  CHECK FAILED <n>. Exit code 0 only on OK.
Only the standard library: runs anywhere Python runs.
"""
import re, sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    d = Path(a[0]).expanduser().resolve()
    app = "--app" in a
    bad, warn = [], []
    f = d / "SKILL.md"
    if not f.is_file():
        print(f"PROBLEM no SKILL.md in {d}")
        print("CHECK FAILED 1")
        sys.exit(1)
    text = f.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m or not text.startswith("---"):
        bad.append("SKILL.md must start with a front block between two --- lines, holding name and description")
        fm, body = "", text
    else:
        fm, body = m.group(1), text[m.end():]
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    name = name.group(1).strip().strip("\"'") if name else ""
    desc = desc.group(1).strip() if desc else ""
    if not name:
        bad.append("no name: in the front block")
    elif name != d.name:
        bad.append(f"name is '{name}' but the folder is '{d.name}'; they must be the same")
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        bad.append(f"name '{name}' must be small English letters, digits and hyphens, at most 64")
    if not desc:
        bad.append("no description: on one line in the front block. The description is what makes the skill run")
    else:
        plain = desc.strip("\"'")
        if ": " in plain:
            bad.append("the description has a colon followed by a space; that silently breaks the front block. "
                       "Use a comma or a period instead")
        if "<" in plain or ">" in plain:
            bad.append("the description has < or >, which the Claude app refuses")
        limit = 200 if app else 1024
        if len(plain) > limit:
            bad.append(f"the description is {len(plain)} characters; at most {limit}"
                       + (" for the Claude app" if app else ""))
        if not re.search(r"[\"“”״]", plain):
            warn.append("the description quotes no phrase the owner would say; add two or three, in their language")
    if re.search(r"^\S+:\s", fm, re.M) and re.search(r"^(?!name:|description:|license:|allowed-tools:|metadata:|\s)\S+:", fm, re.M):
        warn.append("the front block has fields other than name and description; the Claude app may refuse them")
    lines = body.count("\n") + 1
    if lines > 500:
        bad.append(f"the body is {lines} lines; keep it under 500 and move detail into files next to it")
    steps = re.findall(r"^#{1,4}\s*(?:שלב|step)\s*\d+|^#{1,4}\s*\d+[.)]|^\s*\d+[.)]\s", body, re.M | re.I)
    if len(steps) < 2:
        bad.append("no numbered steps; write the work as numbered steps, so nothing in an opening paragraph is skipped")
    for ref in sorted(set(re.findall(r"(?<![\w/.])((?:scripts|assets|references|templates|examples)/[\w./-]+\.\w+)", text))):
        if not (d / ref).is_file():
            bad.append(f"the skill mentions {ref}, and there is no such file in the folder")
    if not re.search(r"^#{1,3}\s*(מקור|מקורות|source|sources)\b", body, re.M | re.I):
        bad.append("no 'מקור' (source) section saying what this skill was learned from and when")
    for w in warn:
        print("note  " + w)
    for b in bad:
        print("PROBLEM " + b)
    if bad:
        print(f"CHECK FAILED {len(bad)}")
        sys.exit(1)
    print(f"CHECK OK  {name} · description {len(desc.strip(chr(34) + chr(39)))} characters · {lines} lines · {len(steps)} steps")


if __name__ == "__main__":
    main()
