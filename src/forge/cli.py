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
        "--category",
        choices=["devtools", "trading", "creative", "publishing", "research"],
        default="devtools",
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

    # readme
    p_readme = sub.add_parser("readme", help="Generate or update README from template")
    p_readme.add_argument("--all", action="store_true", help="Update all plugins in workspace")
    p_readme.add_argument("--dry-run", action="store_true", help="Show diff without writing")
    p_readme.add_argument("--force", action="store_true", help="Overwrite without merge")
    p_readme.add_argument("--template", type=str, help="Path to custom template")

    # doctor
    sub.add_parser("doctor", help="Check dependencies and config")

    # sync
    p_sync = sub.add_parser("sync", help="Sync plugin.json to all registries")
    p_sync.add_argument("--apply", action="store_true", help="Actually write (default: dry-run)")

    # bump
    p_bump = sub.add_parser("bump", help="Coordinated version bump")
    p_bump.add_argument("level", choices=["patch", "minor", "major"], help="Version bump level")
    p_bump.add_argument("--apply", action="store_true", help="Actually write (default: dry-run)")

    # audit
    p_audit = sub.add_parser("audit", help="Quality rubric + cross-repo consistency")
    p_audit.add_argument("--plugin", type=str, help="Plugin name to audit (default: cwd)")
    p_audit.add_argument("--allow-stale", action="store_true", help="Allow stale rubric snapshot")

    # promote
    p_promote = sub.add_parser("promote", help="Generate promotion checklist")
    p_promote.add_argument("--output", type=str, help="Write checklist to file instead of stdout")

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
    from forge.config import ConfigError, load_config
    from forge.register import register_plugin
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

    manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text())
    name = manifest["name"]

    dry_run = args.dry_run
    reg_result = register_plugin(plugin_dir, cfg, dry_run=dry_run)

    if not reg_result.success:
        print(f"Registration failed for {name}:", file=sys.stderr)
        for err in reg_result.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    mode = "dry-run" if dry_run else "applied"
    print(f"register ({mode}): {name}")
    if reg_result.pr_urls:
        for url in reg_result.pr_urls:
            print(f"  PR: {url}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from forge.config import ConfigError, load_config
    from forge.sync import sync_plugin

    plugin_dir = _find_plugin_dir()
    try:
        cfg = load_config(_config_path())
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    dry_run = not args.apply
    result = sync_plugin(plugin_dir, cfg, dry_run=dry_run)
    mode = "dry-run" if dry_run else "applied"
    print(f"sync ({mode}):")
    for target, status in result.statuses.items():
        print(f"  {target}: {status}")
    return 0


def cmd_bump(args: argparse.Namespace) -> int:
    from forge.bump import bump_version
    from forge.config import ConfigError, load_config

    plugin_dir = _find_plugin_dir()
    try:
        cfg = load_config(_config_path())
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    dry_run = not args.apply
    result = bump_version(plugin_dir, cfg, args.level, dry_run=dry_run)
    mode = "dry-run" if dry_run else "applied"
    print(f"bump {args.level} ({mode}):")
    print(f"  {result.old_version} → {result.new_version}")
    for target, status in result.files_written.items():
        print(f"  {target}: {status}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from forge.audit import audit_plugin
    from forge.config import ConfigError, load_config

    try:
        cfg = load_config(_config_path())
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    if args.plugin:
        # Search category dirs for plugin
        ws = cfg.skill7_workspace
        if not ws.exists():
            print(f"Error: workspace unreachable: {ws}", file=sys.stderr)
            return 1
        plugin_dir = None
        for cat_dir in sorted(ws.iterdir()):
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue
            candidate = cat_dir / args.plugin
            if (candidate / ".claude-plugin" / "plugin.json").exists():
                plugin_dir = candidate
                break
        if plugin_dir is None:
            print(f"Error: plugin not found: {args.plugin}", file=sys.stderr)
            return 1
    else:
        plugin_dir = _find_plugin_dir()

    result = audit_plugin(plugin_dir, cfg, allow_stale=args.allow_stale)
    if result.snapshot_error:
        print(f"Rubric: ERROR — {result.snapshot_error}")
    elif result.rubric_score is not None:
        print(f"Rubric: {result.rubric_score}/12")
    if result.rubric_errors:
        for err in result.rubric_errors:
            print(f"  - {err}")
    if result.consistency_errors:
        print("Consistency:")
        for err in result.consistency_errors:
            print(f"  - {err}")
    has_errors = bool(result.snapshot_error or result.rubric_errors or result.consistency_errors)
    return 1 if has_errors else 0


def cmd_promote(args: argparse.Namespace) -> int:
    from forge.promote import generate_checklist

    plugin_dir = _find_plugin_dir()
    checklist = generate_checklist(plugin_dir)
    if args.output:
        Path(args.output).write_text(checklist)
        print(f"Checklist written to {args.output}")
    else:
        print(checklist)
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
        "sync": lambda: cmd_sync(args),
        "bump": lambda: cmd_bump(args),
        "audit": lambda: cmd_audit(args),
        "promote": lambda: cmd_promote(args),
    }
    sys.exit(commands[args.command]())


if __name__ == "__main__":
    main()
