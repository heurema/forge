# tests/conftest.py
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_plugin(tmp_path: Path) -> Path:
    """Copy sample-plugin fixture to tmp_path and return its path."""
    dest = tmp_path / "devtools" / "sample-plugin"
    shutil.copytree(FIXTURES_DIR / "sample-plugin", dest)
    return dest


@pytest.fixture
def registry_files(tmp_path: Path) -> dict[str, Path]:
    """Copy registry fixtures to tmp_path and return paths dict."""
    reg_dir = tmp_path / "registries"
    shutil.copytree(FIXTURES_DIR / "registries", reg_dir)
    return {
        "skill7": reg_dir / "registry.json",
        "emporium": reg_dir / "emporium-marketplace.json",
        "website_marketplace": reg_dir / "website-marketplace.json",
        "website_meta": reg_dir / "plugin-meta.json",
    }


@pytest.fixture
def forge_config(tmp_path: Path, registry_files: dict[str, Path]) -> "ForgeConfig":
    """Build a ForgeConfig pointing to tmp registry files for testing.

    Website adapter paths are derived from registry_files (no duplication).
    """
    from forge.config import ForgeConfig

    website_dir = tmp_path / "website"
    data_dir = website_dir / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "marketplace.json").symlink_to(registry_files["website_marketplace"])
    (data_dir / "plugin-meta.json").symlink_to(registry_files["website_meta"])

    return ForgeConfig(
        skill7_workspace=tmp_path,
        emporium_path=tmp_path / "emporium-repo",
        website_path=website_dir,
        github_org="heurema",
        default_type="marketplace",
        default_category="devtools",
        readme_template=None,
    )


def make_valid_snapshot(base_dir: Path) -> Path:
    """Create a valid rubric_snapshot directory for testing."""
    snap_dir = base_dir / "rubric_snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)
    code = "# vendored rubric\ndef check_readme(path): return (True, 'ok')\n"
    (snap_dir / "__init__.py").write_text(code)
    content_hash = "sha256:" + hashlib.sha256(code.encode()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "content_hash": content_hash,
        "source_commit": "abc123",
        "vendored_at": "2026-03-11T00:00:00Z",
    }
    (snap_dir / "manifest.json").write_text(json.dumps(manifest))
    return snap_dir
