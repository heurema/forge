"""Tests for forge CLI entrypoint."""

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

    def test_register_yes(self) -> None:
        args = parse_args(["register", "--yes"])
        assert args.command == "register"
        assert args.yes is True

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
