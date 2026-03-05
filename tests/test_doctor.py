"""Tests for forge doctor module."""

from pathlib import Path
from unittest.mock import patch

from forge.doctor import CheckResult, run_doctor_checks
from forge.providers_doctor import check_providers


class TestDoctor:
    def test_check_result_pass(self) -> None:
        r = CheckResult(name="test", passed=True, detail="ok")
        assert r.passed
        assert r.detail == "ok"

    def test_check_result_fail(self) -> None:
        r = CheckResult(name="test", passed=False, detail="missing")
        assert not r.passed

    def test_run_checks_returns_list(self, tmp_path: Path) -> None:
        results = run_doctor_checks(config_path=tmp_path / "nonexistent.md")
        assert isinstance(results, list)
        assert all(isinstance(r, CheckResult) for r in results)

    def test_missing_config_fails(self, tmp_path: Path) -> None:
        results = run_doctor_checks(config_path=tmp_path / "nonexistent.md")
        config_check = next(r for r in results if r.name == "forge.local.md")
        assert not config_check.passed

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_gh_found(self, _mock: object) -> None:
        results = run_doctor_checks(config_path=Path("/nonexistent"))
        gh_check = next(r for r in results if r.name == "gh CLI")
        assert gh_check.passed

    @patch("shutil.which", return_value=None)
    def test_gh_missing(self, _mock: object) -> None:
        results = run_doctor_checks(config_path=Path("/nonexistent"))
        gh_check = next(r for r in results if r.name == "gh CLI")
        assert not gh_check.passed


VALID_PROVIDERS = """\
---
version: 1

defaults:
  codex:
    model: "gpt-5.3-codex"

routing:
  default:
    codex: "gpt-5.2-codex"

fallback:
  on_error: "skip_warn"

privacy:
  allow_cross_vendor_fallback: true
---

# Providers
"""


class TestProvidersDoctorChecks:
    def test_config_found_valid(self, tmp_path: Path) -> None:
        p = tmp_path / "emporium-providers.local.md"
        p.write_text(VALID_PROVIDERS)
        results = check_providers(p)
        cfg_check = next(r for r in results if r.name == "providers config")
        assert cfg_check.passed

    def test_config_missing(self, tmp_path: Path) -> None:
        results = check_providers(tmp_path / "nope.md")
        cfg_check = next(r for r in results if r.name == "providers config")
        assert not cfg_check.passed
        assert "not found" in cfg_check.detail

    def test_config_invalid(self, tmp_path: Path) -> None:
        p = tmp_path / "emporium-providers.local.md"
        p.write_text("---\nno_version: true\n---\n")
        results = check_providers(p)
        cfg_check = next(r for r in results if r.name == "providers config")
        assert not cfg_check.passed
        assert "version" in cfg_check.detail.lower()
