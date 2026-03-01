"""Tests for forge config module."""

import textwrap
from pathlib import Path

import pytest

from forge.config import ConfigError, load_config


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
