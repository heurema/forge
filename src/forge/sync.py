"""Sync plugin.json to all 4 registries."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from forge.config import ForgeConfig, derive_category
from forge.registry_io import (
    EmporiumMarketplace,
    Skill7Registry,
    WebsiteMarketplace,
    WebsitePluginMeta,
)


CATEGORY_MAP = {
    "devtools": "development",
    "trading": "trading",
    "creative": "creative",
    "publishing": "publishing",
    "research": "research",
}


@dataclass
class SyncResult:
    """Result of sync_plugin with per-target status."""

    statuses: dict[str, str] = field(default_factory=dict)


def build_skill7_entry(plugin_json: dict, category: str, plugin_dir: Path) -> dict:
    """Build a skill7 registry.json entry from plugin.json."""
    skills_dir = plugin_dir / "skills"
    skill_dirs = (
        sorted(d.name for d in skills_dir.iterdir() if d.is_dir())
        if skills_dir.exists()
        else []
    )
    first_skill = skill_dirs[0] if skill_dirs else plugin_json["name"]

    return {
        "name": plugin_json["name"],
        "description": plugin_json["description"],
        "version": plugin_json["version"],
        "path": f"{category}/{plugin_json['name']}",
        "allowed_tools": [],
        "skill_id": f"{plugin_json['name']}:{first_skill}",
        "capabilities": list(plugin_json.get("keywords", [])),
        "metadata": {
            "author": plugin_json.get("author", ""),
            "compatibility": plugin_json.get("compatibility", "claude-code"),
            "homepage": plugin_json.get("homepage", ""),
            "keywords": list(plugin_json.get("keywords", [])),
            "license": plugin_json.get("license", ""),
            "repository": plugin_json.get("repository", ""),
        },
    }


def build_emporium_entry(plugin_json: dict, category: str) -> dict:
    """Build an emporium marketplace.json entry (no version field)."""
    mapped = CATEGORY_MAP.get(category, "development")
    repo = plugin_json.get("repository", "")
    return {
        "name": plugin_json["name"],
        "description": plugin_json["description"],
        "category": mapped,
        "source": {"source": "url", "url": f"{repo}.git" if repo else ""},
        "homepage": plugin_json.get("homepage", ""),
    }


def build_website_entry(plugin_json: dict, category: str) -> dict:
    """Build a website marketplace.json entry (has version)."""
    mapped = CATEGORY_MAP.get(category, "development")
    repo = plugin_json.get("repository", "")
    return {
        "name": plugin_json["name"],
        "description": plugin_json["description"],
        "version": plugin_json["version"],
        "category": mapped,
        "source": {"source": "url", "url": f"{repo}.git" if repo else ""},
        "homepage": plugin_json.get("homepage", ""),
    }


def build_meta_entry(plugin_json: dict, category: str) -> dict:
    """Build a website plugin-meta.json entry."""
    mapped = CATEGORY_MAP.get(category, "development")
    return {
        "category": mapped,
        "description": plugin_json["description"],
        "version": plugin_json["version"],
        "license": plugin_json.get("license", ""),
        "status": "alpha",
        "tags": list(plugin_json.get("keywords", [])),
        "verified": False,
    }


def make_adapters(config: ForgeConfig) -> dict[str, object]:
    """Construct registry adapters from config paths."""
    return {
        "skill7_registry": Skill7Registry(
            config.skill7_workspace / "registry.json"
        ),
        "emporium_marketplace": EmporiumMarketplace(
            config.emporium_path / ".claude-plugin" / "marketplace.json"
        ),
        "website_marketplace": WebsiteMarketplace(
            config.website_path / "src" / "data" / "marketplace.json"
        ),
        "website_plugin_meta": WebsitePluginMeta(
            config.website_path / "src" / "data" / "plugin-meta.json"
        ),
    }


def sync_plugin(
    plugin_dir: Path,
    config: ForgeConfig,
    *,
    dry_run: bool = True,
    adapters: dict | None = None,
) -> SyncResult:
    """Sync plugin.json to all registries.

    Returns SyncResult with per-target status (added/updated/unchanged).
    """
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    plugin_json = json.loads(pj_path.read_text())
    name = plugin_json["name"]
    category = derive_category(plugin_dir)

    if adapters is None:
        adapters = make_adapters(config)

    entries = {
        "skill7_registry": build_skill7_entry(plugin_json, category, plugin_dir),
        "emporium_marketplace": build_emporium_entry(plugin_json, category),
        "website_marketplace": build_website_entry(plugin_json, category),
        "website_plugin_meta": build_meta_entry(plugin_json, category),
    }

    result = SyncResult()

    for target_name, adapter in adapters.items():
        expected = entries[target_name]
        current = adapter.read_entry(name)

        if current == expected:
            result.statuses[target_name] = "unchanged"
            continue

        if dry_run:
            result.statuses[target_name] = "updated" if current else "added"
        else:
            if target_name == "skill7_registry":
                status = adapter.write_entry(name, expected, category=category)
            else:
                status = adapter.write_entry(name, expected)
            result.statuses[target_name] = status

    return result
