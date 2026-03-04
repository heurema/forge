"""Tests for forge readme module."""

from pathlib import Path

from forge.readme import (
    generate_readme,
    parse_readme_sections,
    smart_merge,
)


class TestParseReadmeSections:
    def test_empty_content(self) -> None:
        sections = parse_readme_sections("")
        # Empty string produces empty hero
        assert "__hero__" not in sections or sections["__hero__"].strip() == ""

    def test_hero_only(self) -> None:
        content = "# My Plugin\n\n> Description\n"
        sections = parse_readme_sections(content)
        assert "__hero__" in sections
        assert "# My Plugin" in sections["__hero__"]

    def test_sections_parsed(self) -> None:
        content = "# Hero\n\n## Install\n\nDo this.\n\n## Privacy\n\nNo data sent.\n"
        sections = parse_readme_sections(content)
        assert "__hero__" in sections
        assert "install" in sections
        assert "privacy" in sections
        assert "Do this." in sections["install"]
        assert "No data sent." in sections["privacy"]

    def test_no_hero(self) -> None:
        content = "## Install\n\nContent here.\n"
        sections = parse_readme_sections(content)
        assert "__hero__" not in sections
        assert "install" in sections

    def test_case_insensitive_keys(self) -> None:
        content = "## Quick Start\n\nContent.\n"
        sections = parse_readme_sections(content)
        assert "quick start" in sections


class TestSmartMerge:
    def test_preserves_existing_content(self) -> None:
        existing = (
            "# my-plugin\n\n"
            "## Install\n\nReal install instructions here.\n\n"
            "## Privacy\n\nNo data leaves your machine.\n"
        )
        rendered = (
            "# my-plugin\n\n"
            "## Install\n\n{placeholder}\n\n"
            "## Privacy\n\n{placeholder}\n\n"
            "## License\n\n[MIT](LICENSE)\n"
        )
        result = smart_merge(existing, rendered, {})
        assert "Real install instructions here." in result
        assert "No data leaves your machine." in result

    def test_adds_missing_sections(self) -> None:
        existing = "# my-plugin\n\n## Install\n\nContent.\n"
        rendered = (
            "# my-plugin\n\n"
            "## Install\n\nContent.\n\n"
            "## Privacy\n\nNo data sent.\n\n"
            "## License\n\n[MIT](LICENSE)\n"
        )
        result = smart_merge(existing, rendered, {})
        assert "## Privacy" in result
        assert "## License" in result

    def test_replaces_placeholder_content(self) -> None:
        existing = "# my-plugin\n\n## Install\n\nAdd usage instructions here.\n"
        rendered = "# my-plugin\n\n## Install\n\nNew content from template.\n"
        result = smart_merge(existing, rendered, {})
        assert "New content from template." in result
        assert "Add usage instructions here." not in result

    def test_overwrites_license(self) -> None:
        existing = "# my-plugin\n\n## License\n\nOld license text.\n"
        rendered = "# my-plugin\n\n## License\n\n[MIT](LICENSE)\n"
        result = smart_merge(existing, rendered, {})
        assert "[MIT](LICENSE)" in result

    def test_warns_on_extra_sections(self) -> None:
        existing = "# my-plugin\n\n## Custom section\n\nMy content.\n"
        rendered = "# my-plugin\n\n## Install\n\nContent.\n"
        result = smart_merge(existing, rendered, {})
        assert "consider removing" in result
        assert "My content." in result

    def test_uses_template_hero(self) -> None:
        existing = "# old-hero\n\nOld tagline.\n\n## Install\n\nContent.\n"
        rendered = "# new-hero\n\nNew tagline.\n\n## Install\n\nContent.\n"
        result = smart_merge(existing, rendered, {})
        assert "# new-hero" in result
        assert "# old-hero" not in result

    def test_reorders_sections_to_template_order(self) -> None:
        existing = (
            "# my-plugin\n\n"
            "## License\n\n[MIT](LICENSE)\n\n"
            "## Install\n\nContent.\n\n"
            "## Privacy\n\nNo data.\n"
        )
        rendered = (
            "# my-plugin\n\n"
            "## Install\n\nContent.\n\n"
            "## Privacy\n\nNo data.\n\n"
            "## License\n\n[MIT](LICENSE)\n"
        )
        result = smart_merge(existing, rendered, {})
        install_pos = result.index("## Install")
        privacy_pos = result.index("## Privacy")
        license_pos = result.index("## License")
        assert install_pos < privacy_pos < license_pos

    def test_merges_install_markers(self) -> None:
        existing = (
            "# my-plugin\n\n"
            "## Install\n\n"
            "<!-- INSTALL:START -->\n"
            "```bash\nold command\n```\n"
            "<!-- INSTALL:END -->\n\n"
            "Extra install notes.\n"
        )
        rendered = (
            "# my-plugin\n\n"
            "## Install\n\n"
            "<!-- INSTALL:START -->\n"
            "```bash\nnew command\n```\n"
            "<!-- INSTALL:END -->\n"
        )
        result = smart_merge(existing, rendered, {})
        assert "new command" in result
        assert "old command" not in result
        assert "Extra install notes." in result


class TestGenerateReadme:
    def test_generates_from_template(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / ".claude-plugin").mkdir()
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "test-plugin", "version": "0.1.0", "description": "A test"}'
        )

        template = tmp_path / "templates" / "README.md.j2"
        template.parent.mkdir()
        template.write_text("# {{ name }}\n\n> {{ description }}\n\n## Install\n\nContent.\n")

        content, changes = generate_readme(plugin_dir, template)
        assert "# test-plugin" in content
        assert "generated from template" in changes

    def test_merge_mode(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / ".claude-plugin").mkdir()
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "test-plugin", "version": "0.1.0", "description": "A test"}'
        )
        (plugin_dir / "README.md").write_text(
            "# test-plugin\n\n## Install\n\nExisting instructions.\n"
        )

        template = tmp_path / "templates" / "README.md.j2"
        template.parent.mkdir()
        template.write_text(
            "# {{ name }}\n\n> {{ description }}\n\n"
            "## Install\n\n{placeholder}\n\n"
            "## Privacy\n\nNo data.\n"
        )

        content, changes = generate_readme(plugin_dir, template)
        assert "Existing instructions." in content
        assert "## Privacy" in content

    def test_no_merge_when_disabled(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "test-plugin"
        plugin_dir.mkdir()
        (plugin_dir / ".claude-plugin").mkdir()
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "test-plugin", "version": "0.1.0", "description": "A test"}'
        )
        (plugin_dir / "README.md").write_text("# old content\n")

        template = tmp_path / "templates" / "README.md.j2"
        template.parent.mkdir()
        template.write_text("# {{ name }}\n\n> {{ description }}\n")

        content, changes = generate_readme(plugin_dir, template, merge=False)
        assert "# test-plugin" in content
        assert "generated from template" in changes
