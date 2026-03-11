# tests/test_sync.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge.sync import (
    CATEGORY_MAP,
    SyncResult,
    build_emporium_entry,
    build_meta_entry,
    build_skill7_entry,
    build_website_entry,
    make_adapters,
    sync_plugin,
)
from forge.registry_io import (
    EmporiumMarketplace,
    Skill7Registry,
    WebsiteMarketplace,
    WebsitePluginMeta,
)


def _load_plugin_json(sample_plugin: Path) -> dict:
    return json.loads(
        (sample_plugin / ".claude-plugin" / "plugin.json").read_text()
    )


def _make_adapters(registry_files: dict[str, Path]) -> dict[str, object]:
    """Build adapters pointing at test fixture files."""
    return {
        "skill7_registry": Skill7Registry(registry_files["skill7"]),
        "emporium_marketplace": EmporiumMarketplace(registry_files["emporium"]),
        "website_marketplace": WebsiteMarketplace(
            registry_files["website_marketplace"]
        ),
        "website_plugin_meta": WebsitePluginMeta(registry_files["website_meta"]),
    }


# --- build_skill7_entry ---


class TestBuildSkill7Entry:
    def test_maps_all_fields(self, sample_plugin: Path) -> None:
        pj = _load_plugin_json(sample_plugin)
        entry = build_skill7_entry(pj, category="devtools", plugin_dir=sample_plugin)

        assert entry["name"] == "sample-plugin"
        assert entry["description"] == "A sample plugin for testing"
        assert entry["version"] == "1.2.3"
        assert entry["path"] == "devtools/sample-plugin"
        assert entry["allowed_tools"] == []
        assert entry["skill_id"] == "sample-plugin:sample"
        assert entry["capabilities"] == ["testing", "sample"]
        assert entry["metadata"]["author"] == "heurema"
        assert entry["metadata"]["compatibility"] == "claude-code"
        assert entry["metadata"]["license"] == "MIT"
        assert entry["metadata"]["repository"] == "https://github.com/heurema/sample-plugin"
        assert entry["metadata"]["homepage"] == "https://github.com/heurema/sample-plugin"
        assert entry["metadata"]["keywords"] == ["testing", "sample"]

    def test_no_skills_dir_uses_name(self, tmp_path: Path) -> None:
        """When skills/ dir doesn't exist, skill_id uses plugin name."""
        plugin_dir = tmp_path / "devtools" / "no-skills"
        plugin_dir.mkdir(parents=True)
        pj = {"name": "no-skills", "description": "test", "version": "0.1.0"}
        entry = build_skill7_entry(pj, "devtools", plugin_dir)
        assert entry["skill_id"] == "no-skills:no-skills"

    def test_multiple_skills_uses_sorted_first(self, tmp_path: Path) -> None:
        """When multiple skill dirs exist, use sorted first."""
        plugin_dir = tmp_path / "devtools" / "multi"
        (plugin_dir / "skills" / "beta").mkdir(parents=True)
        (plugin_dir / "skills" / "alpha").mkdir(parents=True)
        pj = {"name": "multi", "description": "test", "version": "0.1.0"}
        entry = build_skill7_entry(pj, "devtools", plugin_dir)
        assert entry["skill_id"] == "multi:alpha"


# --- build_emporium_entry ---


class TestBuildEmporiumEntry:
    def test_maps_fields(self, sample_plugin: Path) -> None:
        pj = _load_plugin_json(sample_plugin)
        entry = build_emporium_entry(pj, "devtools")

        assert entry["name"] == "sample-plugin"
        assert entry["description"] == "A sample plugin for testing"
        assert entry["category"] == "development"
        assert entry["source"] == {
            "source": "url",
            "url": "https://github.com/heurema/sample-plugin.git",
        }
        assert entry["homepage"] == "https://github.com/heurema/sample-plugin"
        assert "version" not in entry

    def test_category_mapping(self) -> None:
        pj = {"name": "x", "description": "d", "version": "1.0.0"}
        for raw_cat, mapped_cat in CATEGORY_MAP.items():
            entry = build_emporium_entry(pj, raw_cat)
            assert entry["category"] == mapped_cat

    def test_unknown_category_defaults_to_development(self) -> None:
        pj = {"name": "x", "description": "d", "version": "1.0.0"}
        entry = build_emporium_entry(pj, "unknown")
        assert entry["category"] == "development"


# --- build_website_entry ---


class TestBuildWebsiteEntry:
    def test_has_version(self, sample_plugin: Path) -> None:
        pj = _load_plugin_json(sample_plugin)
        entry = build_website_entry(pj, "devtools")

        assert entry["version"] == "1.2.3"
        assert entry["name"] == "sample-plugin"
        assert entry["category"] == "development"
        assert entry["source"]["url"] == "https://github.com/heurema/sample-plugin.git"

    def test_category_mapping(self) -> None:
        pj = {"name": "x", "description": "d", "version": "1.0.0"}
        entry = build_website_entry(pj, "trading")
        assert entry["category"] == "trading"


# --- build_meta_entry ---


class TestBuildMetaEntry:
    def test_maps_fields(self, sample_plugin: Path) -> None:
        pj = _load_plugin_json(sample_plugin)
        entry = build_meta_entry(pj, "devtools")

        assert entry["category"] == "development"
        assert entry["description"] == pj["description"]
        assert entry["version"] == "1.2.3"
        assert entry["license"] == "MIT"
        assert entry["status"] == "alpha"
        assert entry["tags"] == ["testing", "sample"]
        assert entry["verified"] is False


# --- make_adapters ---


class TestMakeAdapters:
    def test_returns_all_four_keys(self, forge_config) -> None:
        adapters = make_adapters(forge_config)
        assert set(adapters.keys()) == {
            "skill7_registry",
            "emporium_marketplace",
            "website_marketplace",
            "website_plugin_meta",
        }

    def test_adapter_types(self, forge_config) -> None:
        adapters = make_adapters(forge_config)
        assert isinstance(adapters["skill7_registry"], Skill7Registry)
        assert isinstance(adapters["emporium_marketplace"], EmporiumMarketplace)
        assert isinstance(adapters["website_marketplace"], WebsiteMarketplace)
        assert isinstance(adapters["website_plugin_meta"], WebsitePluginMeta)


# --- sync_plugin ---


class TestSyncPlugin:
    def test_dry_run_reports_added(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        adapters = _make_adapters(registry_files)
        result = sync_plugin(
            sample_plugin, forge_config, dry_run=True, adapters=adapters
        )

        assert isinstance(result, SyncResult)
        assert result.statuses["skill7_registry"] == "added"
        assert result.statuses["emporium_marketplace"] == "added"
        assert result.statuses["website_marketplace"] == "added"
        assert result.statuses["website_plugin_meta"] == "added"

    def test_dry_run_does_not_modify_files(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        adapters = _make_adapters(registry_files)
        # Snapshot before
        before = {k: p.read_text() for k, p in registry_files.items()}
        sync_plugin(sample_plugin, forge_config, dry_run=True, adapters=adapters)
        # Verify unchanged
        for k, p in registry_files.items():
            assert p.read_text() == before[k], f"{k} was modified during dry_run"

    def test_apply_writes_all_targets(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        adapters = _make_adapters(registry_files)
        result = sync_plugin(
            sample_plugin, forge_config, dry_run=False, adapters=adapters
        )

        assert result.statuses["skill7_registry"] == "added"
        assert result.statuses["emporium_marketplace"] == "added"
        assert result.statuses["website_marketplace"] == "added"
        assert result.statuses["website_plugin_meta"] == "added"

        # Verify skill7 registry has the entry
        data = json.loads(registry_files["skill7"].read_text())
        names = [e["name"] for cat in data.values() for e in cat]
        assert "sample-plugin" in names

        # Verify emporium marketplace has the entry
        data = json.loads(registry_files["emporium"].read_text())
        names = [p["name"] for p in data["plugins"]]
        assert "sample-plugin" in names

        # Verify website marketplace has the entry
        data = json.loads(registry_files["website_marketplace"].read_text())
        names = [e["name"] for e in data["plugins"]]
        assert "sample-plugin" in names

        # Verify plugin-meta has the entry
        data = json.loads(registry_files["website_meta"].read_text())
        assert "sample-plugin" in data["plugins"]

    def test_idempotent_rerun(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        result2 = sync_plugin(
            sample_plugin, forge_config, dry_run=False, adapters=adapters
        )
        assert all(s == "unchanged" for s in result2.statuses.values()), (
            f"Expected all unchanged, got {result2.statuses}"
        )

    def test_dry_run_reports_updated_for_existing(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        """If entry exists but differs, dry_run reports 'updated'."""
        adapters = _make_adapters(registry_files)
        # First write
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)

        # Modify plugin.json to trigger a diff
        pj_path = sample_plugin / ".claude-plugin" / "plugin.json"
        pj = json.loads(pj_path.read_text())
        pj["description"] = "Updated description"
        pj_path.write_text(json.dumps(pj))

        # Re-create adapters to pick up fresh data
        adapters = _make_adapters(registry_files)
        result = sync_plugin(
            sample_plugin, forge_config, dry_run=True, adapters=adapters
        )
        assert result.statuses["skill7_registry"] == "updated"

    def test_returns_sync_result_dataclass(
        self, sample_plugin, registry_files, forge_config
    ) -> None:
        adapters = _make_adapters(registry_files)
        result = sync_plugin(
            sample_plugin, forge_config, dry_run=True, adapters=adapters
        )
        assert hasattr(result, "statuses")
        assert isinstance(result.statuses, dict)
        assert len(result.statuses) == 4
