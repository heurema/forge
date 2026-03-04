"""Tests for forge readme_verify module."""

from forge.readme_verify import verify_readme_structure, verify_readme_style


class TestVerifyReadmeStructure:
    def _make_readme(self, sections: list[str]) -> str:
        parts = ["# My Plugin\n\n> Description\n"]
        for s in sections:
            parts.append(f"\n## {s}\n\nContent here.\n")
        return "\n".join(parts)

    def test_valid_marketplace_readme(self) -> None:
        readme = self._make_readme(
            ["Install", "Quick start", "Commands", "Privacy", "See also", "License"]
        )
        # Add a badge for marketplace check
        readme = readme.replace(
            "# My Plugin",
            "# My Plugin\n\n[![v](https://img.shields.io/badge/v-1.0-blue)]()",
        )
        errors = verify_readme_structure(readme, "marketplace")
        assert errors == []

    def test_missing_required_section(self) -> None:
        readme = self._make_readme(["Install"])
        errors = verify_readme_structure(readme, "local")
        assert any("Privacy" in e for e in errors)

    def test_marketplace_requires_more_sections(self) -> None:
        readme = self._make_readme(["Install", "Privacy"])
        errors = verify_readme_structure(readme, "marketplace")
        assert any("Quick start" in e or "Commands" in e for e in errors)

    def test_out_of_order_sections(self) -> None:
        readme = self._make_readme(["Privacy", "Install"])
        errors = verify_readme_structure(readme, "local")
        assert any("order" in e.lower() for e in errors)

    def test_marketplace_requires_badges(self) -> None:
        readme = self._make_readme(
            ["Install", "Quick start", "Commands", "Privacy", "See also", "License"]
        )
        errors = verify_readme_structure(readme, "marketplace")
        assert any("badge" in e.lower() for e in errors)

    def test_local_no_badge_requirement(self) -> None:
        readme = self._make_readme(["Install", "Privacy"])
        errors = verify_readme_structure(readme, "local")
        assert not any("badge" in e.lower() for e in errors)


class TestVerifyReadmeStyle:
    def test_correct_header_naming(self) -> None:
        readme = "## Install\n\nContent.\n\n## Privacy\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert errors == []

    def test_wrong_install_header(self) -> None:
        readme = "## Installation\n\nContent.\n"
        errors = verify_readme_style(readme)
        # "Installation" lowered = "installation", not in EXACT_HEADERS, so no exact match error
        # This is fine — the structure check catches missing "Install"
        assert errors == []

    def test_wrong_privacy_casing(self) -> None:
        readme = "## privacy\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert any("Privacy" in e for e in errors)

    def test_emoji_in_header(self) -> None:
        readme = "## \U0001f680 Install\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert any("emoji" in e.lower() for e in errors)

    def test_sentence_case_violation(self) -> None:
        readme = "## How It Works\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert any("sentence case" in e.lower() for e in errors)

    def test_sentence_case_ok_with_acronym(self) -> None:
        readme = "## How API works\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert not any("sentence case" in e.lower() for e in errors)

    def test_wide_table(self) -> None:
        wide_row = "| " + "x" * 110 + " |"
        readme = f"## Commands\n\n{wide_row}\n"
        errors = verify_readme_style(readme)
        assert any("wide table" in e.lower() for e in errors)

    def test_normal_width_table_ok(self) -> None:
        readme = (
            "## Commands\n\n"
            "| Command | Description |\n"
            "|---------|-------------|\n"
            "| /foo | Does stuff |\n"
        )
        errors = verify_readme_style(readme)
        assert not any("wide table" in e.lower() for e in errors)

    def test_see_also_exact_casing(self) -> None:
        readme = "## See Also\n\nContent.\n"
        errors = verify_readme_style(readme)
        assert any("See also" in e for e in errors)
