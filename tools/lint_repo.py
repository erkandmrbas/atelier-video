#!/usr/bin/env python3
"""Repository checks run in CI: JSON validity, skill front matter, size limits, banned words."""
import base64
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "atelier-video"
# Names that must never appear in this repo (sources, products, tools). Stored encoded so this file passes its own scan.
BANNED = re.compile(base64.b64decode("YXZlbm94fHNpcmlvfHlvdXR1YmV8dG9wdmlld3xsaW1vbnxsZW1vbnxoeXBlcmZyYW1lc3xzZWVkYW5jZXx3aGlzcGVyfGVsZXZlbmxhYnN8cmVtb3Rpb24=").decode(), re.I)
MAX_SKILL_LINES = 250
problems = []

for path in [ROOT / ".claude-plugin/marketplace.json",
             PLUGIN / ".claude-plugin/plugin.json", PLUGIN / "hooks/hooks.json"]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"{path.relative_to(ROOT)}: invalid JSON ({exc})")

names = {json.loads((PLUGIN / ".claude-plugin/plugin.json").read_text())["name"],
         json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())["plugins"][0]["name"]}
if names != {"atelier-video"}:
    problems.append(f"manifest names disagree: {names}")

skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
if not skills:
    problems.append("no skills found")
for skill in skills:
    text = skill.read_text(encoding="utf-8")
    rel = skill.relative_to(ROOT)
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        problems.append(f"{rel}: missing front matter")
        continue
    front = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    name = front.get("name", "").strip()
    desc = front.get("description", "").strip()
    if name != skill.parent.name:
        problems.append(f"{rel}: name '{name}' does not match folder '{skill.parent.name}'")
    if not desc or len(desc) > 1024:
        problems.append(f"{rel}: description missing or longer than 1024 characters")
    lines = text.count("\n") + 1
    if lines > MAX_SKILL_LINES:
        problems.append(f"{rel}: {lines} lines (limit {MAX_SKILL_LINES})")

for path in ROOT.rglob("*"):
    if path.is_file() and ".git" not in path.parts and path.suffix in {".md", ".json", ".py", ".yml", ".sh", ".txt", ".toml"}:
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if BANNED.search(line):
                problems.append(f"{path.relative_to(ROOT)}:{number}: banned word")

for problem in problems:
    print(f"FAIL {problem}")
print(f"{len(skills)} skills checked, {len(problems)} problems")
sys.exit(1 if problems else 0)
