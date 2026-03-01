"""Tests for forge doctor module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from forge.doctor import CheckResult, run_doctor_checks


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
