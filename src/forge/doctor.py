"""Check system dependencies and configuration."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
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


def refresh_rubric_snapshot(emporium_path: Path, snapshot_dir: Path) -> CheckResult:
    """Copy rubric from emporium into a local snapshot dir and write a manifest."""
    try:
        source = emporium_path / "lib" / "rubric" / "__init__.py"
        if not source.exists():
            return CheckResult(
                name="rubric snapshot",
                passed=False,
                detail=f"{source} does not exist",
            )

        snapshot_dir.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        content_hash = "sha256:" + hashlib.sha256(content).hexdigest()

        dest = snapshot_dir / "__init__.py"
        dest.write_bytes(content)

        # Try to get HEAD commit from emporium
        source_commit: str | None = None
        try:
            result = subprocess.run(
                ["git", "-C", str(emporium_path), "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                source_commit = result.stdout.strip() or None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try to get remote URL from emporium
        source_remote: str | None = None
        try:
            result = subprocess.run(
                ["git", "-C", str(emporium_path), "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                source_remote = result.stdout.strip() or None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        manifest = {
            "schema_version": "1.0",
            "content_hash": content_hash,
            "source_commit": source_commit,
            "source_remote": source_remote,
            "vendored_at": datetime.now(timezone.utc).isoformat(),
        }
        (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        return CheckResult(
            name="rubric snapshot",
            passed=True,
            detail=f"vendored {content_hash} from {emporium_path}",
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name="rubric snapshot", passed=False, detail=str(exc))


def check_gh_auth() -> CheckResult:
    """Check whether gh CLI is authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return CheckResult(name="gh auth", passed=True, detail="authenticated")
        detail = (result.stderr.strip() or result.stdout.strip() or "not authenticated")
        return CheckResult(name="gh auth", passed=False, detail=detail)
    except FileNotFoundError:
        return CheckResult(name="gh auth", passed=False, detail="gh not found in PATH")
    except subprocess.TimeoutExpired:
        return CheckResult(name="gh auth", passed=False, detail="gh auth status timed out")


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

    from forge.providers_doctor import check_providers

    providers_config = config_path.parent / "emporium-providers.local.md"
    results.extend(check_providers(providers_config))

    return results
