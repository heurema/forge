"""Read and validate forge.local.md config."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """Raised when config is invalid or missing."""


VALID_TYPES = {"marketplace", "project", "local"}
VALID_CATEGORIES = {"devtools", "trading", "creative", "publishing", "research"}
REQUIRED_FIELDS = ("skill7_workspace", "emporium_path", "website_path", "github_org")
DEFAULTS: dict[str, str] = {"default_type": "marketplace", "default_category": "devtools"}


@dataclass(frozen=True)
class ForgeConfig:
    skill7_workspace: Path
    emporium_path: Path
    website_path: Path
    github_org: str
    default_type: str
    default_category: str
    readme_template: Path | None

    def require_path(self, field: str) -> Path:
        """Return the path for field if it exists on disk, else raise ConfigError."""
        path: Path = getattr(self, field)
        if not path.exists():
            raise ConfigError(f"{field} path does not exist: {path}")
        return path


def _parse_yaml_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML frontmatter from markdown. Minimal parser — no PyYAML dependency."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            result[key.strip()] = value.strip().strip("\"'")
    return result


def load_config(config_path: Path) -> ForgeConfig:
    """Load and validate forge config from a .local.md file."""
    if not config_path.exists():
        raise ConfigError(f"Config not found: {config_path}")

    raw = _parse_yaml_frontmatter(config_path.read_text())

    for field in REQUIRED_FIELDS:
        if field not in raw:
            raise ConfigError(f"Missing required field: {field}")

    for key, default in DEFAULTS.items():
        raw.setdefault(key, default)

    if raw["default_type"] not in VALID_TYPES:
        raise ConfigError(
            f"Invalid default_type: '{raw['default_type']}'. Must be one of {VALID_TYPES}"
        )
    if raw["default_category"] not in VALID_CATEGORIES:
        raise ConfigError(
            f"Invalid default_category: '{raw['default_category']}'."
            f" Must be one of {VALID_CATEGORIES}"
        )

    readme_template: Path | None = None
    if "readme_template" in raw:
        readme_template = Path(raw["readme_template"]).expanduser()

    return ForgeConfig(
        skill7_workspace=Path(raw["skill7_workspace"]).expanduser(),
        emporium_path=Path(raw["emporium_path"]).expanduser(),
        website_path=Path(raw["website_path"]).expanduser(),
        github_org=raw["github_org"],
        default_type=raw["default_type"],
        default_category=raw["default_category"],
        readme_template=readme_template,
    )


def derive_category(plugin_dir: Path) -> str:
    """Derive plugin category from its parent directory name."""
    category = plugin_dir.parent.name
    if category not in VALID_CATEGORIES:
        raise ConfigError(
            f"Invalid category '{category}' derived from {plugin_dir}. "
            f"Valid: {sorted(VALID_CATEGORIES)}"
        )
    return category
