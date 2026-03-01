"""Tests for forge register module."""

import json
from pathlib import Path

from forge.register import (
    add_to_marketplace_json,
    add_to_registry,
    build_marketplace_entry,
    determine_targets,
)


class TestDetermineTargets:
    def test_marketplace_all_targets(self) -> None:
        targets = determine_targets("marketplace")
        names = {t.name for t in targets}
        assert "skill7_registry" in names
        assert "emporium" in names
        assert "website_marketplace" in names
        assert "website_plugin_meta" in names

    def test_project_only_registry(self) -> None:
        targets = determine_targets("project")
        names = {t.name for t in targets}
        assert "skill7_registry" in names
        assert "emporium" not in names

    def test_local_no_targets(self) -> None:
        targets = determine_targets("local")
        assert len(targets) == 0


class TestAddToMarketplace:
    def test_adds_new_entry_flat_format(self, tmp_path: Path) -> None:
        """Website-style flat array format."""
        mp_file = tmp_path / "marketplace.json"
        mp_file.write_text(json.dumps([{"name": "existing"}]))
        entry = {"name": "new-plugin", "description": "test", "category": "development"}
        add_to_marketplace_json(mp_file, entry)
        data = json.loads(mp_file.read_text())
        assert len(data) == 2
        assert data[1]["name"] == "new-plugin"

    def test_adds_new_entry_dict_format(self, tmp_path: Path) -> None:
        """Emporium-style dict with plugins key."""
        mp_file = tmp_path / "marketplace.json"
        mp_file.write_text(json.dumps({"name": "emporium", "plugins": [{"name": "existing"}]}))
        entry = {"name": "new-plugin", "description": "test", "category": "development"}
        add_to_marketplace_json(mp_file, entry)
        data = json.loads(mp_file.read_text())
        assert isinstance(data, dict)
        assert len(data["plugins"]) == 2
        assert data["plugins"][1]["name"] == "new-plugin"

    def test_skip_duplicate(self, tmp_path: Path) -> None:
        mp_file = tmp_path / "marketplace.json"
        mp_file.write_text(json.dumps({"plugins": [{"name": "existing"}]}))
        entry = {"name": "existing", "description": "test", "category": "development"}
        result = add_to_marketplace_json(mp_file, entry)
        assert result is False  # already exists
        data = json.loads(mp_file.read_text())
        assert len(data["plugins"]) == 1

    def test_sorted_output(self, tmp_path: Path) -> None:
        mp_file = tmp_path / "marketplace.json"
        mp_file.write_text(json.dumps({"plugins": [{"name": "zebra"}]}))
        entry = {"name": "alpha", "description": "test", "category": "development"}
        add_to_marketplace_json(mp_file, entry)
        data = json.loads(mp_file.read_text())
        assert data["plugins"][0]["name"] == "alpha"
        assert data["plugins"][1]["name"] == "zebra"


class TestBuildMarketplaceEntry:
    def test_devtools_maps_to_development(self) -> None:
        entry = build_marketplace_entry("test", "desc", "devtools", "heurema")
        assert entry["category"] == "development"
        assert entry["name"] == "test"
        assert "heurema/test.git" in entry["source"]["url"]

    def test_trading_maps_to_trading(self) -> None:
        entry = build_marketplace_entry("test", "desc", "trading", "heurema")
        assert entry["category"] == "trading"

    def test_unknown_category_defaults_development(self) -> None:
        entry = build_marketplace_entry("test", "desc", "unknown", "heurema")
        assert entry["category"] == "development"


class TestAddToRegistry:
    def test_adds_to_correct_category(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({"devtools": []}))
        add_to_registry(reg_file, "new-plugin", "devtools", "0.1.0", description="A plugin")
        data = json.loads(reg_file.read_text())
        assert len(data["devtools"]) == 1
        entry = data["devtools"][0]
        assert entry["name"] == "new-plugin"
        assert entry["description"] == "A plugin"
        assert entry["owner"] == "heurema"
        assert entry["status"] == "active"
        assert entry["path"] == "devtools/new-plugin"
        assert "devtools" in entry["tags"]

    def test_creates_category_if_missing(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({}))
        add_to_registry(reg_file, "new-plugin", "trading", "0.1.0")
        data = json.loads(reg_file.read_text())
        assert "trading" in data

    def test_skip_duplicate(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({"devtools": [{"name": "existing"}]}))
        result = add_to_registry(reg_file, "existing", "devtools", "0.1.0")
        assert result is False
