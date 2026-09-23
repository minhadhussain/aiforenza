"""Validate pinned skill contents and actual OpenCode discovery, without inference."""

import json
from pathlib import Path
import re
import subprocess

from install_security_skills import check, LOCK, ROOT, SKILLS, skill_name


def main():
    check()
    sources = json.loads(LOCK.read_text(encoding="utf-8"))["skills"]
    expected = {source["name"] for source in sources} | {"aiforenza-security-review"}
    for name in expected:
        path = SKILLS / name / "SKILL.md"
        if skill_name(path.read_bytes()) != name:
            raise ValueError("Skill frontmatter/name mismatch")
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in link or link.startswith("#"):
                continue
            target = path.parent / link.split("#", 1)[0]
            if not target.exists():
                raise ValueError("Missing local skill reference: " + name + "/" + link)
    exe = Path.home() / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    result = subprocess.run([str(exe), "debug", "skill", "--pure"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if result.returncode:
        raise ValueError("OpenCode skill discovery failed")
    payload = json.loads(result.stdout)
    entries = payload if isinstance(payload, list) else payload.get("skills", [])
    found = {item["name"]: item for item in entries if item.get("name") in expected}
    if set(found) != expected:
        raise ValueError("OpenCode did not discover all project security skills: " + ", ".join(sorted(expected - set(found))))
    for name, item in found.items():
        location = item.get("location") or item.get("path")
        if not location or not Path(location).resolve().is_relative_to(SKILLS.resolve()):
            raise ValueError("A global skill shadowed the project skill: " + name)
    # Capture resolved config privately: it may contain the user's provider keys.
    result = subprocess.run([str(exe), "debug", "config", "--pure"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if result.returncode:
        raise ValueError("OpenCode configuration validation failed")
    config = json.loads(result.stdout)
    command = config.get("command", {}).get("security-review", {})
    if command.get("agent") != "build" or "aiforenza-security-review" not in command.get("template", ""):
        raise ValueError("OpenCode did not load the security-review command")
    print(json.dumps({"opencode_discovered_skills": sorted(found), "all_skills_project_scoped": True, "local_references_valid": True, "security_review_command_loaded": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is ValueError else "Skill verification failed: " + type(exc).__name__)
        raise SystemExit(1)
