#!/usr/bin/env python3
"""Pull the exact commands an agent runs out of the install runbooks, so CI runs what an owner's computer runs.

Nothing here is retyped: every command comes out of video-editor/INSTALL-makers.md, skills/video-editor/SKILL.md
or skills/style-maker/SKILL.md as it is written there. A runbook that changed shape fails here, loudly, instead of
CI quietly testing an old copy.

Usage: python runbook-blocks.py <repo> <out-dir>
"""
import re
import sys
from pathlib import Path

repo, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
FENCE = re.compile(r"^```(\w*)\n(.*?)^```", re.M | re.S)


def section(text, start, end=None):
    i = text.find(start)
    if i < 0:
        sys.exit(f"RUNBOOK CHANGED: no section starting {start!r}")
    j = text.find(end, i + len(start)) if end else -1
    return text[i:j if j > 0 else len(text)]


def bash_blocks(text):
    return [body for lang, body in FENCE.findall(text) if lang == "bash"]


def inline(text, prefix):
    hits = [c for c in re.findall(r"`([^`\n]+)`", text) if c.startswith(prefix)]
    if not hits:
        sys.exit(f"RUNBOOK CHANGED: no inline command starting {prefix!r}")
    return hits[0] + "\n"


def put(name, body):
    with open(out / name, "w", encoding="utf-8", newline="\n") as f:     # LF on Windows too: bash reads these
        f.write(body if body.endswith("\n") else body + "\n")
    print(f"{name:<22} {body.strip().splitlines()[0][:100]}")


inst = (repo / "video-editor/INSTALL-makers.md").read_text(encoding="utf-8")
s3 = bash_blocks(section(inst, "### שלב 3.", "### שלב 4."))
s5 = bash_blocks(section(inst, "### שלב 5.", "### שלב 6."))
s6 = section(inst, "### שלב 6.", "### שלב 7.")
b6 = bash_blocks(s6)
if len(s3) != 1 or len(s5) != 3 or len(b6) < 3:
    sys.exit(f"RUNBOOK CHANGED: expected 1 block in step 3, 3 in step 5, 3 or more in step 6; got {len(s3)}, {len(s5)}, {len(b6)}")
put("step3-look.sh", s3[0])
put("step5-download.sh", s5[0])
put("step5-check.sh", s5[1])
put("step5-launcher.sh", s5[2])
ie = [b for b in b6 if b.startswith("#!/bin/bash")]
if len(ie) != 1:
    sys.exit("RUNBOOK CHANGED: step 6 must hold exactly one install-editor.sh block")
put("install-editor.sh", ie[0])
doc = [b for b in b6 if b.strip() == "bash ~/reel-studio/editor doctor"]
if len(doc) != 1:
    sys.exit("RUNBOOK CHANGED: step 6 must end with the doctor block")
put("step6-doctor.sh", doc[0])
put("step6-base.sh", inline(s6, "bash ~/reel-studio/install-editor.sh base"))
put("step6-libs.sh", inline(s6, "nohup bash ~/reel-studio/install-editor.sh libs"))
put("step6-libs-wait.sh", inline(s6, "bash ~/reel-studio/install-editor.sh wait"))
put("step6-model.sh", inline(s6, "nohup bash ~/reel-studio/editor model ivrit"))
put("step6-model-wait.sh", inline(s6, "bash ~/reel-studio/editor wait"))

skill = (repo / "skills/video-editor/SKILL.md").read_text(encoding="utf-8")
b1 = bash_blocks(section(skill, "### Step 1.", "### Step 2."))
if len(b1) != 1:
    sys.exit("RUNBOOK CHANGED: Step 1 of the skill must hold one block, the launcher and the check")
put("skill-step1.sh", b1[0])

sm = (repo / "skills/style-maker/SKILL.md").read_text(encoding="utf-8")
smi = [b for b in bash_blocks(sm) if b.startswith("#!/bin/bash") and 'part "base"' in b]
if len(smi) != 1:
    sys.exit("RUNBOOK CHANGED: the style builder skill must hold exactly one install.sh block")
put("style-install.sh", smi[0])
put("style-base.sh", inline(sm, "bash ~/reel-studio/install.sh base"))
put("style-doctor.sh", inline(sm, "bash ~/reel-studio/kit doctor"))
print("BLOCKS OK")
