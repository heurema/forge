"""PR-based plugin registration across registries."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.sync import SyncResult, sync_plugin  # noqa: F401


@dataclass
class RegistryTarget:
    name: str
    description: str


def determine_targets(plugin_type: str) -> list[RegistryTarget]:
    """Determine which registries to update based on plugin type."""
    targets: list[RegistryTarget] = []
    if plugin_type in ("marketplace", "project"):
        targets.append(
            RegistryTarget(name="skill7_registry", description="skill7 workspace registry.json")
        )
    if plugin_type == "marketplace":
        targets.extend(
            [
                RegistryTarget(name="emporium", description="emporium marketplace.json"),
                RegistryTarget(
                    name="website_marketplace", description="skill7.dev marketplace.json"
                ),
                RegistryTarget(
                    name="website_plugin_meta", description="skill7.dev plugin-meta.json"
                ),
            ]
        )
    return targets


def add_to_marketplace_json(mp_file: Path, entry: dict[str, Any]) -> bool:
    """Add entry to marketplace.json. Returns False if duplicate.

    Handles two formats:
    - Emporium: {"name":..., "plugins": [...]}  (dict with plugins key)
    - Website/flat: [...]  (plain array)
    """
    raw = json.loads(mp_file.read_text())
    # Extract plugin list from either format
    if isinstance(raw, dict) and "plugins" in raw:
        plugins = raw["plugins"]
    elif isinstance(raw, list):
        plugins = raw
    else:
        raise ValueError(f"Unexpected marketplace.json format in {mp_file}")
    if any(e.get("name") == entry["name"] for e in plugins):
        return False
    plugins.append(entry)
    plugins.sort(key=lambda e: e.get("name", ""))
    # Write back in original format
    if isinstance(raw, dict):
        raw["plugins"] = plugins
        mp_file.write_text(json.dumps(raw, indent=2) + "\n")
    else:
        mp_file.write_text(json.dumps(plugins, indent=2) + "\n")
    return True


def add_to_registry(
    reg_file: Path,
    name: str,
    category: str,
    version: str,
    description: str = "",
    owner: str = "heurema",
) -> bool:
    """Add entry to skill7 registry.json. Returns False if duplicate.

    Matches actual registry.json schema: name, description, owner, path, status, tags, version.
    """
    data: dict[str, list[dict[str, Any]]] = json.loads(reg_file.read_text())
    if category not in data:
        data[category] = []
    if any(p.get("name") == name for p in data[category]):
        return False
    data[category].append(
        {
            "name": name,
            "description": description,
            "owner": owner,
            "path": f"{category}/{name}",
            "status": "active",
            "tags": [category],
            "version": version,
        }
    )
    data[category].sort(key=lambda e: e.get("name", ""))
    reg_file.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return True


def build_marketplace_entry(
    name: str,
    description: str,
    category: str,
    github_org: str,
) -> dict[str, Any]:
    """Build a marketplace.json entry for emporium."""
    # Map forge categories to emporium categories (match actual marketplace.json)
    mp_category = {
        "devtools": "development",
        "trading": "trading",
        "creative": "creative",
    }.get(category, "development")
    return {
        "name": name,
        "description": description,
        "category": mp_category,
        "source": {
            "source": "url",
            "url": f"https://github.com/{github_org}/{name}.git",
        },
        "homepage": f"https://github.com/{github_org}/{name}",
    }


# ---------------------------------------------------------------------------
# New registration flow: preflight → verify → sync → commit → PR
# ---------------------------------------------------------------------------


@dataclass
class RegisterResult:
    success: bool
    pr_urls: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def preflight_check(plugin_dir: Path, config: "ForgeConfig") -> list[str]:
    """Run preflight checks before registration. Returns list of errors (empty = OK)."""
    from forge.config import ForgeConfig  # noqa: F401 (imported for type only)

    errors: list[str] = []
    for repo_path, repo_name in [
        (config.skill7_workspace, "skill7_workspace"),
        (config.emporium_path, "emporium"),
        (config.website_path, "website"),
    ]:
        if not repo_path.exists():
            errors.append(f"{repo_name} path does not exist: {repo_path}")
            continue
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                errors.append(f"{repo_name} has uncommitted changes")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            errors.append(f"git not available for {repo_name}")
    # Check gh auth
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            errors.append("gh auth not configured")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        errors.append("gh CLI not available")
    return errors


def check_existing_prs(config: "ForgeConfig", branch_name: str) -> list[str]:
    """Check for existing PRs with the given branch name. Returns list of PR URLs."""
    urls: list[str] = []
    for repo_path in [config.emporium_path, config.website_path]:
        if not repo_path.exists():
            continue
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--head", branch_name, "--json", "url", "-q", ".[].url"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(repo_path),
            )
            if result.stdout.strip():
                urls.extend(result.stdout.strip().splitlines())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return urls


def register_plugin(
    plugin_dir: Path,
    config: "ForgeConfig",
    *,
    dry_run: bool = True,
    resume: bool = False,
    adapters: dict | None = None,
) -> RegisterResult:
    """Register plugin: preflight → verify → sync → commit → PR.

    Args:
        plugin_dir: Path to plugin directory
        config: ForgeConfig instance
        dry_run: If True, only report what would happen
        resume: If True, check for existing PRs first
        adapters: Optional DI for testing (passed to sync_plugin)
    """
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json = json.loads(pj_path.read_text())
    name = plugin_json["name"]
    version = plugin_json["version"]
    branch_name = f"forge/{name}-v{version}"

    result = RegisterResult(success=False)

    # Resume: check for existing PRs
    if resume:
        existing = check_existing_prs(config, branch_name)
        if existing:
            result.success = True
            result.pr_urls = existing
            return result

    # Preflight (skipped in dry-run)
    if not dry_run:
        errors = preflight_check(plugin_dir, config)
        if errors:
            result.errors = errors
            return result

    # Sync (does the actual registry updates)
    sync_plugin(plugin_dir, config, dry_run=dry_run, adapters=adapters)

    result.success = True
    return result
