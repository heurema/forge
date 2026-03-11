# tests/test_bump.py
import json
from pathlib import Path

import pytest

from forge.bump import bump_version, BumpResult, compute_next_version
from forge.sync import sync_plugin
from forge.registry_io import (
    Skill7Registry,
    EmporiumMarketplace,
    WebsiteMarketplace,
    WebsitePluginMeta,
)


def _make_adapters(registry_files):
    return {
        "skill7_registry": Skill7Registry(registry_files["skill7"]),
        "emporium_marketplace": EmporiumMarketplace(registry_files["emporium"]),
        "website_marketplace": WebsiteMarketplace(registry_files["website_marketplace"]),
        "website_plugin_meta": WebsitePluginMeta(registry_files["website_meta"]),
    }


class TestComputeNextVersion:
    def test_patch(self) -> None:
        assert compute_next_version("1.2.3", "patch") == "1.2.4"

    def test_minor(self) -> None:
        assert compute_next_version("1.2.3", "minor") == "1.3.0"

    def test_major(self) -> None:
        assert compute_next_version("1.2.3", "major") == "2.0.0"


class TestBumpVersion:
    def test_dry_run_shows_changes(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        result = bump_version(sample_plugin, forge_config, "patch", dry_run=True, adapters=adapters)
        assert result.new_version == "1.2.4"
        # plugin.json not modified
        pj = json.loads((sample_plugin / ".claude-plugin" / "plugin.json").read_text())
        assert pj["version"] == "1.2.3"

    def test_apply_writes_all(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        result = bump_version(sample_plugin, forge_config, "patch", dry_run=False, adapters=adapters)
        assert result.new_version == "1.2.4"
        pj = json.loads((sample_plugin / ".claude-plugin" / "plugin.json").read_text())
        assert pj["version"] == "1.2.4"
        cl = (sample_plugin / "CHANGELOG.md").read_text()
        assert "## [1.2.4]" in cl

    def test_idempotent_rerun(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        bump_version(sample_plugin, forge_config, "patch", dry_run=False, adapters=adapters)
        result2 = bump_version(sample_plugin, forge_config, "patch", dry_run=False, adapters=adapters)
        assert result2.new_version == "1.2.5"

    def test_partial_failure_rolls_back(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        """If a config path is invalid, bump should raise before writing anything."""
        from forge.config import ForgeConfig, ConfigError
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        broken_config = ForgeConfig(
            skill7_workspace=tmp_path,
            emporium_path=tmp_path / "emporium-repo",
            website_path=tmp_path / "nonexistent-website",
            github_org="heurema",
            default_type="marketplace",
            default_category="devtools",
            readme_template=None,
        )
        with pytest.raises(ConfigError):
            bump_version(sample_plugin, broken_config, "patch", dry_run=False, adapters=adapters)
        pj = json.loads((sample_plugin / ".claude-plugin" / "plugin.json").read_text())
        assert pj["version"] == "1.2.3"
