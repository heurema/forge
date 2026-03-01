"""Tests for forge status module."""

import json
from pathlib import Path

from forge.status import StatusCheck, check_plugin_status


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
    (plugin_dir / "README.md").write_text("# test-plugin\n")
    (plugin_dir / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial\n")
    return plugin_dir


def _make_registry(tmp_path: Path, entries: list[str]) -> Path:
    """Helper: create a fake registry.json."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = {"devtools": [{"name": n, "version": "0.1.0"} for n in entries]}
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry))
    return tmp_path


def _make_marketplace(tmp_path: Path, entries: list[str]) -> Path:
    """Helper: create a fake marketplace.json (emporium dict format)."""
    mp = tmp_path / ".claude-plugin"
    mp.mkdir(parents=True, exist_ok=True)
    plugins = [{"name": n, "description": "", "category": "development"} for n in entries]
    data = {"name": "emporium", "plugins": plugins}
    (mp / "marketplace.json").write_text(json.dumps(data))
    return tmp_path


class TestStatus:
    def test_returns_list_of_checks(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        checks = check_plugin_status(plugin_dir)
        assert isinstance(checks, list)
        assert all(isinstance(c, StatusCheck) for c in checks)

    def test_gitignore_present(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        checks = check_plugin_status(plugin_dir)
        gi = next(c for c in checks if ".gitignore" in c.name)
        assert gi.passed

    def test_gitignore_missing(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / ".gitignore").unlink()
        checks = check_plugin_status(plugin_dir)
        gi = next(c for c in checks if ".gitignore" in c.name)
        assert not gi.passed

    def test_registry_check_found(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        ws = _make_registry(tmp_path / "ws", ["test-plugin"])
        checks = check_plugin_status(plugin_dir, skill7_workspace=ws)
        reg = next(c for c in checks if "registry" in c.name.lower())
        assert reg.passed

    def test_registry_check_missing(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        ws = _make_registry(tmp_path / "ws", ["other-plugin"])
        checks = check_plugin_status(plugin_dir, skill7_workspace=ws)
        reg = next(c for c in checks if "registry" in c.name.lower())
        assert not reg.passed

    def test_marketplace_check_for_marketplace_type(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path, plugin_type="marketplace")
        emp = _make_marketplace(tmp_path / "emp", ["test-plugin"])
        checks = check_plugin_status(plugin_dir, emporium_path=emp)
        mp = next(c for c in checks if "emporium" in c.name.lower())
        assert mp.passed

    def test_no_marketplace_check_for_local(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path, plugin_type="local")
        checks = check_plugin_status(plugin_dir)
        mp_checks = [c for c in checks if "emporium" in c.name.lower()]
        assert len(mp_checks) == 0
