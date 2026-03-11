# src/forge/promote.py
"""Generate a markdown promotion checklist for a plugin release."""
from __future__ import annotations

import json
from pathlib import Path


_AWESOME_LISTS = [
    (
        "anthropics/claude-plugins-official",
        "https://github.com/anthropics/claude-plugins-official/issues/new?template=plugin-submission.md",
        "Submit via issue form",
    ),
    (
        "hesreallyhim/awesome-claude-code",
        "https://github.com/hesreallyhim/awesome-claude-code/issues/new",
        "Submit via PR or issue",
    ),
    (
        "ComposioHQ/awesome-claude-plugins",
        "https://github.com/ComposioHQ/awesome-claude-plugins",
        "Submit via PR",
    ),
    (
        "ccplugins/awesome-claude-code-plugins",
        "https://github.com/ccplugins/awesome-claude-code-plugins",
        "Submit via PR",
    ),
    (
        "davila7/claude-code-templates",
        "https://github.com/davila7/claude-code-templates",
        "Submit via PR",
    ),
]


def generate_checklist(plugin_dir: Path) -> str:
    """Generate a markdown promotion checklist for the plugin at *plugin_dir*.

    Reads plugin.json from ``plugin_dir/.claude-plugin/plugin.json`` and
    produces a checklist covering pre-flight, awesome-list submissions, blog
    post, social, and GitHub topics.
    """
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest: dict = json.loads(manifest_path.read_text())

    name: str = manifest.get("name", plugin_dir.name)
    description: str = manifest.get("description", "")
    keywords: list[str] = manifest.get("keywords", [])
    version: str = manifest.get("version", "")

    lines: list[str] = []

    # ---------------------------------------------------------------------------
    # Pre-flight
    # ---------------------------------------------------------------------------
    lines += [
        f"# Promotion checklist — {name} {version}",
        "",
        "## Pre-flight",
        "",
        "- [ ] Version synced across plugin.json, CHANGELOG.md, and any pyproject.toml/package.json",
        "- [ ] `forge audit` passed with no errors",
        "- [ ] README has install instructions (emporium + manual)",
        "- [ ] CHANGELOG entry for this version is present",
        "- [ ] GitHub release tag created",
        "",
    ]

    # ---------------------------------------------------------------------------
    # Awesome lists
    # ---------------------------------------------------------------------------
    lines += [
        "## Awesome lists",
        "",
    ]
    for repo, url, method in _AWESOME_LISTS:
        lines.append(f"- [ ] [{repo}]({url}) — {method}")
    lines.append("")

    # ---------------------------------------------------------------------------
    # Blog post
    # ---------------------------------------------------------------------------
    feature_bullets = "\n".join(
        f"  - {kw}" for kw in keywords
    ) if keywords else "  - (add key features here)"

    lines += [
        "## Blog post",
        "",
        f"Plugin name: **{name}**",
        f"Description: {description}",
        "",
        "Draft outline:",
        f"- What is {name}?",
        "- Problem it solves",
        "- Key features:",
        feature_bullets,
        "- Install instructions",
        "- Demo / screenshot",
        "",
        "- [ ] Draft written",
        "- [ ] Published to ctxt.dev",
        "- [ ] Cross-posted to dev.to",
        "- [ ] Cross-posted to Hashnode",
        "",
    ]

    # ---------------------------------------------------------------------------
    # Social
    # ---------------------------------------------------------------------------
    lines += [
        "## Social",
        "",
        "### Twitter / X thread",
        "",
        f"1/ Just shipped {name} — {description}",
        "",
        f"2/ Install with emporium: `emporium install {name}`",
        "",
        "3/ (screenshot or demo GIF here)",
        "",
        "4/ Open-source, contributions welcome. Link in bio.",
        "",
        "- [ ] Twitter / X thread posted",
        "",
        "### LinkedIn",
        "",
        f"Excited to announce {name}! {description}",
        "",
        f"Install: `emporium install {name}`",
        "",
        "- [ ] LinkedIn post published",
        "",
    ]

    # ---------------------------------------------------------------------------
    # GitHub
    # ---------------------------------------------------------------------------
    topic_suggestions = ["claude-code", "claude-code-plugin"] + [
        kw.lower().replace(" ", "-") for kw in keywords
    ]
    topics_str = ", ".join(f"`{t}`" for t in topic_suggestions)

    lines += [
        "## GitHub",
        "",
        f"- [ ] Repository topics set: {topics_str}",
        "- [ ] Repository description matches plugin.json description",
        "- [ ] Social preview image uploaded",
        "",
    ]

    return "\n".join(lines)
