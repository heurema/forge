"""CLI entrypoint for forge plugin lifecycle manager."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(prog="forge", description="Plugin lifecycle manager")
    sub = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = sub.add_parser("new", help="Scaffold a new plugin")
    p_new.add_argument("name", help="Plugin name (lowercase, hyphens)")
    p_new.add_argument("--type", choices=["marketplace", "project", "local"], default="marketplace")
    p_new.add_argument(
        "--category", choices=["devtools", "trading", "creative"], default="devtools"
    )
    p_new.add_argument("--description", default="", help="Plugin description")
    p_new.add_argument("--yes", action="store_true", help="Skip confirmations")

    # status
    sub.add_parser("status", help="Show plugin health dashboard")

    # verify
    sub.add_parser("verify", help="Run strict quality checks")

    # register
    p_reg = sub.add_parser("register", help="Register in applicable registries")
    p_reg.add_argument("--dry-run", action="store_true", help="Show what would be done")
    p_reg.add_argument("--yes", action="store_true", help="Skip confirmations")

    # readme
    p_readme = sub.add_parser("readme", help="Generate or update README from template")
    p_readme.add_argument("--all", action="store_true", help="Update all plugins in workspace")
    p_readme.add_argument("--dry-run", action="store_true", help="Show diff without writing")
    p_readme.add_argument("--force", action="store_true", help="Overwrite without merge")
    p_readme.add_argument("--template", type=str, help="Path to custom template")

    # doctor
    sub.add_parser("doctor", help="Check dependencies and config")

    return parser.parse_args(argv)


def _config_path() -> Path:
    return Path.home() / ".claude" / "forge.local.md"


def _find_plugin_dir() -> Path:
    """Find nearest plugin directory by walking up."""
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / ".claude-plugin" / "plugin.json").exists():
            return current
        # Stop at git root to avoid escaping repo
        if (current / ".git").exists():
            break
        current = current.parent
    print(
        "Error: not inside a plugin directory (no .claude-plugin/plugin.json found)",
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_doctor() -> int:
    from forge.doctor import run_doctor_checks

    results = run_doctor_checks(_config_path())
    any_failed = False
    for r in results:
        icon = "\u2705" if r.passed else "\u274c"
        print(f"  {icon} {r.name}: {r.detail}")
        if not r.passed:
            any_failed = True
    return 1 if any_failed else 0


def cmd_status() -> int:
    from forge.config import ConfigError, load_config
    from forge.status import check_plugin_status

    plugin_dir = _find_plugin_dir()
    try:
        cfg = load_config(_config_path())
        checks = check_plugin_status(
            plugin_dir,
            skill7_workspace=cfg.skill7_workspace,
            emporium_path=cfg.emporium_path,
            website_path=cfg.website_path,
        )
    except ConfigError:
        checks = check_plugin_status(plugin_dir)

    try:
        manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: cannot read plugin.json: {e}", file=sys.stderr)
        manifest = {}
    print(f"forge status: {manifest.get('name', '?')} ({manifest.get('type', '?')})\n")
    for c in checks:
        icon = "\u2705" if c.passed else "\u274c"
        print(f"  {icon} {c.name}: {c.detail}")
    return 0


def cmd_verify() -> int:
    from forge.verify import verify_plugin

    plugin_dir = _find_plugin_dir()
    result = verify_plugin(plugin_dir)
    if result.passed:
        print("PASS: all checks passed")
        return 0
    print("FAIL:")
    for e in result.errors:
        print(f"  - {e}")
    return 1


def cmd_new(args: argparse.Namespace) -> int:
    from forge.config import ConfigError, load_config
    from forge.scaffold import ScaffoldError, scaffold_plugin

    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    # src/forge/cli.py -> src/forge/ -> src/ -> forge-root/templates/

    if args.type == "local":
        target = Path.cwd() / args.name
        github_org = "heurema"  # default for local
        cfg = None
    else:
        try:
            cfg = load_config(_config_path())
        except ConfigError as e:
            print(f"Config error: {e}", file=sys.stderr)
            print("Run: forge doctor", file=sys.stderr)
            return 1
        github_org = cfg.github_org

    if args.type != "local":
        assert cfg is not None  # guaranteed by else-branch above
        target = cfg.skill7_workspace / args.category / args.name

    description = args.description or f"{args.name} plugin"

    try:
        scaffold_plugin(
            target_dir=target,
            name=args.name,
            plugin_type=args.type,
            category=args.category,
            description=description,
            github_org=github_org,
            templates_dir=templates_dir,
        )
    except ScaffoldError as e:
        print(f"Scaffold error: {e}", file=sys.stderr)
        return 1

    # Git init + initial commit
    import subprocess

    # Pre-flight: check git user config
    r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
    if not r.stdout.strip():
        print(
            "Error: git user.name not set. Run: git config --global user.name 'Your Name'",
            file=sys.stderr,
        )
        return 1

    try:
        subprocess.run(["git", "init"], cwd=str(target), check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(target), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"feat: scaffold {args.name} plugin"],
            cwd=str(target),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"Error: git init/commit failed: {e.stderr.strip() if e.stderr else e}", file=sys.stderr
        )
        return 1

    # For marketplace: create GitHub repo + push
    if args.type == "marketplace":
        r = subprocess.run(
            [
                "gh",
                "repo",
                "create",
                f"{github_org}/{args.name}",
                "--public",
                "--description",
                description,
                "--source",
                str(target),
                "--push",
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            print(f"GitHub repo created and pushed: github.com/{github_org}/{args.name}")
        elif "already exists" in r.stderr:
            # Repo exists — set remote (idempotent: works whether origin exists or not)
            print("GitHub repo already exists, setting remote...")
            subprocess.run(
                ["git", "remote", "remove", "origin"],
                cwd=str(target),
                capture_output=True,  # ignore error if no origin
            )
            subprocess.run(
                ["git", "remote", "add", "origin", f"git@github.com:{github_org}/{args.name}.git"],
                cwd=str(target),
                capture_output=True,
            )
            push_r = subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=str(target),
                capture_output=True,
                text=True,
            )
            if push_r.returncode != 0:
                print(
                    f"Warning: push failed ({push_r.stderr.strip()}). Push manually.",
                    file=sys.stderr,
                )
        else:
            print(
                f"Warning: gh repo create failed ({r.stderr.strip()}). Create manually.",
                file=sys.stderr,
            )

    print(f"\nPlugin created at: {target}")
    print(f"Next: cd {target}, develop, then /forge-verify && /forge-register")
    return 0


def _resolve_template(args: argparse.Namespace) -> Path:
    """Resolve README template path: CLI arg > config > built-in."""
    builtin = Path(__file__).resolve().parent.parent.parent / "templates" / "README.md.j2"

    if hasattr(args, "template") and args.template:
        p = Path(args.template).expanduser()
        if not p.exists():
            print(f"Error: template not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p

    try:
        from forge.config import ConfigError, load_config

        cfg = load_config(_config_path())
        if cfg.readme_template and cfg.readme_template.exists():
            return cfg.readme_template
    except (ConfigError, Exception):
        pass

    return builtin


def _readme_for_plugin(
    plugin_dir: Path, template_path: Path, *, merge: bool, dry_run: bool
) -> int:
    """Generate/update README for a single plugin. Returns 0 on success."""
    from forge.readme import generate_readme

    try:
        manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest_path.exists():
            print(f"  skip: {plugin_dir.name} (no plugin.json)")
            return 0

        content, changes = generate_readme(plugin_dir, template_path, merge=merge)
        change_str = ", ".join(changes)

        if "no changes needed" in change_str:
            print(f"  {plugin_dir.name}: no changes")
            return 0

        if dry_run:
            print(f"  {plugin_dir.name}: {change_str} (dry-run)")
            return 0

        (plugin_dir / "README.md").write_text(content)
        print(f"  {plugin_dir.name}: {change_str}")
        return 0
    except Exception as e:
        print(f"  {plugin_dir.name}: error: {e}", file=sys.stderr)
        return 1


def cmd_readme(args: argparse.Namespace) -> int:
    template_path = _resolve_template(args)
    merge = not args.force
    dry_run = args.dry_run

    if args.all:
        from forge.config import ConfigError, load_config

        try:
            cfg = load_config(_config_path())
        except ConfigError as e:
            print(f"Config error: {e}", file=sys.stderr)
            return 1

        ws = cfg.skill7_workspace
        errors = 0
        count = 0
        for category_dir in sorted(ws.iterdir()):
            if not category_dir.is_dir() or category_dir.name.startswith("."):
                continue
            for plugin_dir in sorted(category_dir.iterdir()):
                if not plugin_dir.is_dir():
                    continue
                if not (plugin_dir / ".claude-plugin" / "plugin.json").exists():
                    continue
                count += 1
                errors += _readme_for_plugin(
                    plugin_dir, template_path, merge=merge, dry_run=dry_run
                )

        verb = "would update" if dry_run else "updated"
        print(f"\n{verb} {count} plugins, {errors} errors")
        return 1 if errors else 0

    plugin_dir = _find_plugin_dir()
    return _readme_for_plugin(plugin_dir, template_path, merge=merge, dry_run=dry_run)


def cmd_register(args: argparse.Namespace) -> int:
    import subprocess
    from collections.abc import Callable

    from forge.config import ConfigError, load_config
    from forge.register import (
        add_to_marketplace_json,
        add_to_registry,
        build_marketplace_entry,
        determine_targets,
    )
    from forge.verify import verify_plugin

    plugin_dir = _find_plugin_dir()
    result = verify_plugin(plugin_dir)
    if not result.passed:
        print("FAIL: verify must pass before register", file=sys.stderr)
        for e in result.errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    try:
        cfg = load_config(_config_path())
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    github_org = cfg.github_org

    manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text())
    name = manifest["name"]
    plugin_type = manifest.get("type", "marketplace")
    description = manifest.get("description", "")
    version = manifest.get("version", "0.1.0")
    category = manifest.get("tags", ["devtools"])[0] if manifest.get("tags") else "devtools"

    targets = determine_targets(plugin_type)
    print(f"Registering {name} ({plugin_type}) in {len(targets)} registries:")
    for t in targets:
        print(f"  - {t.description}")

    if args.dry_run:
        print("\n--dry-run: no changes made")
        return 0

    if not args.yes:
        answer = input("\nProceed? [y/N] ")
        if answer.lower() != "y":
            print("Aborted")
            return 1

    pr_urls: list[str] = []
    errors: list[str] = []

    def _run_git(cmd: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError(f"git failed: {' '.join(cmd)}: {r.stderr.strip()}")
        return r

    def _register_in_repo(
        repo_path: Path,
        branch: str,
        label: str,
        update_fn: Callable[[], bool],
        commit_msg: str,
        pr_title: str,
        pr_body: str,
        files_to_add: list[str],
    ) -> None:
        """Branch + update + commit + push + PR for a single repo."""
        cwd = str(repo_path)
        default_branch = "main"  # safe fallback before detection
        try:
            # Detect default branch (main or master)
            head_ref = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if head_ref.returncode == 0 and head_ref.stdout.strip():
                default_branch = head_ref.stdout.strip().split("/")[-1]
            else:
                # Fallback: check if main exists, otherwise master
                main_check = subprocess.run(
                    ["git", "rev-parse", "--verify", "main"],
                    cwd=cwd,
                    capture_output=True,
                    timeout=10,
                )
                default_branch = "main" if main_check.returncode == 0 else "master"

            # Check for existing local branch
            existing = _run_git(["git", "branch", "--list", branch], cwd)
            if branch in existing.stdout:
                print(f"  \u26a0\ufe0f branch {branch} already exists in {label}, skipping")
                return

            # Check for existing remote branch (skip if no remote)
            remote_check = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", branch],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if remote_check.returncode == 0 and remote_check.stdout.strip():
                print(f"  \u26a0\ufe0f branch {branch} already on remote {label}, skipping")
                return

            # Refuse if repo has uncommitted changes
            status = _run_git(["git", "status", "--porcelain"], cwd)
            if status.stdout.strip():
                errors.append(f"{label}: repo has uncommitted changes, refusing to checkout")
                return

            _run_git(["git", "checkout", default_branch], cwd)
            _run_git(["git", "pull"], cwd)
            _run_git(["git", "checkout", "-b", branch], cwd)

            added = update_fn()
            if not added:
                print(f"  \u26a0\ufe0f already in {label}, skipping")
                _run_git(["git", "checkout", default_branch], cwd)
                # Clean up empty branch to avoid blocking future runs
                subprocess.run(
                    ["git", "branch", "-d", branch],
                    cwd=cwd,
                    capture_output=True,
                    timeout=10,
                )
                return

            for f in files_to_add:
                _run_git(["git", "add", f], cwd)
            _run_git(["git", "commit", "-m", commit_msg], cwd)
            _run_git(["git", "push", "-u", "origin", branch], cwd)

            # Use subprocess.run directly for gh (don't raise on non-zero)
            r = subprocess.run(
                ["gh", "pr", "create", "--title", pr_title, "--body", pr_body],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode == 0:
                pr_urls.append(r.stdout.strip())
                print(f"  \u2705 {label} PR created")
            else:
                errors.append(f"{label}: gh pr create failed: {r.stderr.strip()}")
        except Exception as e:
            errors.append(f"{label}: {e}")
            # Try to restore default branch — safe cleanup, ignore failures
            try:
                subprocess.run(
                    ["git", "checkout", default_branch],
                    cwd=cwd,
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass  # Best-effort cleanup

    # skill7 registry — local-only (skill7 has no remote)
    if plugin_type in ("marketplace", "project"):
        ws = cfg.skill7_workspace
        reg_file = ws / "registry.json"
        if reg_file.exists():
            try:
                added = add_to_registry(
                    reg_file,
                    name,
                    category,
                    version,
                    description=description,
                    owner=github_org,
                )
                if added:
                    # Commit locally (no push — skill7 has no remote)
                    add_r = subprocess.run(
                        ["git", "add", "registry.json"],
                        cwd=str(ws),
                        capture_output=True,
                        timeout=10,
                    )
                    commit_r = subprocess.run(
                        ["git", "commit", "-m", f"feat: add {name} to registry"],
                        cwd=str(ws),
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if add_r.returncode != 0 or commit_r.returncode != 0:
                        errors.append(
                            f"skill7 registry: git commit failed: {commit_r.stderr.strip()}"
                        )
                    else:
                        print("  \u2705 skill7 registry updated (local commit)")
                else:
                    print("  \u26a0\ufe0f already in skill7 registry, skipping")
            except Exception as e:
                errors.append(f"skill7 registry: {e}")
        else:
            # Fallback: run update-registry.py if registry.json doesn't exist
            reg_script = ws / "scripts" / "update-registry.py"
            if reg_script.exists():
                try:
                    subprocess.run(
                        ["python3", str(reg_script)],
                        cwd=str(ws),
                        check=True,
                        timeout=30,
                    )
                    print("  \u2705 skill7 registry regenerated via update-registry.py")
                except Exception as e:
                    errors.append(f"skill7 registry: {e}")

    if plugin_type != "marketplace":
        if errors:
            print("\nErrors:")
            for err in errors:
                print(f"  - {err}")
            return 1
        return 0

    # Emporium
    entry = build_marketplace_entry(name, description, category, github_org)
    branch = f"forge/add-{name}"

    def _update_emporium() -> bool:
        return add_to_marketplace_json(
            cfg.emporium_path / ".claude-plugin" / "marketplace.json", entry
        )

    _register_in_repo(
        cfg.emporium_path,
        branch,
        "emporium",
        _update_emporium,
        f"feat: add {name} to marketplace",
        f"Add {name} to marketplace",
        f"Adds {name} plugin to emporium registry.",
        [".claude-plugin/marketplace.json"],
    )

    # Website — marketplace.json + plugin-meta.json
    website_files_modified: list[str] = []

    def _update_website() -> bool:
        web = cfg.website_path
        web_mp = web / "src" / "data" / "marketplace.json"
        web_meta = web / "src" / "data" / "plugin-meta.json"
        if not web_mp.exists() and not web_meta.exists():
            errors.append(
                "website: neither marketplace.json nor plugin-meta.json found in src/data/"
            )
            return False
        added = False
        if web_mp.exists():
            if add_to_marketplace_json(web_mp, entry):
                website_files_modified.append("src/data/marketplace.json")
                added = True
        if web_meta.exists():
            # plugin-meta.json: {"categories": {...}, "plugins": {"name": {...}, ...}}
            try:
                meta = json.loads(web_meta.read_text())
                if not isinstance(meta, dict) or "plugins" not in meta:
                    errors.append(
                        "website: plugin-meta.json must be a JSON object with 'plugins' key"
                    )
                elif name not in meta["plugins"]:
                    meta["plugins"][name] = {
                        "version": version,
                        "license": "MIT",
                        "status": "alpha",
                        "tags": [category],
                        "verified": False,
                    }
                    web_meta.write_text(json.dumps(meta, indent=2) + "\n")
                    website_files_modified.append("src/data/plugin-meta.json")
                    added = True
            except json.JSONDecodeError:
                errors.append("website: plugin-meta.json invalid JSON")
        return added

    _register_in_repo(
        cfg.website_path,
        branch,
        "website",
        _update_website,
        f"feat: add {name} to website",
        f"Add {name} to skill7.dev",
        f"Adds {name} plugin metadata to website.",
        website_files_modified,  # only stage files actually modified
    )

    # Summary
    if pr_urls:
        print(f"\nCreated {len(pr_urls)} PRs:")
        for url in pr_urls:
            print(f"  {url}")
    if errors:
        print("\nErrors (re-run is safe \u2014 idempotent):")
        for err in errors:
            print(f"  - {err}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    commands = {
        "new": lambda: cmd_new(args),
        "status": cmd_status,
        "verify": cmd_verify,
        "readme": lambda: cmd_readme(args),
        "register": lambda: cmd_register(args),
        "doctor": cmd_doctor,
    }
    sys.exit(commands[args.command]())


if __name__ == "__main__":
    main()
