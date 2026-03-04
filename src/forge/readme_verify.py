"""README structure and style validation rules."""

from __future__ import annotations

import re

SECTION_HEADER_RE = re.compile(r"^## (.+)$", re.MULTILINE)

# Minimum required sections for any plugin
REQUIRED_SECTIONS = ["install", "privacy"]

# Full set for marketplace plugins
MARKETPLACE_SECTIONS = [
    "install",
    "quick start",
    "commands",
    "privacy",
    "see also",
    "license",
]

# Expected section order (for ordering check)
SECTION_ORDER = [
    "what it does",
    "install",
    "quick start",
    "commands",
    "features",
    "configuration",
    "privacy",
    "see also",
    "license",
]

# Headers that must be named exactly as specified
EXACT_HEADERS = {
    "privacy": "Privacy",
    "install": "Install",
    "commands": "Commands",
    "license": "License",
    "see also": "See also",
    "quick start": "Quick start",
}

EMOJI_RE = re.compile(
    r"[\U0001f300-\U0001f9ff\U0001fa00-\U0001fa6f\U0001fa70-\U0001faff"
    r"\u2600-\u26ff\u2700-\u27bf]"
)


def verify_readme_structure(readme: str, plugin_type: str) -> list[str]:
    """Check required sections exist and are in order."""
    errors: list[str] = []
    headers = [m.group(1) for m in SECTION_HEADER_RE.finditer(readme)]
    header_keys = [h.strip().lower() for h in headers]

    required = MARKETPLACE_SECTIONS if plugin_type == "marketplace" else REQUIRED_SECTIONS

    for section in required:
        if section not in header_keys:
            expected = EXACT_HEADERS.get(section, section.title())
            errors.append(f"README missing required section: ## {expected}")

    # Check section order (only for sections that exist)
    present_ordered = [s for s in SECTION_ORDER if s in header_keys]
    actual_ordered = [s for s in header_keys if s in SECTION_ORDER]
    if present_ordered != actual_ordered:
        errors.append(
            "README sections out of order"
            f" (expected: {', '.join(present_ordered)},"
            f" got: {', '.join(actual_ordered)})"
        )

    # Check badges for marketplace
    if plugin_type == "marketplace":
        if "shields.io" not in readme and "img.shields.io" not in readme:
            errors.append("README missing badges (required for marketplace)")

    return errors


def verify_readme_style(readme: str) -> list[str]:
    """Check style rules: naming, emoji, capitalization."""
    errors: list[str] = []
    headers = list(SECTION_HEADER_RE.finditer(readme))

    for m in headers:
        header_text = m.group(1).strip()
        header_key = header_text.lower()

        # Check exact naming for known headers
        if header_key in EXACT_HEADERS:
            expected = EXACT_HEADERS[header_key]
            if header_text != expected:
                errors.append(
                    f'README header "## {header_text}" should be "## {expected}"'
                )

        # No emoji in headers
        if EMOJI_RE.search(header_text):
            errors.append(f'README header "## {header_text}" contains emoji')

        # Sentence case check (first word capitalized, rest lowercase)
        # Exception: proper nouns, acronyms, and exact headers
        if header_key not in EXACT_HEADERS:
            words = header_text.split()
            if len(words) > 1:
                for word in words[1:]:
                    # Skip proper nouns / acronyms (all caps, single char)
                    if word.isupper() or len(word) <= 1:
                        continue
                    if word[0].isupper() and word[1:].islower() and word not in ("I",):
                        errors.append(
                            f'README header "## {header_text}" should use sentence case'
                            f' (lowercase "{word.lower()}")'
                        )
                        break

    # No wide tables
    for line in readme.splitlines():
        if "|" in line and len(line) > 100:
            # Check it's actually a table row
            if line.strip().startswith("|") or line.strip().endswith("|"):
                errors.append(f"README has wide table row ({len(line)} chars, max 100)")
                break

    return errors
