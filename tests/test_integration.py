# tests/test_integration.py
"""Integration tests using sample-plugin fixture + temp registries."""
import json
from pathlib import Path

from forge.audit import audit_plugin
from forge.bump import bump_version
from forge.registry_io import (
    EmporiumMarketplace,
    Skill7Registry,
    WebsiteMarketplace,
    WebsitePluginMeta,
)
from forge.sync import sync_plugin


def _make_adapters(registry_files: dict[str, Path]) -> dict[str, object]:
    """Build adapters directly from registry_files fixture paths."""
    return {
        "skill7_registry": Skill7Registry(registry_files["skill7"]),
        "emporium_marketplace": EmporiumMarketplace(registry_files["emporium"]),
        "website_marketplace": WebsiteMarketplace(registry_files["website_marketplace"]),
        "website_plugin_meta": WebsitePluginMeta(registry_files["website_meta"]),
    }


class TestFullFlow:
    def test_doctor_sync_bump_audit(self, sample_plugin, registry_files, forge_config, tmp_path):
        """forge doctor → sync → bump → audit → sync again."""
        config = forge_config
        adapters = _make_adapters(registry_files)

        # 1. Sync adds plugin to all registries
        result = sync_plugin(sample_plugin, config, dry_run=False, adapters=adapters)
        assert all(s == "added" for s in result.statuses.values())

        # 2. Audit passes (skip rubric, test consistency only)
        audit = audit_plugin(sample_plugin, config, allow_stale=True, adapters=adapters)
        assert len(audit.consistency_errors) == 0

        # 3. Bump patch
        bump = bump_version(sample_plugin, config, "patch", dry_run=False, adapters=adapters)
        assert bump.new_version == "1.2.4"

        # 4. Audit passes again (bump syncs registries)
        audit2 = audit_plugin(sample_plugin, config, allow_stale=True, adapters=adapters)
        assert len(audit2.consistency_errors) == 0

    def test_desync_detection_and_fix(self, sample_plugin, registry_files, forge_config, tmp_path):
        """Manually desync → audit detects → sync fixes → audit passes."""
        config = forge_config
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, config, dry_run=False, adapters=adapters)

        # Manually desync: change version in one registry
        data = json.loads(registry_files["skill7"].read_text())
        for cat in data.values():
            for e in cat:
                if e["name"] == "sample-plugin":
                    e["version"] = "0.0.1"
        registry_files["skill7"].write_text(json.dumps(data, indent=2))

        # Audit detects
        audit = audit_plugin(sample_plugin, config, allow_stale=True, adapters=adapters)
        assert len(audit.consistency_errors) > 0

        # Sync fixes
        sync_plugin(sample_plugin, config, dry_run=False, adapters=adapters)

        # Audit passes
        audit2 = audit_plugin(sample_plugin, config, allow_stale=True, adapters=adapters)
        assert len(audit2.consistency_errors) == 0
