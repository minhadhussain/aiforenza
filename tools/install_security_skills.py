"""Install pinned, documentation-only security skills into this project's OpenCode.

No upstream scripts, plugins, hooks, dependencies, or commands are executed.
Use --check for offline integrity validation of an existing installation.
"""

import argparse
import fnmatch
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".opencode/skills"
LOCK = ROOT / ".opencode/security-skills.lock.json"
SOURCES = [
    {
        "name": "security-best-practices",
        "repository": "openai/skills",
        "commit": "49f948faa9258a0c61caceaf225e179651397431",
        "path": "skills/.curated/security-best-practices",
        "license": "Apache-2.0",
        "include": ["SKILL.md", "LICENSE.txt", "references/python-fastapi-web-server-security.md", "references/javascript-general-web-frontend-security.md", "references/javascript-typescript-nextjs-web-server-security.md", "references/javascript-typescript-react-web-frontend-security.md"],
    },
    {
        "name": "security-threat-model",
        "repository": "openai/skills",
        "commit": "49f948faa9258a0c61caceaf225e179651397431",
        "path": "skills/.curated/security-threat-model",
        "license": "Apache-2.0",
        "include": ["SKILL.md", "LICENSE.txt", "references/*.md"],
    },
    {
        "name": "supabase-postgres-best-practices",
        "repository": "supabase/agent-skills",
        "commit": "8331f910845103c08d51f6ca1d86ebb7d1f745e3",
        "path": "skills/supabase-postgres-best-practices",
        "license": "MIT",
        "license_path": "LICENSE",
        "include": ["SKILL.md", "references/*.md"],
    },
    {
        "name": "property-based-testing",
        "repository": "trailofbits/skills",
        "commit": "32e34f8173796e3566a51aee877dc96bc5191f64",
        "path": "plugins/property-based-testing/skills/property-based-testing",
        "license": "CC-BY-SA-4.0",
        "license_path": "LICENSE",
        "include": ["SKILL.md", "references/*.md"],
    },
]


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {".", ".."} or ":" in part or "\\" in part for part in path.parts):
        raise ValueError("Unsafe upstream path")
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("Only documentation files are permitted")
    return path


def skill_name(data):
    text = data.decode("utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("Missing skill frontmatter")
    frontmatter = text.split("---", 2)[1]
    match = re.search(r'^name:\s*["\']?([a-z0-9]+(?:-[a-z0-9]+)*)["\']?\s*$', frontmatter, re.MULTILINE)
    if not match or not re.search(r"^description:\s*\S", frontmatter, re.MULTILINE):
        raise ValueError("Invalid skill name/description")
    return match.group(1)


def digest(data):
    # Git may normalize text line endings on Windows; semantic content must match.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def install():
    if not SKILLS.resolve().is_relative_to(ROOT):
        raise ValueError("Skill installation directory must remain inside this project")
    if LOCK.exists() or any((SKILLS / source["name"]).exists() for source in SOURCES):
        raise ValueError("Skills already exist; use --check. Existing/user-edited skills are never overwritten.")
    trees = {}
    prepared = []
    with httpx.Client(timeout=45, follow_redirects=False, headers={"User-Agent": "AI-Forenza-Skill-Installer"}) as client:
        for source in SOURCES:
            identity = (source["repository"], source["commit"])
            if identity not in trees:
                response = client.get(f"https://api.github.com/repos/{identity[0]}/git/trees/{identity[1]}", params={"recursive": "1"})
                response.raise_for_status()
                tree = response.json()
                if tree.get("truncated"):
                    raise ValueError("Upstream tree was truncated")
                trees[identity] = {entry["path"]: entry for entry in tree["tree"]}
            tree = trees[identity]
            prefix = source["path"] + "/"
            chosen = {}
            for path, entry in tree.items():
                if not path.startswith(prefix):
                    continue
                relative = path[len(prefix):]
                if entry["type"] == "blob" and any(fnmatch.fnmatchcase(relative, pattern) for pattern in source["include"]):
                    chosen[relative] = (path, entry)
            if source.get("license_path"):
                license_path = source["license_path"]
                chosen["LICENSE.txt"] = (license_path, tree[license_path])
            if "SKILL.md" not in chosen or "LICENSE.txt" not in chosen or len(chosen) > 200:
                raise ValueError("Incomplete or oversized skill bundle")
            for pattern in source["include"]:
                if not any(fnmatch.fnmatchcase(relative, pattern) for relative in chosen):
                    raise ValueError("Required skill reference is missing")
            files = []
            for relative, (upstream, entry) in sorted(chosen.items()):
                safe_relative(relative)
                if entry["mode"] != "100644" or entry.get("size", 0) > 512000:
                    raise ValueError("Unexpected upstream file mode or size")
                url = f"https://raw.githubusercontent.com/{identity[0]}/{identity[1]}/{quote(upstream, safe='/')}"
                response = client.get(url)
                response.raise_for_status()
                data = response.content
                blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                if blob != entry["sha"]:
                    raise ValueError("Upstream Git blob integrity mismatch")
                data.decode("utf-8")
                files.append(({"path": relative, "upstream_path": upstream, "git_blob_sha": blob, "sha256_lf": digest(data)}, data))
            if skill_name(next(data for record, data in files if record["path"] == "SKILL.md")) != source["name"]:
                raise ValueError("Upstream skill name does not match its installation directory")
            prepared.append((source, files))
    # Download/verify everything first, then create only new skill directories.
    manifest = {"version": 1, "hash_normalization": "CRLF to LF", "skills": []}
    for source, files in prepared:
        target = SKILLS / source["name"]
        target.mkdir(parents=True, exist_ok=False)
        for record, data in files:
            file = target.joinpath(*safe_relative(record["path"]).parts)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        manifest["skills"].append({**source, "files": [record for record, _ in files]})
        print(json.dumps({"installed": source["name"], "source": source["repository"], "commit": source["commit"], "documentation_files": len(files)}))
    LOCK.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def check():
    if not SKILLS.resolve().is_relative_to(ROOT):
        raise ValueError("Skill installation directory must remain inside this project")
    manifest = json.loads(LOCK.read_text(encoding="utf-8"))
    total = 0
    for source in manifest["skills"]:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source["name"]):
            raise ValueError("Invalid installed skill name")
        target = SKILLS / source["name"]
        if target.is_symlink() or not target.resolve().is_relative_to(SKILLS.resolve()):
            raise ValueError("Installed skill directory escapes the project")
        for record in source["files"]:
            file = target.joinpath(*safe_relative(record["path"]).parts)
            if not file.resolve().is_relative_to(target.resolve()) or file.is_symlink():
                raise ValueError("Installed skill reference escapes its directory")
            if digest(file.read_bytes()) != record["sha256_lf"]:
                raise ValueError("Installed skill differs from pinned source: " + source["name"] + "/" + record["path"])
            total += 1
        if skill_name((target / "SKILL.md").read_bytes()) != source["name"]:
            raise ValueError("Installed skill has invalid frontmatter")
    print(json.dumps({"verified_skills": len(manifest["skills"]), "verified_files": total, "pinned_source_integrity": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        check() if args.check else install()
    except Exception as exc:
        print(str(exc) if type(exc) is ValueError else "Skill installation failed: " + type(exc).__name__)
        raise SystemExit(1)
