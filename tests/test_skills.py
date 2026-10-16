"""Validate every skills/<name>/SKILL.md: frontmatter, name == directory, no secrets."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRET = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w+|hooks/\d+/[\w-]+)")


def check(skill_md: Path) -> list[str]:
    errors = []
    text = skill_md.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return [f"{skill_md}: missing frontmatter"]
    fields = dict(
        line.split(":", 1) for line in m.group(1).splitlines() if ":" in line
    )
    name = fields.get("name", "").strip()
    if name != skill_md.parent.name:
        errors.append(f"{skill_md}: name {name!r} != directory {skill_md.parent.name!r}")
    if not fields.get("description", "").strip():
        errors.append(f"{skill_md}: empty description")
    if SECRET.search(text):
        errors.append(f"{skill_md}: looks like it contains a secret")
    return errors


def test_skills():
    files = sorted((ROOT / "skills").glob("*/SKILL.md"))
    assert files, "no skills found"
    errors = [e for f in files for e in check(f)]
    assert not errors, "\n".join(errors)


if __name__ == "__main__":
    try:
        test_skills()
    except AssertionError as e:
        print(e)
        sys.exit(1)
    print("ok")
