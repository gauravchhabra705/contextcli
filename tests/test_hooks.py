"""Tests for ctx install-hook and ctx uninstall-hook."""
import stat
from pathlib import Path

from typer.testing import CliRunner

from ctxcli.cli import app
from ctxcli.hooks import (
    HOOK_SIGNATURE,
    generate_hook_content,
    is_ctxcli_hook,
)

runner = CliRunner()


def _make_git_dir(root: Path) -> Path:
    """Create a minimal .git/hooks structure and return the hooks dir."""
    hooks = root / ".git" / "hooks"
    hooks.mkdir(parents=True)
    return hooks


# ------------------------------------------------------------------ #
# Unit tests for hooks.py helpers                                     #
# ------------------------------------------------------------------ #

def test_generate_hook_contains_signature():
    content = generate_hook_content("/usr/local/bin/ctx")
    assert HOOK_SIGNATURE in content


def test_generate_hook_contains_watched_files():
    content = generate_hook_content("/usr/bin/ctx")
    for f in ("package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml"):
        assert f in content


def test_generate_hook_contains_ctx_bin():
    content = generate_hook_content("/home/user/.venv/bin/ctx")
    assert '/home/user/.venv/bin/ctx' in content


def test_generate_hook_contains_source_file_check():
    content = generate_hook_content("ctx")
    assert ".py" in content
    assert ".ts" in content


def test_is_ctxcli_hook_true_for_generated_hook():
    content = generate_hook_content("/usr/bin/ctx")
    assert is_ctxcli_hook(content) is True


def test_is_ctxcli_hook_false_for_foreign_hook():
    assert is_ctxcli_hook("#!/bin/sh\necho 'custom'\n") is False


# ------------------------------------------------------------------ #
# CLI: ctx install-hook                                               #
# ------------------------------------------------------------------ #

def test_install_hook_creates_file(tmp_path):
    _make_git_dir(tmp_path)
    result = runner.invoke(app, ["install-hook", str(tmp_path)])

    assert result.exit_code == 0, result.output
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    assert hook.exists()


def test_install_hook_content_is_correct(tmp_path):
    _make_git_dir(tmp_path)
    runner.invoke(app, ["install-hook", str(tmp_path)])

    content = (tmp_path / ".git" / "hooks" / "post-commit").read_text()
    assert HOOK_SIGNATURE in content
    assert "ctx update" in content or "CTX_BIN" in content
    assert "package.json" in content


def test_install_hook_file_is_executable(tmp_path):
    _make_git_dir(tmp_path)
    runner.invoke(app, ["install-hook", str(tmp_path)])

    hook = tmp_path / ".git" / "hooks" / "post-commit"
    mode = hook.stat().st_mode
    assert mode & stat.S_IEXEC, "post-commit hook must be executable"


def test_install_hook_prints_success_message(tmp_path):
    _make_git_dir(tmp_path)
    result = runner.invoke(app, ["install-hook", str(tmp_path)])

    assert "Hook installed" in result.output
    assert "CLAUDE.md will update automatically" in result.output


# ------------------------------------------------------------------ #
# CLI: install-hook error — no .git directory                        #
# ------------------------------------------------------------------ #

def test_install_hook_errors_without_git_dir(tmp_path):
    # No .git directory created
    result = runner.invoke(app, ["install-hook", str(tmp_path)])

    assert result.exit_code != 0
    assert "No git repository found" in result.output


# ------------------------------------------------------------------ #
# CLI: install-hook overwrite prompt                                  #
# ------------------------------------------------------------------ #

def test_install_hook_overwrite_declined_preserves_original(tmp_path):
    _make_git_dir(tmp_path)
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho 'original'\n")

    # Press Enter → default = N
    result = runner.invoke(app, ["install-hook", str(tmp_path)], input="\n")

    assert result.exit_code == 0
    assert hook.read_text() == "#!/bin/sh\necho 'original'\n"


def test_install_hook_overwrite_confirmed_replaces_hook(tmp_path):
    _make_git_dir(tmp_path)
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho 'original'\n")

    result = runner.invoke(app, ["install-hook", str(tmp_path)], input="y\n")

    assert result.exit_code == 0
    assert HOOK_SIGNATURE in hook.read_text()


# ------------------------------------------------------------------ #
# CLI: ctx uninstall-hook                                             #
# ------------------------------------------------------------------ #

def test_uninstall_hook_removes_ctxcli_hook(tmp_path):
    _make_git_dir(tmp_path)
    runner.invoke(app, ["install-hook", str(tmp_path)])
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    assert hook.exists()

    result = runner.invoke(app, ["uninstall-hook", str(tmp_path)])

    assert result.exit_code == 0
    assert not hook.exists()
    assert "Hook removed" in result.output


def test_uninstall_hook_warns_for_foreign_hook_and_aborts(tmp_path):
    _make_git_dir(tmp_path)
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho 'my custom hook'\n")

    # Decline removal (Enter = default = N)
    result = runner.invoke(app, ["uninstall-hook", str(tmp_path)], input="\n")

    assert "was not installed by ctxcli" in result.output
    assert hook.exists(), "foreign hook must not be removed when user declines"


def test_uninstall_hook_foreign_hook_removed_when_confirmed(tmp_path):
    _make_git_dir(tmp_path)
    hook = tmp_path / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho 'my custom hook'\n")

    result = runner.invoke(app, ["uninstall-hook", str(tmp_path)], input="y\n")

    assert result.exit_code == 0
    assert not hook.exists()


def test_uninstall_hook_no_op_when_hook_missing(tmp_path):
    _make_git_dir(tmp_path)
    result = runner.invoke(app, ["uninstall-hook", str(tmp_path)])
    assert result.exit_code == 0
    assert "No post-commit hook found" in result.output
