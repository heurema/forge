# tests/test_audit.py
import json
from pathlib import Path

import pytest

from conftest import make_valid_snapshot
from forge.audit import (
    audit_plugin,
    AuditResult,
    validate_rubric_snapshot,
    SUPPORTED_RUBRIC_SCHEMAS,
)
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


class TestValidateRubricSnapshot:
    def test_missing_manifest_errors(self, tmp_path: Path) -> None:
        result = validate_rubric_snapshot(tmp_path / "rubric_snapshot")
        assert not result.valid
        assert "forge doctor" in result.error.lower() or "missing" in result.error.lower()

    def test_unsupported_schema_errors(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "rubric_snapshot"
        snap_dir.mkdir()
        (snap_dir / "__init__.py").write_text("# rubric")
        manifest = {"schema_version": "99.0", "content_hash": "sha256:abc"}
        (snap_dir / "manifest.json").write_text(json.dumps(manifest))
        result = validate_rubric_snapshot(snap_dir)
        assert not result.valid
        assert "schema_version" in result.error

    def test_hash_mismatch_errors(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "rubric_snapshot"
        snap_dir.mkdir()
        (snap_dir / "__init__.py").write_text("# rubric code")
        manifest = {"schema_version": "1.0", "content_hash": "sha256:wrong"}
        (snap_dir / "manifest.json").write_text(json.dumps(manifest))
        result = validate_rubric_snapshot(snap_dir)
        assert not result.valid
        assert "corrupt" in result.error.lower() or "hash" in result.error.lower()

    def test_valid_snapshot_passes(self, tmp_path: Path) -> None:
        snap_dir = make_valid_snapshot(tmp_path)
        result = validate_rubric_snapshot(snap_dir)
        assert result.valid


class TestAuditConsistency:
    def test_version_mismatch_detected(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        # Write mismatched version in skill7 registry
        data = json.loads(registry_files["skill7"].read_text())
        data["devtools"].append({
            "name": "sample-plugin", "version": "0.0.1",
            "path": "devtools/sample-plugin",
        })
        registry_files["skill7"].write_text(json.dumps(data))
        result = audit_plugin(sample_plugin, forge_config, allow_stale=True, adapters=adapters)
        assert any("version" in f.lower() for f in result.consistency_errors)

    def test_changelog_version_mismatch_detected(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        cl_path = sample_plugin / "CHANGELOG.md"
        cl_path.write_text("# CHANGELOG\n\n## [9.9.9] - 2026-01-01\n\n- Wrong version\n")
        result = audit_plugin(sample_plugin, forge_config, allow_stale=True, adapters=adapters)
        assert any("changelog" in f.lower() for f in result.consistency_errors)

    def test_description_mismatch_detected(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        emp = json.loads(registry_files["emporium"].read_text())
        for p in emp["plugins"]:
            if p["name"] == "sample-plugin":
                p["description"] = "WRONG description"
        registry_files["emporium"].write_text(json.dumps(emp))
        result = audit_plugin(sample_plugin, forge_config, allow_stale=True, adapters=adapters)
        assert any("description" in f.lower() for f in result.consistency_errors)

    def test_all_matching_passes(self, sample_plugin, registry_files, forge_config, tmp_path) -> None:
        adapters = _make_adapters(registry_files)
        sync_plugin(sample_plugin, forge_config, dry_run=False, adapters=adapters)
        result = audit_plugin(sample_plugin, forge_config, allow_stale=True, adapters=adapters)
        assert len(result.consistency_errors) == 0
