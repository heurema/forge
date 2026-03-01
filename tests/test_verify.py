"""Tests for forge verify module."""

import json
from pathlib import Path

from forge.verify import verify_plugin


def _make_plugin(tmp_path: Path, *, plugin_type: str = "marketplace") -> Path:
    """Helper: create a minimal valid plugin directory."""
    plugin_dir = tmp_path / "test-plugin"
    plugin_dir.mkdir()
    (plugin_dir / ".claude-plugin").mkdir()
    manifest = {
        "name": "test-plugin",
        "version": "0.1.0",
        "description": "A test plugin",
        "type": plugin_type,
    }
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
    (plugin_dir / ".gitignore").write_text("__pycache__/\n")
    (plugin_dir / "README.md").write_text(
        "# test-plugin\n\n"
        "<!-- INSTALL:START -->\n```bash\n"
        "claude plugin install test-plugin@emporium\n"
        "```\n<!-- INSTALL:END -->\n"
    )
    (plugin_dir / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial\n")
    return plugin_dir


class TestVerify:
    def test_valid_plugin_passes(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        result = verify_plugin(plugin_dir)
        assert result.passed
        assert len(result.errors) == 0

    def test_missing_gitignore_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / ".gitignore").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any(".gitignore" in e for e in result.errors)

    def test_missing_readme_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "README.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("README" in e for e in result.errors)

    def test_marketplace_missing_install_markers(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "README.md").write_text("# test-plugin\n\nNo install markers.\n")
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("INSTALL" in e for e in result.errors)

    def test_local_no_install_markers_ok(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path, plugin_type="local")
        (plugin_dir / "README.md").write_text("# test-plugin\n\nLocal only.\n")
        result = verify_plugin(plugin_dir)
        assert result.passed

    def test_version_mismatch_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "CHANGELOG.md").write_text("# Changelog\n\n## 0.2.0\n\n- Wrong\n")
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("version" in e.lower() for e in result.errors)

    def test_invalid_semver_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text())
        manifest["version"] = "1.0"
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("semver" in e.lower() for e in result.errors)

    def test_name_dirname_mismatch_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text())
        manifest["name"] = "wrong-name"
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("name" in e.lower() and "match" in e.lower() for e in result.errors)

    def test_readme_todo_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "README.md").write_text(
            "# test-plugin\n\n> TODO: Add description\n\n"
            "<!-- INSTALL:START -->\n```bash\n"
            "claude plugin install test-plugin@emporium\n"
            "```\n<!-- INSTALL:END -->\n"
        )
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("TODO" in e for e in result.errors)

    def test_collects_all_errors(self, tmp_path: Path) -> None:
        """Verify collects ALL errors, not just the first one."""
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / ".gitignore").unlink()
        (plugin_dir / "README.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert len(result.errors) >= 2
