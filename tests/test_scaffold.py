"""Tests for forge scaffold module."""

import json
from pathlib import Path

import pytest

from forge.scaffold import ScaffoldError, scaffold_plugin, validate_plugin_name


class TestValidateName:
    def test_valid_name(self) -> None:
        validate_plugin_name("my-plugin")

    def test_valid_name_with_numbers(self) -> None:
        validate_plugin_name("plugin-2")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ScaffoldError, match="empty"):
            validate_plugin_name("")

    def test_path_traversal_raises(self) -> None:
        with pytest.raises(ScaffoldError, match="Invalid"):
            validate_plugin_name("../evil")

    def test_slash_raises(self) -> None:
        with pytest.raises(ScaffoldError, match="Invalid"):
            validate_plugin_name("foo/bar")

    def test_uppercase_raises(self) -> None:
        with pytest.raises(ScaffoldError, match="lowercase"):
            validate_plugin_name("MyPlugin")


class TestScaffold:
    def test_creates_plugin_json(self, tmp_path: Path) -> None:
        target = tmp_path / "test-plugin"
        scaffold_plugin(
            target_dir=target,
            name="test-plugin",
            plugin_type="marketplace",
            category="devtools",
            description="A test",
            github_org="heurema",
            templates_dir=Path(__file__).parent.parent / "templates",
        )
        manifest = target / ".claude-plugin" / "plugin.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["name"] == "test-plugin"
        assert data["version"] == "0.1.0"

    def test_creates_gitignore(self, tmp_path: Path) -> None:
        target = tmp_path / "test-plugin"
        scaffold_plugin(
            target_dir=target,
            name="test-plugin",
            plugin_type="local",
            category="devtools",
            description="A test",
            github_org="heurema",
            templates_dir=Path(__file__).parent.parent / "templates",
        )
        gitignore = target / ".gitignore"
        assert gitignore.exists()
        assert "__pycache__" in gitignore.read_text()

    def test_marketplace_has_install_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "test-plugin"
        scaffold_plugin(
            target_dir=target,
            name="test-plugin",
            plugin_type="marketplace",
            category="devtools",
            description="A test",
            github_org="heurema",
            templates_dir=Path(__file__).parent.parent / "templates",
        )
        readme = target / "README.md"
        assert "<!-- INSTALL:START" in readme.read_text()

    def test_local_no_install_markers(self, tmp_path: Path) -> None:
        target = tmp_path / "test-plugin"
        scaffold_plugin(
            target_dir=target,
            name="test-plugin",
            plugin_type="local",
            category="devtools",
            description="A test",
            github_org="heurema",
            templates_dir=Path(__file__).parent.parent / "templates",
        )
        readme = target / "README.md"
        assert "<!-- INSTALL:START" not in readme.read_text()

    def test_existing_dir_raises(self, tmp_path: Path) -> None:
        target = tmp_path / "exists"
        target.mkdir()
        with pytest.raises(ScaffoldError, match="already exists"):
            scaffold_plugin(
                target_dir=target,
                name="exists",
                plugin_type="local",
                category="devtools",
                description="A test",
                github_org="heurema",
                templates_dir=Path(__file__).parent.parent / "templates",
            )

    def test_creates_empty_dirs(self, tmp_path: Path) -> None:
        target = tmp_path / "test-plugin"
        scaffold_plugin(
            target_dir=target,
            name="test-plugin",
            plugin_type="marketplace",
            category="devtools",
            description="A test",
            github_org="heurema",
            templates_dir=Path(__file__).parent.parent / "templates",
        )
        assert (target / "skills").is_dir()
        assert (target / "commands").is_dir()
