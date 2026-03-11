# tests/test_registry_io.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge.registry_io import (
    atomic_write_json,
    read_all_versions,
    RegistryIOError,
    Skill7Registry,
    EmporiumMarketplace,
    WebsiteMarketplace,
    WebsitePluginMeta,
)


class TestAtomicWrite:
    def test_writes_json(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        data = {"key": "value"}
        atomic_write_json(target, data)
        assert json.loads(target.read_text()) == data

    def test_no_temp_file_left(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        atomic_write_json(target, {"k": "v"})
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.json"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        target.write_text('{"old": true}')
        atomic_write_json(target, {"new": True})
        assert json.loads(target.read_text()) == {"new": True}


class TestSkill7Registry:
    def test_read_existing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        entry = adapter.read_entry("existing-plugin")
        assert entry is not None
        assert entry["name"] == "existing-plugin"
        assert entry["version"] == "0.5.0"

    def test_read_missing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        assert adapter.read_entry("nonexistent") is None

    def test_write_new_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        entry = {
            "name": "new-plugin",
            "description": "New",
            "version": "1.0.0",
            "path": "devtools/new-plugin",
            "allowed_tools": [],
            "skill_id": "new-plugin:new-plugin",
            "capabilities": [],
            "metadata": {},
        }
        adapter.write_entry("new-plugin", entry, category="devtools")
        assert adapter.read_entry("new-plugin") is not None

    def test_write_updates_existing(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        entry = adapter.read_entry("existing-plugin")
        entry["version"] = "0.6.0"
        adapter.write_entry("existing-plugin", entry, category="devtools")
        updated = adapter.read_entry("existing-plugin")
        assert updated["version"] == "0.6.0"

    def test_duplicate_in_different_category_raises(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        entry = {"name": "existing-plugin", "version": "1.0.0"}
        with pytest.raises(RegistryIOError, match="collision"):
            adapter.write_entry("existing-plugin", entry, category="creative")

    def test_read_entry_data_corruption_raises(self, registry_files: dict[str, Path]) -> None:
        data = json.loads(registry_files["skill7"].read_text())
        data["devtools"].append(data["devtools"][0].copy())
        registry_files["skill7"].write_text(json.dumps(data))
        adapter = Skill7Registry(registry_files["skill7"])
        with pytest.raises(RegistryIOError, match="corruption"):
            adapter.read_entry("existing-plugin")

    def test_entries_sorted_by_name(self, registry_files: dict[str, Path]) -> None:
        adapter = Skill7Registry(registry_files["skill7"])
        adapter.write_entry("aaa-plugin", {"name": "aaa-plugin", "version": "1.0.0"}, category="devtools")
        data = json.loads(registry_files["skill7"].read_text())
        names = [e["name"] for e in data["devtools"]]
        assert names == sorted(names)


class TestEmporiumMarketplace:
    def test_read_existing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = EmporiumMarketplace(registry_files["emporium"])
        entry = adapter.read_entry("existing-plugin")
        assert entry is not None
        assert entry["name"] == "existing-plugin"
        assert "version" not in entry

    def test_read_missing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = EmporiumMarketplace(registry_files["emporium"])
        assert adapter.read_entry("nonexistent") is None

    def test_write_preserves_top_level_keys(self, registry_files: dict[str, Path]) -> None:
        adapter = EmporiumMarketplace(registry_files["emporium"])
        entry = {"name": "new-plugin", "description": "New", "category": "development"}
        adapter.write_entry("new-plugin", entry)
        data = json.loads(registry_files["emporium"].read_text())
        assert data["name"] == "emporium"
        assert data["owner"] == "heurema"
        assert data["metadata"] == {"version": "1.0"}

    def test_write_new_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = EmporiumMarketplace(registry_files["emporium"])
        entry = {"name": "new-plugin", "description": "New", "category": "development"}
        adapter.write_entry("new-plugin", entry)
        assert adapter.read_entry("new-plugin") is not None

    def test_entries_sorted_by_name(self, registry_files: dict[str, Path]) -> None:
        adapter = EmporiumMarketplace(registry_files["emporium"])
        adapter.write_entry("aaa-plugin", {"name": "aaa-plugin", "description": "A"})
        data = json.loads(registry_files["emporium"].read_text())
        names = [p["name"] for p in data["plugins"]]
        assert names == sorted(names)

    def test_duplicate_raises(self, registry_files: dict[str, Path]) -> None:
        data = json.loads(registry_files["emporium"].read_text())
        data["plugins"].append(data["plugins"][0].copy())
        registry_files["emporium"].write_text(json.dumps(data))
        adapter = EmporiumMarketplace(registry_files["emporium"])
        with pytest.raises(RegistryIOError, match="corruption"):
            adapter.read_entry("existing-plugin")


class TestWebsiteMarketplace:
    def test_read_existing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsiteMarketplace(registry_files["website_marketplace"])
        entry = adapter.read_entry("existing-plugin")
        assert entry is not None
        assert entry["version"] == "0.5.0"

    def test_read_missing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsiteMarketplace(registry_files["website_marketplace"])
        assert adapter.read_entry("nonexistent") is None

    def test_write_new_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsiteMarketplace(registry_files["website_marketplace"])
        entry = {"name": "new-plugin", "version": "1.0.0", "category": "development"}
        adapter.write_entry("new-plugin", entry)
        data = json.loads(registry_files["website_marketplace"].read_text())
        names = [e["name"] for e in data["plugins"]]
        assert "new-plugin" in names

    def test_plugins_array_format(self, registry_files: dict[str, Path]) -> None:
        data = json.loads(registry_files["website_marketplace"].read_text())
        assert isinstance(data, dict)
        assert isinstance(data["plugins"], list)

    def test_entries_sorted_by_name(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsiteMarketplace(registry_files["website_marketplace"])
        adapter.write_entry("aaa-plugin", {"name": "aaa-plugin", "version": "1.0.0"})
        data = json.loads(registry_files["website_marketplace"].read_text())
        names = [e["name"] for e in data["plugins"]]
        assert names == sorted(names)


class TestWebsitePluginMeta:
    def test_read_existing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsitePluginMeta(registry_files["website_meta"])
        entry = adapter.read_entry("existing-plugin")
        assert entry is not None
        assert entry["version"] == "0.5.0"
        assert entry["verified"] is True

    def test_read_missing_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsitePluginMeta(registry_files["website_meta"])
        assert adapter.read_entry("nonexistent") is None

    def test_write_new_entry(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsitePluginMeta(registry_files["website_meta"])
        entry = {"version": "1.0.0", "license": "MIT", "status": "alpha", "tags": []}
        adapter.write_entry("new-plugin", entry)
        data = json.loads(registry_files["website_meta"].read_text())
        assert "new-plugin" in data["plugins"]

    def test_write_updates_existing(self, registry_files: dict[str, Path]) -> None:
        adapter = WebsitePluginMeta(registry_files["website_meta"])
        entry = adapter.read_entry("existing-plugin")
        entry["version"] = "0.6.0"
        adapter.write_entry("existing-plugin", entry)
        updated = adapter.read_entry("existing-plugin")
        assert updated["version"] == "0.6.0"

    def test_dict_keyed_format(self, registry_files: dict[str, Path]) -> None:
        data = json.loads(registry_files["website_meta"].read_text())
        assert isinstance(data["plugins"], dict)


class TestReadAllVersions:
    def test_returns_versions_from_targets_that_have_them(self, registry_files: dict[str, Path]) -> None:
        targets = {
            "skill7_registry": Skill7Registry(registry_files["skill7"]),
            "emporium_marketplace": EmporiumMarketplace(registry_files["emporium"]),
            "website_marketplace": WebsiteMarketplace(registry_files["website_marketplace"]),
            "website_plugin_meta": WebsitePluginMeta(registry_files["website_meta"]),
        }
        versions = read_all_versions(targets, "existing-plugin")
        assert versions["skill7_registry"] == "0.5.0"
        assert versions["website_marketplace"] == "0.5.0"
        assert versions["website_plugin_meta"] == "0.5.0"
        assert "emporium_marketplace" not in versions

    def test_missing_entry_returns_empty(self, registry_files: dict[str, Path]) -> None:
        targets = {
            "skill7_registry": Skill7Registry(registry_files["skill7"]),
        }
        versions = read_all_versions(targets, "nonexistent")
        assert versions == {}
