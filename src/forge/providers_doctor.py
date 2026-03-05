"""Provider‑related doctor checks."""

from __future__ import annotations

import shutil
from pathlib import Path

from forge.doctor import CheckResult
from forge.providers import load_providers_config


def check_providers(config_path: Path) -> list[CheckResult]:
    """Run provider‑related health checks."""
    results: list[CheckResult] = []

    # 1. Config file exists and is valid
    if not config_path.exists():
        results.append(
            CheckResult(
                name="providers config",
                passed=False,
                detail=f"{config_path} not found",
            )
        )
    else:
        try:
            cfg = load_providers_config(config_path)
            if cfg is None:
                results.append(
                    CheckResult(
                        name="providers config",
                        passed=False,
                        detail="failed to load config",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="providers config",
                        passed=True,
                        detail=str(config_path),
                    )
                )
        except ValueError as e:
            results.append(
                CheckResult(
                    name="providers config",
                    passed=False,
                    detail=str(e),
                )
            )

    # 2. codex binary in PATH
    codex_path = shutil.which("codex")
    if codex_path:
        results.append(CheckResult(name="codex CLI", passed=True, detail=codex_path))
    else:
        results.append(
            CheckResult(name="codex CLI", passed=False, detail="codex not found in PATH")
        )

    # 3. gemini binary in PATH
    gemini_path = shutil.which("gemini")
    if gemini_path:
        results.append(CheckResult(name="gemini CLI", passed=True, detail=gemini_path))
    else:
        results.append(
            CheckResult(name="gemini CLI", passed=False, detail="gemini not found in PATH")
        )

    return results
