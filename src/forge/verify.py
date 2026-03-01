"""Strict plugin verification checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
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

    # CHANGELOG version match
    changelog_path = plugin_dir / "CHANGELOG.md"
    if changelog_path.exists() and version:
        changelog = changelog_path.read_text()
        if f"## {version}" not in changelog:
            result.errors.append(
                f"CHANGELOG.md top version does not match plugin.json version {version}"
            )

    return result
