"""Tests for forge provider config parser and model resolution."""

from pathlib import Path

from forge.providers import ProviderConfig, load_providers_config, resolve_model, validate_model_name

VALID_CONFIG = """\
---
version: 1

defaults:
  codex:
    model: "gpt-5.3-codex"
  gemini:
    model: "gemini-3.1-pro"

routing:
  review:
    codex: "gpt-5.3-codex"
    gemini: "gemini-3-flash"
  default:
    codex: "gpt-5.2-codex"
    gemini: "gemini-3-flash"

fallback:
  on_error: "skip_warn"

privacy:
  allow_cross_vendor_fallback: true
---

# Some markdown body
"""


class TestValidateModelName:
    def test_simple_name(self) -> None:
        assert validate_model_name("gpt-5.3-codex")

    def test_with_colons_and_dots(self) -> None:
        assert validate_model_name("claude-opus-4-6")

    def test_with_colon(self) -> None:
        assert validate_model_name("model:latest")

    def test_with_underscore(self) -> None:
        assert validate_model_name("my_model_v2")

    def test_empty_string(self) -> None:
        assert not validate_model_name("")

    def test_space(self) -> None:
        assert not validate_model_name("gpt 5")

    def test_slash(self) -> None:
        assert not validate_model_name("org/model")

    def test_special_chars(self) -> None:
        assert not validate_model_name("model@v1")

    def test_newline(self) -> None:
        assert not validate_model_name("model\nname")


class TestLoadProvidersConfig:
    def test_valid_file(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text(VALID_CONFIG)
        cfg = load_providers_config(p)
        assert cfg is not None
        assert cfg.version == 1
        assert isinstance(cfg.routing, dict)
        assert isinstance(cfg.defaults, dict)

    def test_missing_file(self, tmp_path: Path) -> None:
        result = load_providers_config(tmp_path / "nope.md")
        assert result is None

    def test_no_version(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text("---\ndefaults:\n  codex:\n    model: gpt-5\n---\n")
        try:
            load_providers_config(p)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "version" in str(e).lower()

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text("# Just markdown\nNo frontmatter here.\n")
        try:
            load_providers_config(p)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "frontmatter" in str(e).lower()

    def test_invalid_model_name(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text("---\nversion: 1\ndefaults:\n  codex:\n    model: \"bad model name\"\n---\n")
        try:
            load_providers_config(p)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "model name" in str(e).lower()

    def test_bom_stripping(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text("\ufeff" + VALID_CONFIG)
        cfg = load_providers_config(p)
        assert cfg is not None
        assert cfg.version == 1

    def test_unsupported_version(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text("---\nversion: 99\n---\n")
        try:
            load_providers_config(p)
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "version" in str(e).lower()

    def test_frozen(self, tmp_path: Path) -> None:
        p = tmp_path / "providers.md"
        p.write_text(VALID_CONFIG)
        cfg = load_providers_config(p)
        assert cfg is not None
        try:
            cfg.version = 2  # type: ignore[misc]
            assert False, "Expected FrozenInstanceError"
        except AttributeError:
            pass


class TestResolveModel:
    def _make_cfg(self) -> ProviderConfig:
        return ProviderConfig(
            version=1,
            defaults={
                "codex": {"model": "default-codex"},
                "gemini": {"model": "default-gemini"},
            },
            routing={
                "review": {"codex": "review-codex", "gemini": "review-gemini"},
                "default": {"codex": "fallback-codex"},
            },
            fallback={},
            privacy={},
        )

    def test_routing_specific(self) -> None:
        cfg = self._make_cfg()
        assert resolve_model(cfg, "review", "codex") == "review-codex"

    def test_routing_default_fallback(self) -> None:
        cfg = self._make_cfg()
        # "ask" not in routing, falls to routing.default
        assert resolve_model(cfg, "ask", "codex") == "fallback-codex"

    def test_defaults_fallback(self) -> None:
        cfg = self._make_cfg()
        # gemini not in routing.default, falls to defaults.gemini.model
        assert resolve_model(cfg, "ask", "gemini") == "default-gemini"

    def test_unknown_provider(self) -> None:
        cfg = self._make_cfg()
        assert resolve_model(cfg, "review", "unknown") == ""

    def test_none_config(self) -> None:
        assert resolve_model(None, "review", "codex") == ""
