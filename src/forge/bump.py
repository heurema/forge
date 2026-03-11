"""Coordinated version bump: validate-all-then-write-all."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from forge.config import ForgeConfig
from forge.registry_io import atomic_write_json
from forge.sync import sync_plugin


@dataclass
class BumpResult:
    old_version: str
    new_version: str
    files_written: dict[str, str] = field(default_factory=dict)


def compute_next_version(current: str, level: str) -> str:
    """Compute next semver version. level: patch/minor/major."""
    parts = current.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {current}")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    if level == "patch":
        patch += 1
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid bump level: {level}")
    return f"{major}.{minor}.{patch}"


def _update_changelog(changelog_path: Path, new_version: str) -> None:
    """Prepend a new version entry to CHANGELOG.md."""
    content = changelog_path.read_text() if changelog_path.exists() else "# CHANGELOG\n"
    today = date.today().isoformat()
    new_entry = f"\n## [{new_version}] - {today}\n\n### Changed\n- Version bump\n"

    # Insert after "# CHANGELOG" header
    header_match = re.search(r"^# CHANGELOG\s*$", content, re.MULTILINE)
    if header_match:
        pos = header_match.end()
        content = content[:pos] + new_entry + content[pos:]
    else:
        content = f"# CHANGELOG{new_entry}\n{content}"

    changelog_path.write_text(content)


def bump_version(
    plugin_dir: Path,
    config: ForgeConfig,
    level: str,
    *,
    dry_run: bool = True,
    adapters: dict | None = None,
) -> BumpResult:
    """Bump version in plugin.json, CHANGELOG, and all registries.

    validate-all-then-write-all pattern:
    Phase 1: validate all paths exist
    Phase 2: compute new version and entries
    Phase 3: write (if not dry_run)
    """
    # Phase 1: validate
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not pj_path.exists():
        raise FileNotFoundError(f"plugin.json not found: {pj_path}")

    # Validate config paths that sync will need
    config.require_path("skill7_workspace")
    config.require_path("emporium_path")
    config.require_path("website_path")

    # Phase 2: compute
    plugin_json = json.loads(pj_path.read_text())
    old_version = plugin_json["version"]
    new_version = compute_next_version(old_version, level)

    result = BumpResult(old_version=old_version, new_version=new_version)

    if dry_run:
        result.files_written = {
            "plugin.json": f"{old_version} → {new_version}",
            "CHANGELOG.md": f"new entry [{new_version}]",
            "registries": "sync pending",
        }
        return result

    # Phase 3: write
    # 1. Update plugin.json
    plugin_json["version"] = new_version
    atomic_write_json(pj_path, plugin_json)
    result.files_written["plugin.json"] = f"{old_version} → {new_version}"

    # 2. Update CHANGELOG
    changelog_path = plugin_dir / "CHANGELOG.md"
    _update_changelog(changelog_path, new_version)
    result.files_written["CHANGELOG.md"] = f"new entry [{new_version}]"

    # 3. Sync all registries
    sync_result = sync_plugin(plugin_dir, config, dry_run=False, adapters=adapters)
    result.files_written.update(sync_result.statuses)

    return result
