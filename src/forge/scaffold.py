"""Scaffold a new plugin from templates."""

from __future__ import annotations

import re
from pathlib import Path

import jinja2


class ScaffoldError(Exception):
    """Raised when scaffold fails."""


NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def validate_plugin_name(name: str) -> None:
    """Validate plugin name against GitHub naming rules."""
    if not name:
        raise ScaffoldError("Plugin name cannot be empty")
    if ".." in name or "/" in name or "\\" in name:
        raise ScaffoldError(f"Invalid plugin name: '{name}' (path traversal)")
    if name != name.lower():
        raise ScaffoldError(f"Plugin name must be lowercase: '{name}'")
    if not NAME_RE.match(name):
        raise ScaffoldError(f"Invalid plugin name: '{name}' (use lowercase letters, numbers, hyphens)")


def scaffold_plugin(
    *,
    target_dir: Path,
    name: str,
    plugin_type: str,
    category: str,
    description: str,
    github_org: str,
    templates_dir: Path,
) -> None:
    """Create plugin directory with all scaffold files."""
    validate_plugin_name(name)

    if target_dir.exists():
        raise ScaffoldError(f"Directory already exists: {target_dir}")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )

    context = {
        "name": name,
        "type": plugin_type,
        "category": category,
        "version": "0.1.0",
        "description": description,
        "github_org": github_org,
    }

    # Render all templates first (before creating any files)
    file_map = {
        "plugin.json.j2": ".claude-plugin/plugin.json",
        "README.md.j2": "README.md",
        "gitignore.j2": ".gitignore",
        "CHANGELOG.md.j2": "CHANGELOG.md",
        "LICENSE.j2": "LICENSE",
    }

    try:
        rendered_files: dict[str, str] = {}
        for template_name, output_path in file_map.items():
            rendered_files[output_path] = env.get_template(template_name).render(context)
    except jinja2.TemplateError as e:
        raise ScaffoldError(f"Template error: {e}") from e

    # Only create directories after all templates render successfully
    target_dir.mkdir(parents=True)
    (target_dir / ".claude-plugin").mkdir()
    (target_dir / "skills").mkdir()
    (target_dir / "commands").mkdir()

    # Write pre-rendered files
    for output_path, content in rendered_files.items():
        (target_dir / output_path).write_text(content)
