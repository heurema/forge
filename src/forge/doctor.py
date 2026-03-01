"""Check system dependencies and configuration."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from forge.config import ConfigError, load_config


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _check_binary(name: str, binary: str) -> CheckResult:
    path = shutil.which(binary)
    if path:
        return CheckResult(name=name, passed=True, detail=path)
    return CheckResult(name=name, passed=False, detail=f"{binary} not found in PATH")


def _check_git_config(key: str) -> CheckResult:
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        value = result.stdout.strip()
        if value:
            return CheckResult(name=f"git {key}", passed=True, detail=value)
        return CheckResult(name=f"git {key}", passed=False, detail="not set")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return CheckResult(name=f"git {key}", passed=False, detail="git not available")


def _check_repo_origin(path: Path, expected_org: str, name: str) -> CheckResult:
    if not path.exists():
        return CheckResult(name=name, passed=False, detail=f"{path} does not exist")
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        if expected_org in url:
            return CheckResult(name=name, passed=True, detail=url)
        return CheckResult(
            name=name, passed=False, detail=f"origin {url} doesn't match {expected_org}"
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return CheckResult(name=name, passed=False, detail="git not available")


def run_doctor_checks(config_path: Path) -> list[CheckResult]:
    """Run all doctor checks and return results."""
    results: list[CheckResult] = []

    # Dependencies
    results.append(_check_binary("gh CLI", "gh"))
    results.append(_check_binary("git", "git"))
    results.append(_check_binary("Python", "python3"))
    results.append(_check_git_config("user.name"))
    results.append(_check_git_config("user.email"))

    # Config
    try:
        cfg = load_config(config_path)
        results.append(CheckResult(name="forge.local.md", passed=True, detail=str(config_path)))
    except ConfigError as e:
        results.append(CheckResult(name="forge.local.md", passed=False, detail=str(e)))
        return results  # Can't check repos without config

    # Repos
    results.append(
        CheckResult(
            name="skill7 workspace",
            passed=cfg.skill7_workspace.exists(),
            detail=str(cfg.skill7_workspace),
        )
    )
    results.append(_check_repo_origin(cfg.emporium_path, cfg.github_org, "emporium clone"))
    results.append(_check_repo_origin(cfg.website_path, cfg.github_org, "skill7.dev clone"))

    return results
