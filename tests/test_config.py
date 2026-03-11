"""Tests for forge config module."""

import textwrap
from pathlib import Path

import pytest

from forge.config import ConfigError, ForgeConfig, load_config, derive_category, VALID_CATEGORIES


class TestForgeConfig:
    def test_load_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".claude" / "forge.local.md"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            default_type: marketplace
            default_category: devtools
            ---
        """)
        )
        cfg = load_config(config_file)
        assert cfg.skill7_workspace == Path("/tmp/skill7")
        assert cfg.emporium_path == Path("/tmp/emporium")
        assert cfg.website_path == Path("/tmp/skill7dev")
        assert cfg.github_org == "heurema"
        assert cfg.default_type == "marketplace"
        assert cfg.default_category == "devtools"

    def test_load_missing_file_raises(self) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config(Path("/nonexistent/forge.local.md"))

    def test_load_missing_required_field(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text("---\nskill7_workspace: /tmp\n---\n")
        with pytest.raises(ConfigError, match="emporium_path"):
            load_config(config_file)

    def test_defaults_applied(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            ---
        """)
        )
        cfg = load_config(config_file)
        assert cfg.default_type == "marketplace"
        assert cfg.default_category == "devtools"

    def test_invalid_category_raises(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            default_category: invalid
            ---
        """)
        )
        with pytest.raises(ConfigError, match="default_category"):
            load_config(config_file)

    def test_readme_template_loaded(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            readme_template: ~/my-templates/README.md.j2
            ---
        """)
        )
        cfg = load_config(config_file)
        assert cfg.readme_template is not None
        assert str(cfg.readme_template).endswith("my-templates/README.md.j2")
        assert "~" not in str(cfg.readme_template)

    def test_readme_template_default_none(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            ---
        """)
        )
        cfg = load_config(config_file)
        assert cfg.readme_template is None

    def test_invalid_type_raises(self, tmp_path: Path) -> None:
        config_file = tmp_path / "forge.local.md"
        config_file.write_text(
            textwrap.dedent("""\
            ---
            skill7_workspace: /tmp/skill7
            emporium_path: /tmp/emporium
            website_path: /tmp/skill7dev
            github_org: heurema
            default_type: invalid
            ---
        """)
        )
        with pytest.raises(ConfigError, match="default_type"):
            load_config(config_file)


class TestRequirePath:
    def test_existing_path_returns_it(self, tmp_path: Path) -> None:
        cfg = ForgeConfig(
            skill7_workspace=tmp_path,
            emporium_path=tmp_path,
            website_path=tmp_path,
            github_org="heurema",
            default_type="marketplace",
            default_category="devtools",
            readme_template=None,
        )
        assert cfg.require_path("skill7_workspace") == tmp_path

    def test_missing_path_raises(self, tmp_path: Path) -> None:
        cfg = ForgeConfig(
            skill7_workspace=tmp_path / "nonexistent",
            emporium_path=tmp_path,
            website_path=tmp_path,
            github_org="heurema",
            default_type="marketplace",
            default_category="devtools",
            readme_template=None,
        )
        with pytest.raises(ConfigError, match="skill7_workspace"):
            cfg.require_path("skill7_workspace")


class TestDeriveCategory:
    def test_devtools_category(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "devtools" / "my-plugin"
        plugin_dir.mkdir(parents=True)
        assert derive_category(plugin_dir) == "devtools"

    def test_publishing_category(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "publishing" / "my-plugin"
        plugin_dir.mkdir(parents=True)
        assert derive_category(plugin_dir) == "publishing"

    def test_unknown_category_raises(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "unknown" / "my-plugin"
        plugin_dir.mkdir(parents=True)
        with pytest.raises(ConfigError, match="unknown"):
            derive_category(plugin_dir)


class TestValidCategories:
    def test_includes_publishing_and_research(self) -> None:
        assert "publishing" in VALID_CATEGORIES
        assert "research" in VALID_CATEGORIES
