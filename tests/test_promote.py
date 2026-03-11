# tests/test_promote.py
from pathlib import Path

from forge.promote import generate_checklist


class TestGenerateChecklist:
    def test_contains_all_sections(self, sample_plugin: Path) -> None:
        checklist = generate_checklist(sample_plugin)
        assert "Pre-flight" in checklist
        assert "Awesome lists" in checklist or "awesome" in checklist.lower()
        assert "Blog post" in checklist or "blog" in checklist.lower()
        assert "Social" in checklist or "Twitter" in checklist
        assert "GitHub" in checklist

    def test_contains_plugin_name(self, sample_plugin: Path) -> None:
        checklist = generate_checklist(sample_plugin)
        assert "sample-plugin" in checklist

    def test_contains_awesome_list_urls(self, sample_plugin: Path) -> None:
        checklist = generate_checklist(sample_plugin)
        assert "claude-plugins-official" in checklist
        assert "awesome-claude-code" in checklist
