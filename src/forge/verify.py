"""Strict plugin verification checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REQUIRED_MANIFEST_FIELDS = ("name", "version", "description")


@dataclass
class VerifyResult:
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def verify_plugin(plugin_dir: Path) -> VerifyResult:
    """Run all verification checks on a plugin directory. Collects all errors."""
    result = VerifyResult()
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"

    # File existence checks
    if not (plugin_dir / ".gitignore").exists():
        result.errors.append(".gitignore missing")

    if not (plugin_dir / "README.md").exists():
        result.errors.append("README.md missing")

    if not (plugin_dir / "LICENSE").exists():
        result.errors.append("LICENSE missing")

    if not (plugin_dir / "CHANGELOG.md").exists():
        result.errors.append("CHANGELOG.md missing")

    # Docs checks
    docs_dir = plugin_dir / "docs"
    if not (docs_dir / "how-it-works.md").exists():
        result.errors.append("docs/how-it-works.md missing")
    if not (docs_dir / "reference.md").exists():
        result.errors.append("docs/reference.md missing")

    # If src/ exists, tests/ must exist
    if (plugin_dir / "src").is_dir() and not (plugin_dir / "tests").is_dir():
        result.errors.append("tests/ required when src/ exists")

    if not manifest_path.exists():
        result.errors.append(".claude-plugin/plugin.json missing")
        return result  # Can't continue without manifest

    # Parse manifest
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        result.errors.append(f"plugin.json invalid JSON: {e}")
        return result

    if not isinstance(manifest, dict):
        result.errors.append("plugin.json must be a JSON object, not array or scalar")
        return result

    # Required fields
    for f in REQUIRED_MANIFEST_FIELDS:
        if f not in manifest:
            result.errors.append(f"plugin.json missing required field: {f}")

    # Semver
    version = manifest.get("version", "")
    if version and not SEMVER_RE.match(version):
        result.errors.append(f"Invalid semver: '{version}' (expected X.Y.Z)")

    # Name matches dirname
    if "name" in manifest and manifest["name"] != plugin_dir.name:
        result.errors.append(
            f"plugin.json name '{manifest['name']}' does not match directory '{plugin_dir.name}'"
        )

    plugin_type = manifest.get("type", "marketplace")

    # README checks
    readme_path = plugin_dir / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text()
        if "TODO" in readme:
            result.errors.append("README.md contains TODO placeholders")
        if plugin_type == "marketplace" and "<!-- INSTALL:START" not in readme:
            result.errors.append("README.md missing INSTALL markers (required for marketplace)")

        # Extended README validation
        from forge.readme_verify import verify_readme_structure, verify_readme_style

        result.errors.extend(verify_readme_structure(readme, plugin_type))
        result.errors.extend(verify_readme_style(readme))

    # CHANGELOG version match (supports both "## 1.0.0" and "## [1.0.0]" formats)
    changelog_path = plugin_dir / "CHANGELOG.md"
    if changelog_path.exists() and version:
        changelog = changelog_path.read_text()
        if f"## {version}" not in changelog and f"## [{version}]" not in changelog:
            result.errors.append(
                f"CHANGELOG.md top version does not match plugin.json version {version}"
            )

    # Kebab-case top-level directories
    SKIP_DIRS = {".claude-plugin", ".git", ".github", "__pycache__", ".venv", "node_modules"}
    for child in plugin_dir.iterdir():
        if child.is_dir() and child.name not in SKIP_DIRS and not child.name.startswith("."):
            if not KEBAB_RE.match(child.name):
                result.errors.append(
                    f"Directory '{child.name}' is not kebab-case"
                )

    # SKILL.md uppercase check
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_files = [f.name for f in skill_dir.iterdir() if f.is_file()]
                if "SKILL.md" not in skill_files:
                    lower = [f for f in skill_files if f.lower() == "skill.md"]
                    if lower:
                        result.errors.append(
                            f"skills/{skill_dir.name}/{lower[0]} must be SKILL.md (uppercase)"
                        )

    return result
