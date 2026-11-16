#!/usr/bin/env python3
"""Lists the skills the owner already has, so a new lesson upgrades one of them instead of becoming a copy.

Usage:  python3 my_skills.py            (or: bash run.sh my_skills.py)
        python3 my_skills.py --show NAME   prints that skill's SKILL.md, to read before upgrading it

Looks only in the places skills are loaded from, never across the whole disk:
  this folder's .claude/skills, ~/.claude/skills, ~/.agents/skills, ~/.codex/skills,
  and in the Claude app /mnt/skills/user.
Prints one block per skill (name, where, what its description says), then  SKILLS <n>.
Only the standard library: runs anywhere Python runs.
"""
import os, re, sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SELF = "video-to-skill"


def places():
    home = Path.home()
    seen, out = set(), []
    for p in (Path.cwd() / ".claude" / "skills", home / ".claude" / "skills", home / ".agents" / "skills",
              home / ".codex" / "skills", Path("/mnt/skills/user")):
        try:
            r = p.resolve()
        except OSError:
            continue
        if r in seen or not p.is_dir():
            continue
        seen.add(r)
        out.append(p)
    return out


def front(text):
    m = re.match(r"\s*---\s*\n(.*?)\n---", text, re.S)
    fm = m.group(1) if m else ""

    def field(k):
        f = re.search(rf"^{k}:\s*(.*(?:\n[ \t]+.*)*)", fm, re.M)
        if not f:
            return ""
        v = re.sub(r"\s*\n\s*", " ", f.group(1)).strip()
        return v.strip("\"'>| ")
    return field("name"), field("description")


def skills():
    for p in places():
        for d in sorted(p.iterdir()):
            f = d / "SKILL.md"
            if not d.is_dir() or not f.is_file() or d.name.startswith("."):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            name, desc = front(text)
            yield (name or d.name), d, desc, text.count("\n") + 1


def main():
    a = sys.argv[1:]
    if a and a[0] in ("-h", "--help"):
        print(__doc__)
        return
    if a and a[0] == "--show":
        want = a[1] if len(a) > 1 else ""
        for name, d, _desc, _n in skills():
            if name == want or d.name == want:
                print(f"# {d / 'SKILL.md'}\n")
                print((d / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
                return
        print(f"PROBLEM no skill named {want}")
        sys.exit(1)
    n = 0
    for name, d, desc, lines in skills():
        if name == SELF:
            continue
        n += 1
        print(f"{name}\n  where: {d}\n  lines: {lines}\n  does: {desc[:400] or '(no description)'}\n")
    where = ", ".join(str(p) for p in places()) or "none of the usual places exist yet"
    print(f"looked in: {where}")
    print(f"SKILLS {n}")


if __name__ == "__main__":
    main()
