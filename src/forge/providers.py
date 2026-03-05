"""Parse and resolve emporium provider configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_MODEL_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


def validate_model_name(name: str) -> bool:
    """Return True if *name* matches the allowed model‑name pattern."""
    return bool(_MODEL_RE.match(name))


@dataclass(frozen=True)
class ProviderConfig:
    version: int
    defaults: dict[str, object] = field(default_factory=dict)
    routing: dict[str, object] = field(default_factory=dict)
    fallback: dict[str, object] = field(default_factory=dict)
    privacy: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# YAML‑subset line parser (no PyYAML dependency)
# ---------------------------------------------------------------------------

def _coerce_value(raw: str) -> object:
    """Best‑effort coerce a scalar string to int / float / bool / str."""
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _parse_yaml_block(lines: list[str]) -> dict[str, object]:
    """Minimal nested‑dict parser for the JSON‑compatible YAML subset.

    Handles:
    * ``key: value`` (scalars)
    * ``key:`` followed by indented children (nested dicts)
    * ``- "item"`` lists under a parent key
    """
    result: dict[str, object] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = len(line) - len(stripped)
        key_part, sep, val_part = stripped.partition(":")
        if not sep:
            i += 1
            continue

        key = key_part.strip()
        val_raw = val_part.strip().strip("\"'")

        if val_raw:
            # scalar
            result[key] = _coerce_value(val_raw)
            i += 1
        else:
            # collect child block (higher indent)
            children: list[str] = []
            i += 1
            while i < len(lines):
                child_line = lines[i]
                child_stripped = child_line.lstrip()
                if not child_stripped or child_stripped.startswith("#"):
                    children.append(child_line)
                    i += 1
                    continue
                child_indent = len(child_line) - len(child_stripped)
                if child_indent <= indent:
                    break
                children.append(child_line)
                i += 1

            # Detect list vs dict
            first_non_blank = next(
                (l.lstrip() for l in children if l.strip() and not l.strip().startswith("#")),
                "",
            )
            if first_non_blank.startswith("- "):
                items: list[str] = []
                for cl in children:
                    cs = cl.strip()
                    if cs.startswith("- "):
                        items.append(cs[2:].strip().strip("\"'"))
                result[key] = items
            else:
                result[key] = _parse_yaml_block(children)

    return result


def _parse_frontmatter(text: str) -> dict[str, object] | None:
    """Extract YAML frontmatter between ``---`` delimiters.

    Returns ``None`` when no frontmatter is found.
    """
    # Strip BOM
    if text.startswith("\ufeff"):
        text = text[1:]

    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        return None

    block = text[3:end]
    lines = block.splitlines()
    # Drop the leading blank line that follows the opening ---
    if lines and not lines[0].strip():
        lines = lines[1:]

    try:
        import yaml as _yaml  # type: ignore[import-untyped]

        data: dict[str, object] = _yaml.safe_load("\n".join(lines)) or {}
    except ImportError:
        data = _parse_yaml_block(lines)

    return data


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _collect_model_names(obj: object) -> list[str]:
    """Walk *obj* and return every leaf string that looks like a model name.

    Heuristic: any string value whose dict‑key is ``"model"`` **or** any string
    value nested under the ``routing`` or ``defaults`` trees — except keys that
    are obviously not model names (``on_error``, ``order``, etc.).
    """
    names: list[str] = []

    def _walk(o: object, parent_key: str = "") -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                _walk(v, str(k))
        elif isinstance(o, list):
            for item in o:
                _walk(item, parent_key)
        elif isinstance(o, str) and parent_key == "model":
            names.append(o)

    _walk(obj)
    return names


def _collect_routing_model_names(routing: object) -> list[str]:
    """Collect model name strings from the routing dict.

    In routing, the leaf string values (e.g. routing.review.codex = "gpt-5.3-codex")
    are model names.
    """
    names: list[str] = []
    if not isinstance(routing, dict):
        return names
    for _task, providers in routing.items():
        if isinstance(providers, dict):
            for _prov, model in providers.items():
                if isinstance(model, str):
                    names.append(model)
        elif isinstance(providers, str):
            names.append(providers)
    return names


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_providers_config(path: Path) -> ProviderConfig | None:
    """Load provider configuration from a markdown file with YAML frontmatter.

    Returns ``None`` if *path* does not exist.
    Raises ``ValueError`` on structural or validation errors.
    """
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")

    data = _parse_frontmatter(text)
    if data is None:
        raise ValueError(f"No YAML frontmatter found in {path}")

    # version is mandatory
    if "version" not in data:
        raise ValueError("Missing required field: version")

    version = data["version"]
    if version != 1:
        raise ValueError(f"Unsupported version: {version}")

    defaults = data.get("defaults", {})
    routing = data.get("routing", {})
    fallback = data.get("fallback", {})
    privacy = data.get("privacy", {})

    if not isinstance(defaults, dict):
        defaults = {}
    if not isinstance(routing, dict):
        routing = {}
    if not isinstance(fallback, dict):
        fallback = {}
    if not isinstance(privacy, dict):
        privacy = {}

    # Validate model names
    all_models = _collect_model_names(defaults) + _collect_routing_model_names(routing)
    for m in all_models:
        if not validate_model_name(m):
            raise ValueError(f"Invalid model name: {m!r}")

    return ProviderConfig(
        version=int(version),
        defaults=defaults,
        routing=routing,
        fallback=fallback,
        privacy=privacy,
    )


def resolve_model(cfg: ProviderConfig | None, task: str, provider: str) -> str:
    """Resolve a model name for *task* and *provider* using the priority chain.

    Resolution order:
    1. ``routing[task][provider]``
    2. ``routing["default"][provider]``
    3. ``defaults[provider]["model"]``
    4. ``""`` (empty string)
    """
    if cfg is None:
        return ""

    routing = cfg.routing
    if isinstance(routing, dict):
        # 1. routing[task][provider]
        task_block = routing.get(task)
        if isinstance(task_block, dict):
            val = task_block.get(provider)
            if isinstance(val, str):
                return val

        # 2. routing["default"][provider]
        default_block = routing.get("default")
        if isinstance(default_block, dict):
            val = default_block.get(provider)
            if isinstance(val, str):
                return val

    # 3. defaults[provider]["model"]
    defaults = cfg.defaults
    if isinstance(defaults, dict):
        prov_block = defaults.get(provider)
        if isinstance(prov_block, dict):
            model = prov_block.get("model")
            if isinstance(model, str):
                return model

    return ""
