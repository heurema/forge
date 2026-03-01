"""Tests for Jinja2 templates."""

from pathlib import Path

import jinja2
import pytest

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@pytest.fixture
def env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )


@pytest.fixture
def context() -> dict[str, str]:
    return {
        "name": "test-plugin",
        "type": "marketplace",
        "category": "devtools",
        "version": "0.1.0",
        "description": "A test plugin",
        "github_org": "heurema",
    }


class TestTemplates:
    def test_plugin_json_valid(self, env: jinja2.Environment, context: dict[str, str]) -> None:
        import json
        rendered = env.get_template("plugin.json.j2").render(context)
        data = json.loads(rendered)
        assert data["name"] == "test-plugin"
        assert data["version"] == "0.1.0"
        assert data["status"] == "alpha"

    def test_readme_marketplace_has_install_markers(
        self, env: jinja2.Environment, context: dict[str, str]
    ) -> None:
        rendered = env.get_template("README.md.j2").render(context)
        assert "<!-- INSTALL:START" in rendered
        assert "<!-- INSTALL:END -->" in rendered
        assert "test-plugin@emporium" in rendered

    def test_readme_local_no_install_markers(
        self, env: jinja2.Environment, context: dict[str, str]
    ) -> None:
        context["type"] = "local"
        rendered = env.get_template("README.md.j2").render(context)
        assert "<!-- INSTALL:START" not in rendered

    def test_gitignore_has_pycache(self, env: jinja2.Environment, context: dict[str, str]) -> None:
        rendered = env.get_template("gitignore.j2").render(context)
        assert "__pycache__" in rendered

    def test_changelog_has_version(
        self, env: jinja2.Environment, context: dict[str, str]
    ) -> None:
        rendered = env.get_template("CHANGELOG.md.j2").render(context)
        assert "0.1.0" in rendered
