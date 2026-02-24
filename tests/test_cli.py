"""Tests for the CLI entry point."""

import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

import recronslator
from recronslator.cli import main


PYTHON = sys.executable
WORKSPACE = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Direct unit tests (for coverage)
# ---------------------------------------------------------------------------

class TestMainDirect:
    def test_basic_forward(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate", "Every Monday at 3am"]):
            main()
        out = capsys.readouterr().out.strip()
        assert out == "0 3 * * 1"

    def test_describe_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate", "--describe", "0 3 * * 1"]):
            main()
        out = capsys.readouterr().out.strip()
        assert "Monday" in out

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate", "--version"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0

    def test_invalid_input_exits_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate", "biweekly on monday"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "Error" in err

    def test_no_args_no_stdin_exits_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate"]):
            with mock.patch("sys.stdin.isatty", return_value=True):
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 1

    def test_stdin_input(self, capsys: pytest.CaptureFixture[str]) -> None:
        with mock.patch("sys.argv", ["recronslate"]):
            with mock.patch("sys.stdin.isatty", return_value=False):
                with mock.patch("sys.stdin.read", return_value="Every 15 minutes"):
                    main()
        out = capsys.readouterr().out.strip()
        assert out == "*/15 * * * *"


# ---------------------------------------------------------------------------
# Subprocess integration tests (verify installed entry point)
# ---------------------------------------------------------------------------

def run_cli(*args: str, stdin: str | None = None) -> tuple[int, str, str]:
    """Run the recronslate CLI and return (returncode, stdout, stderr)."""
    cmd = [PYTHON, "-m", "recronslator.cli"] + list(args)
    result = subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        cwd=WORKSPACE,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestCLIForwardTranslation:
    def test_basic_schedule(self) -> None:
        rc, out, err = run_cli("Every Monday at 3am")
        assert rc == 0
        assert out == "0 3 * * 1"

    def test_multi_word_schedule(self) -> None:
        rc, out, err = run_cli("Every", "15", "minutes")
        assert rc == 0
        assert out == "*/15 * * * *"

    def test_pipe_input(self) -> None:
        rc, out, err = run_cli(stdin="Every 15 minutes")
        assert rc == 0
        assert out == "*/15 * * * *"

    def test_invalid_schedule_exits_1(self) -> None:
        rc, out, err = run_cli("biweekly on monday")
        assert rc == 1
        assert "Error" in err

    def test_empty_input_exits_1(self) -> None:
        rc, out, err = run_cli("")
        assert rc == 1


class TestCLIReverseTranslation:
    def test_describe_flag(self) -> None:
        rc, out, err = run_cli("--describe", "0 3 * * 1")
        assert rc == 0
        assert "Monday" in out
        assert "3:00 AM" in out

    def test_d_short_flag(self) -> None:
        rc, out, err = run_cli("-d", "*/15 * * * *")
        assert rc == 0
        assert "15" in out

    def test_describe_invalid_cron_exits_1(self) -> None:
        rc, out, err = run_cli("--describe", "0 99 * * *")
        assert rc == 1
        assert "Error" in err


class TestCLIVersion:
    def test_version_flag(self) -> None:
        rc, out, err = run_cli("--version")
        assert rc == 0
        assert "1.0.0" in out
