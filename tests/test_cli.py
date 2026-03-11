"""Tests for forge CLI entrypoint."""

import pytest

from forge.cli import parse_args


class TestParseArgs:
    def test_new_command(self) -> None:
        args = parse_args(["new", "my-plugin"])
        assert args.command == "new"
        assert args.name == "my-plugin"
        assert args.type == "marketplace"  # default
        assert args.category == "devtools"  # default

    def test_new_with_options(self) -> None:
        args = parse_args(["new", "sentinel", "--type", "project", "--category", "trading"])
        assert args.name == "sentinel"
        assert args.type == "project"
        assert args.category == "trading"

    def test_status_command(self) -> None:
        args = parse_args(["status"])
        assert args.command == "status"

    def test_verify_command(self) -> None:
        args = parse_args(["verify"])
        assert args.command == "verify"

    def test_register_dry_run(self) -> None:
        args = parse_args(["register", "--dry-run"])
        assert args.command == "register"
        assert args.dry_run is True

    def test_readme_command(self) -> None:
        args = parse_args(["readme"])
        assert args.command == "readme"
        assert args.all is False
        assert args.dry_run is False
        assert args.force is False
        assert args.template is None

    def test_readme_all_dry_run(self) -> None:
        args = parse_args(["readme", "--all", "--dry-run"])
        assert args.command == "readme"
        assert args.all is True
        assert args.dry_run is True

    def test_readme_force(self) -> None:
        args = parse_args(["readme", "--force"])
        assert args.force is True

    def test_readme_custom_template(self) -> None:
        args = parse_args(["readme", "--template", "/tmp/my.j2"])
        assert args.template == "/tmp/my.j2"

    def test_doctor_command(self) -> None:
        args = parse_args(["doctor"])
        assert args.command == "doctor"


class TestNewCommands:
    def test_sync_subcommand_exists(self) -> None:
        ns = parse_args(["sync"])
        assert ns.command == "sync"

    def test_sync_apply_flag(self) -> None:
        ns = parse_args(["sync", "--apply"])
        assert ns.apply is True

    def test_bump_requires_level(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["bump"])

    def test_bump_patch(self) -> None:
        ns = parse_args(["bump", "patch"])
        assert ns.level == "patch"

    def test_audit_plugin_flag(self) -> None:
        ns = parse_args(["audit", "--plugin", "signum"])
        assert ns.plugin == "signum"

    def test_audit_allow_stale(self) -> None:
        ns = parse_args(["audit", "--allow-stale"])
        assert ns.allow_stale is True

    def test_promote_output(self) -> None:
        ns = parse_args(["promote", "--output", "out.md"])
        assert ns.output == "out.md"
