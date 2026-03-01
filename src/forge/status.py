"""Plugin health dashboard — non-failing checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StatusCheck:
    name: str
    passed: bool
    detail: str


def _check_file(plugin_dir: Path, filename: str) -> StatusCheck:
    path = plugin_dir / filename
    return StatusCheck(
        name=filename,
        passed=path.exists(),
        detail=str(path) if path.exists() else "missing",
    )


def _check_in_registry(plugin_name: str, skill7_workspace: Path | None) -> StatusCheck:
    if skill7_workspace is None:
        return StatusCheck(name="skill7 registry", passed=False, detail="workspace not configured")
    registry_path = skill7_workspace / "registry.json"
    if not registry_path.exists():
        return StatusCheck(name="skill7 registry", passed=False, detail="registry.json not found")
    try:
        registry = json.loads(registry_path.read_text())
    except json.JSONDecodeError:
        return StatusCheck(name="skill7 registry", passed=False, detail="invalid JSON")
    for plugins in registry.values():
        for p in plugins:
            if p.get("name") == plugin_name:
                return StatusCheck(name="skill7 registry", passed=True, detail="found")
    return StatusCheck(name="skill7 registry", passed=False, detail="not registered")


def _check_in_marketplace(
    plugin_name: str, emporium_path: Path | None, label: str = "emporium"
) -> StatusCheck:
    if emporium_path is None:
        return StatusCheck(name=label, passed=False, detail="path not configured")
    mp_path = emporium_path / ".claude-plugin" / "marketplace.json"
    if not mp_path.exists():
        return StatusCheck(name=label, passed=False, detail="marketplace.json not found")
    try:
        raw = json.loads(mp_path.read_text())
    except json.JSONDecodeError:
        return StatusCheck(name=label, passed=False, detail="invalid JSON")
    # Handle both formats: dict with "plugins" key (emporium) or flat array (website)
    plugins = raw.get("plugins", raw) if isinstance(raw, dict) else raw
    if not isinstance(plugins, list):
        return StatusCheck(name=label, passed=False, detail="unexpected format")
    for entry in plugins:
        if entry.get("name") == plugin_name:
            return StatusCheck(name=label, passed=True, detail="found")
    return StatusCheck(name=label, passed=False, detail="not registered")


def check_plugin_status(
    plugin_dir: Path,
    *,
    skill7_workspace: Path | None = None,
    emporium_path: Path | None = None,
    website_path: Path | None = None,
) -> list[StatusCheck]:
    """Run all status checks for a plugin directory."""
    checks: list[StatusCheck] = []

    # Read manifest for type
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        checks.append(StatusCheck(name="plugin.json", passed=False, detail="missing"))
        return checks

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        checks.append(StatusCheck(name="plugin.json", passed=False, detail=f"invalid JSON: {e}"))
        return checks
    if not isinstance(manifest, dict):
        checks.append(StatusCheck(name="plugin.json", passed=False, detail="must be a JSON object"))
        return checks
    plugin_name = manifest.get("name", plugin_dir.name)
    plugin_type = manifest.get("type", "marketplace")

    # File checks
    checks.append(_check_file(plugin_dir, ".gitignore"))
    checks.append(_check_file(plugin_dir, "README.md"))
    checks.append(
        StatusCheck(
            name="plugin.json",
            passed=True,
            detail=f"v{manifest.get('version', '?')}",
        )
    )
    checks.append(_check_file(plugin_dir, "CHANGELOG.md"))

    # Registry checks (always for marketplace and project)
    if plugin_type in ("marketplace", "project"):
        checks.append(_check_in_registry(plugin_name, skill7_workspace))

    # Marketplace checks (only for marketplace)
    if plugin_type == "marketplace":
        checks.append(_check_in_marketplace(plugin_name, emporium_path, "emporium marketplace"))
        # Check website registration too
        if website_path:
            web_mp = website_path / "src" / "data" / "marketplace.json"
            if web_mp.exists():
                try:
                    raw = json.loads(web_mp.read_text())
                    plugins = raw if isinstance(raw, list) else raw.get("plugins", [])
                    found = any(e.get("name") == plugin_name for e in plugins)
                    checks.append(
                        StatusCheck(
                            name="website marketplace",
                            passed=found,
                            detail="found" if found else "not registered",
                        )
                    )
                except json.JSONDecodeError:
                    checks.append(
                        StatusCheck(name="website marketplace", passed=False, detail="invalid JSON")
                    )
            else:
                checks.append(
                    StatusCheck(name="website marketplace", passed=False, detail="file not found")
                )

    return checks
