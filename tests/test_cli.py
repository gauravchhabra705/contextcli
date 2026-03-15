import tempfile
from pathlib import Path

from typer.testing import CliRunner

from ctxcli.cli import app

runner = CliRunner()


def test_help_lists_three_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "learn" in result.output
    assert "show" in result.output
    assert "update" in result.output


def test_learn_writes_claude_md() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(app, ["learn", tmp])
        assert result.exit_code == 0
        assert "lines written" in result.output
        assert (Path(tmp) / "CLAUDE.md").exists()


def test_show_errors_when_no_claude_md() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(app, ["show", tmp])
        assert result.exit_code != 0


def test_update_writes_claude_md() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = runner.invoke(app, ["update", tmp])
        assert result.exit_code == 0
        assert "lines written" in result.output
        assert (Path(tmp) / "CLAUDE.md").exists()
