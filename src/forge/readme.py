"""README generation and smart merge for plugins."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jinja2

# Sections whose content is always overwritten from template
ALWAYS_OVERWRITE = {"license"}

# Marker patterns for the INSTALL block
INSTALL_START_RE = re.compile(r"<!-- INSTALL:START.*?-->")
INSTALL_END_RE = re.compile(r"<!-- INSTALL:END\s*-->")

# Hero block: everything inside <div align="center"> ... </div>
HERO_RE = re.compile(
    r"(<div\s+align=[\"']center[\"']>.*?</div>)",
    re.DOTALL | re.IGNORECASE,
)

SECTION_HEADER_RE = re.compile(r"^## (.+)$", re.MULTILINE)

# Content that indicates a placeholder (needs user editing)
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[A-Za-z][A-Za-z_ -]*\}"),  # {placeholder}
    re.compile(r"Add .+ here\.?$", re.MULTILINE),  # "Add usage instructions here."
]


def _normalize_section_key(name: str) -> str:
    """Normalize section name to a stable key for matching."""
    return name.strip().lower()


def parse_readme_sections(content: str) -> dict[str, str]:
    """Parse markdown into {section_key: content} by splitting on ## headers.

    Returns a dict where keys are lowercase section names.
    The special key "__hero__" holds everything before the first ## header.
    """
    sections: dict[str, str] = {}
    matches = list(SECTION_HEADER_RE.finditer(content))

    if not matches:
        if content.strip():
            sections["__hero__"] = content
        return sections

    # Hero: everything before first ##
    hero = content[: matches[0].start()].rstrip("\n")
    if hero.strip():
        sections["__hero__"] = hero

    for i, m in enumerate(matches):
        name = _normalize_section_key(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections[name] = content[start:end].strip("\n")

    return sections


def _is_placeholder_content(text: str) -> bool:
    """Check if section content is just a placeholder from the template."""
    stripped = text.strip()
    if not stripped:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        # If the entire meaningful content is just placeholders
        cleaned = pattern.sub("", stripped)
        if not cleaned.strip() or cleaned.strip() in ("-", "|", "||"):
            return True
    return False


def render_readme_template(template_path: Path, context: dict[str, str]) -> str:
    """Render a Jinja2 README template with plugin metadata."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_path.parent)),
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )
    template = env.get_template(template_path.name)
    return template.render(context)


def _extract_install_block(content: str) -> str | None:
    """Extract the full INSTALL marker block from content."""
    start = INSTALL_START_RE.search(content)
    end = INSTALL_END_RE.search(content)
    if start and end and end.end() > start.start():
        return content[start.start() : end.end()]
    return None


def smart_merge(existing: str, rendered: str, manifest: dict[str, object]) -> str:
    """Merge existing README with rendered template, preserving user content.

    Rules:
    - Always overwrite: hero div, INSTALL markers block, license section
    - Keep existing content: if section has real (non-placeholder) content
    - Add missing: sections from template that don't exist in current README
    - Reorder: sections to match template order
    """
    old_sections = parse_readme_sections(existing)
    new_sections = parse_readme_sections(rendered)

    # Determine template section order (excluding hero)
    template_order = [
        _normalize_section_key(m.group(1))
        for m in SECTION_HEADER_RE.finditer(rendered)
    ]

    result_parts: list[str] = []

    # 1. Hero: always use template version
    if "__hero__" in new_sections:
        result_parts.append(new_sections["__hero__"])
    elif "__hero__" in old_sections:
        result_parts.append(old_sections["__hero__"])

    # 2. Process sections in template order
    for section_key in template_order:
        new_content = new_sections.get(section_key, "")

        if section_key in ALWAYS_OVERWRITE:
            # Always use template version
            header = _title_case_section(section_key, rendered)
            result_parts.append(f"\n\n## {header}\n\n{new_content}")
            continue

        if section_key in old_sections:
            old_content = old_sections[section_key]
            if _is_placeholder_content(old_content):
                # Old content is just a placeholder — use template
                result_parts.append(
                    f"\n\n## {_title_case_section(section_key, rendered)}\n\n{new_content}"
                )
            else:
                # Preserve real user content, but update INSTALL markers if present
                merged_content = old_content
                if section_key == "install":
                    merged_content = _merge_install_block(old_content, new_content)
                result_parts.append(
                    f"\n\n## {_title_case_section(section_key, rendered)}\n\n{merged_content}"
                )
        else:
            # Section missing in old — add from template
            result_parts.append(
                f"\n\n## {_title_case_section(section_key, rendered)}\n\n{new_content}"
            )

    # 3. Append any old sections not in template (with warning comment)
    for section_key, content in old_sections.items():
        if section_key == "__hero__":
            continue
        if section_key not in template_order:
            header = _title_case_section(section_key, existing)
            result_parts.append(
                f"\n\n<!-- NOTE: section not in template, consider removing -->\n"
                f"## {header}\n\n{content}"
            )

    text = "\n".join(part.rstrip() for part in result_parts).strip() + "\n"
    # Clean up excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def _title_case_section(key: str, source_text: str) -> str:
    """Find the original casing of a section header in source text."""
    for m in SECTION_HEADER_RE.finditer(source_text):
        if _normalize_section_key(m.group(1)) == key:
            return m.group(1)
    # Fallback: capitalize first letter
    return key.capitalize()


def _merge_install_block(old_content: str, new_content: str) -> str:
    """Replace INSTALL markers block in old content with the one from new content."""
    new_block = _extract_install_block(new_content)
    if not new_block:
        return old_content

    old_block = _extract_install_block(old_content)
    if old_block:
        return old_content.replace(old_block, new_block)

    # No markers in old — prepend the install block
    return new_block + "\n\n" + old_content


def _load_manifest(plugin_dir: Path) -> dict[str, object]:
    """Load plugin.json manifest."""
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if not manifest_path.exists():
        return {}
    try:
        data: dict[str, object] = json.loads(manifest_path.read_text())
        return data
    except json.JSONDecodeError:
        return {}


def _build_template_context(manifest: dict[str, object]) -> dict[str, str]:
    """Build Jinja2 context from manifest."""
    tags = manifest.get("tags", [])
    category = tags[0] if isinstance(tags, list) and tags else "devtools"
    author = manifest.get("author", {})
    github_org = author.get("name", "heurema") if isinstance(author, dict) else "heurema"
    repo = manifest.get("repository", "")
    repo_str = str(repo) if repo else ""
    # Extract org from repository URL if available
    if "/" in repo_str and github_org == "heurema":
        parts = repo_str.rstrip("/").split("/")
        if len(parts) >= 2:
            github_org = parts[-2]

    return {
        "name": str(manifest.get("name", "")),
        "description": str(manifest.get("description", "")),
        "version": str(manifest.get("version", "0.1.0")),
        "type": str(manifest.get("type", "marketplace")),
        "category": str(category),
        "github_org": github_org,
    }


def generate_readme(
    plugin_dir: Path,
    template_path: Path,
    *,
    merge: bool = True,
) -> tuple[str, list[str]]:
    """Generate or update README for a plugin.

    Returns (new_readme_content, list_of_changes).
    """
    manifest = _load_manifest(plugin_dir)
    context = _build_template_context(manifest)
    rendered = render_readme_template(template_path, context)

    readme_path = plugin_dir / "README.md"
    changes: list[str] = []

    if readme_path.exists() and merge:
        existing = readme_path.read_text()
        result = smart_merge(existing, rendered, manifest)
        if result.strip() != existing.strip():
            # Compute what changed
            old_sections = set(parse_readme_sections(existing).keys())
            new_sections = set(parse_readme_sections(result).keys())
            added = new_sections - old_sections
            if added:
                changes.append(f"added sections: {', '.join(sorted(added))}")
            changes.append("merged with template")
        else:
            changes.append("no changes needed")
        return result, changes

    changes.append("generated from template")
    return rendered, changes
