"""PR-based plugin registration across registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
