#!/usr/bin/env python3
"""Build dist/<skill>.zip for upload through Claude's Customize > Skills.

Usage:  python build_zip.py atdd

The ZIP holds the skill folder at its top level (atdd/SKILL.md, atdd/references/...),
leaves out evals/, __pycache__/ and .DS_Store, and checks the frontmatter rules the
upload enforces: name equals the folder name, kebab-case, description 1-200 chars,
only the six fields the Agent Skills spec allows.
"""
import re
import sys
import zipfile
from pathlib import Path

EXCLUDE_DIRS = {"evals", "__pycache__", "node_modules"}
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def check_frontmatter(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with YAML frontmatter"
    fm = match.group(1)
    name = re.search(r'^name:\s*"?([^"\n]+?)"?\s*$', fm, re.M)
    desc = re.search(r'^description:\s*"?(.+?)"?\s*$', fm, re.M)
    assert name and name.group(1) == skill_dir.name, "frontmatter name must equal the folder name"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name.group(1)), "name: lowercase, digits, single hyphens"
    length = len(desc.group(1)) if desc else 0
    assert 0 < length <= 200, f"description must be 1-200 characters, got {length}"
    assert "<" not in desc.group(1) and ">" not in desc.group(1), "description must not contain angle brackets"
    keys = {line.split(":")[0] for line in fm.splitlines() if line and not line[0].isspace()}
    extra = keys - ALLOWED_KEYS
    assert not extra, f"frontmatter keys the upload rejects: {sorted(extra)}"
    print(f"frontmatter ok: name={name.group(1)} description={length} chars")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(__file__).resolve().parent
    skill = root / sys.argv[1]
    check_frontmatter(skill)
    out = root / "dist" / f"{skill.name}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill.rglob("*")):
            relp = path.relative_to(root)
            if not path.is_file() or path.name == ".DS_Store" or set(relp.parts[1:-1]) & EXCLUDE_DIRS:
                continue
            archive.write(path, relp.as_posix())
            print("  added", relp.as_posix())
    print(f"built {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
