"""Audit: rubric snapshot validation + cross-repo consistency checks."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from forge.config import ForgeConfig
from forge.registry_io import (
    Skill7Registry,
    EmporiumMarketplace,
    WebsiteMarketplace,
    WebsitePluginMeta,
    read_all_versions,
)


SUPPORTED_RUBRIC_SCHEMAS = {"1.0"}


@dataclass
class SnapshotValidation:
    valid: bool
    error: str = ""


@dataclass
class AuditResult:
    rubric_score: int | None = None
    rubric_errors: list[str] = field(default_factory=list)
    consistency_errors: list[str] = field(default_factory=list)
    snapshot_error: str | None = None


def validate_rubric_snapshot(snap_dir: Path) -> SnapshotValidation:
    """Validate rubric snapshot directory: manifest, schema version, content hash."""
    manifest_path = snap_dir / "manifest.json"
    if not manifest_path.exists():
        return SnapshotValidation(valid=False, error="Rubric snapshot missing. Run `forge doctor` to refresh.")

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return SnapshotValidation(valid=False, error=f"Cannot read manifest: {e}")

    schema = manifest.get("schema_version", "")
    if schema not in SUPPORTED_RUBRIC_SCHEMAS:
        return SnapshotValidation(
            valid=False,
            error=f"Unsupported schema_version '{schema}'. Supported: {SUPPORTED_RUBRIC_SCHEMAS}",
        )

    init_path = snap_dir / "__init__.py"
    if not init_path.exists():
        return SnapshotValidation(valid=False, error="__init__.py missing from snapshot")

    expected_hash = manifest.get("content_hash", "")
    actual_hash = "sha256:" + hashlib.sha256(init_path.read_text().encode()).hexdigest()
    if actual_hash != expected_hash:
        return SnapshotValidation(valid=False, error="Content hash mismatch — snapshot may be corrupt")

    return SnapshotValidation(valid=True)


def _check_changelog_version(plugin_dir: Path, expected_version: str) -> str | None:
    """Check that CHANGELOG.md top version matches expected_version."""
    cl_path = plugin_dir / "CHANGELOG.md"
    if not cl_path.exists():
        return None
    content = cl_path.read_text()
    match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
    if not match:
        return None
    top_version = match.group(1)
    if top_version != expected_version:
        return f"CHANGELOG top version [{top_version}] != plugin.json [{expected_version}]"
    return None


def audit_plugin(
    plugin_dir: Path,
    config: ForgeConfig,
    *,
    allow_stale: bool = False,
    adapters: dict | None = None,
) -> AuditResult:
    """Run audit checks: rubric snapshot + cross-repo consistency."""
    result = AuditResult()

    # 1. Rubric snapshot validation
    snap_dir = Path(__file__).parent / "rubric_snapshot"
    snap_validation = validate_rubric_snapshot(snap_dir)
    if not snap_validation.valid:
        result.snapshot_error = snap_validation.error
        if not allow_stale:
            return result  # fail-closed

    # 2. If snapshot valid, run rubric checks (if functions available)
    if snap_validation.valid:
        try:
            from forge.rubric_snapshot import check_readme
            # Run checks if available (stub won't have them)
            # This is where the 12 rubric functions would be called
        except (ImportError, AttributeError):
            pass  # Stub module — no checks available

    # 3. Cross-repo consistency: versions
    pj_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if pj_path.exists():
        plugin_json = json.loads(pj_path.read_text())
        name = plugin_json["name"]
        expected_version = plugin_json["version"]
        expected_desc = plugin_json["description"]

        if adapters is None:
            from forge.sync import make_adapters
            adapters = make_adapters(config)

        versions = read_all_versions(adapters, name)
        for target, version in versions.items():
            if version != expected_version:
                result.consistency_errors.append(
                    f"Version mismatch in {target}: {version} != {expected_version} (plugin.json)"
                )

        # 4. Description consistency
        for target_name, adapter in adapters.items():
            entry = adapter.read_entry(name)
            if entry and "description" in entry:
                if entry["description"] != expected_desc:
                    result.consistency_errors.append(
                        f"Description mismatch in {target_name}: "
                        f"'{entry['description']}' != '{expected_desc}' (plugin.json)"
                    )

        # 5. CHANGELOG version check
        cl_error = _check_changelog_version(plugin_dir, expected_version)
        if cl_error:
            result.consistency_errors.append(cl_error)

    return result
