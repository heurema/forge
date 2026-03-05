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
    (plugin_dir / "LICENSE").write_text("MIT License\n")

    # docs/
    (plugin_dir / "docs").mkdir()
    (plugin_dir / "docs" / "how-it-works.md").write_text("# How it works\n")
    (plugin_dir / "docs" / "reference.md").write_text("# Reference\n")

    if plugin_type == "marketplace":
        readme = (
            "# test-plugin\n\n"
            "[![v](https://img.shields.io/badge/v-0.1.0-blue)]()\n\n"
            "## What it does\n\nA test plugin.\n\n"
            "## Install\n\n"
            "<!-- INSTALL:START -->\n```bash\n"
            "claude plugin install test-plugin@emporium\n"
            "```\n<!-- INSTALL:END -->\n\n"
            "## Quick start\n\nRun the command.\n\n"
            "## Commands\n\n| Command | What it does |\n|---------|-------------|\n"
            "| `/test` | Does test |\n\n"
            "## Privacy\n\nNo data sent.\n\n"
            "## See also\n\n- [skill7.dev](https://skill7.dev)\n\n"
            "## License\n\n[MIT](LICENSE)\n"
        )
    else:
        readme = (
            "# test-plugin\n\n"
            "## Install\n\nClone the repo.\n\n"
            "## Privacy\n\nNo data sent.\n"
        )
    (plugin_dir / "README.md").write_text(readme)
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
        (plugin_dir / "README.md").write_text(
            "# test-plugin\n\n"
            "[![v](https://img.shields.io/badge/v-0.1.0-blue)]()\n\n"
            "## Install\n\nNo install markers.\n\n"
            "## Quick start\n\nRun it.\n\n"
            "## Commands\n\n| Cmd | Does |\n|-----|------|\n| /x | y |\n\n"
            "## Privacy\n\nNone.\n\n"
            "## See also\n\nLinks.\n\n"
            "## License\n\n[MIT](LICENSE)\n"
        )
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("INSTALL" in e for e in result.errors)

    def test_local_no_install_markers_ok(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path, plugin_type="local")
        # Local plugins don't need INSTALL markers but still need required sections
        result = verify_plugin(plugin_dir)
        assert result.passed
        assert not any("INSTALL" in e for e in result.errors)

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
        readme = (plugin_dir / "README.md").read_text()
        # Inject a TODO into the existing valid README
        (plugin_dir / "README.md").write_text(
            readme.replace("A test plugin.", "TODO: Add description.")
        )
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("TODO" in e for e in result.errors)

    def test_readme_style_errors_reported(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path, plugin_type="local")
        (plugin_dir / "README.md").write_text(
            "# test-plugin\n\n"
            "## Installation\n\nContent.\n\n"
            "## privacy\n\nNo data.\n"
        )
        result = verify_plugin(plugin_dir)
        assert not result.passed
        # Missing "Install" section (has "Installation" instead) and wrong "privacy" casing
        assert any("Privacy" in e for e in result.errors)

    def test_collects_all_errors(self, tmp_path: Path) -> None:
        """Verify collects ALL errors, not just the first one."""
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / ".gitignore").unlink()
        (plugin_dir / "README.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert len(result.errors) >= 2

    def test_missing_license_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "LICENSE").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("LICENSE" in e for e in result.errors)

    def test_missing_changelog_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "CHANGELOG.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("CHANGELOG" in e for e in result.errors)

    def test_missing_docs_how_it_works_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "docs" / "how-it-works.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("how-it-works" in e for e in result.errors)

    def test_missing_docs_reference_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "docs" / "reference.md").unlink()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("reference" in e for e in result.errors)

    def test_src_without_tests_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "src").mkdir()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("tests/" in e for e in result.errors)

    def test_src_with_tests_passes(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "src").mkdir()
        (plugin_dir / "tests").mkdir()
        result = verify_plugin(plugin_dir)
        assert result.passed

    def test_non_kebab_dir_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "MyModule").mkdir()
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("kebab-case" in e for e in result.errors)

    def test_kebab_dirs_pass(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        (plugin_dir / "my-module").mkdir()
        result = verify_plugin(plugin_dir)
        assert result.passed

    def test_skill_md_lowercase_fails(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        skills = plugin_dir / "skills" / "my-skill"
        skills.mkdir(parents=True)
        (skills / "skill.md").write_text("# Skill\n")
        result = verify_plugin(plugin_dir)
        assert not result.passed
        assert any("SKILL.md" in e and "uppercase" in e for e in result.errors)

    def test_skill_md_uppercase_passes(self, tmp_path: Path) -> None:
        plugin_dir = _make_plugin(tmp_path)
        skills = plugin_dir / "skills" / "my-skill"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_text("# Skill\n")
        result = verify_plugin(plugin_dir)
        assert result.passed
