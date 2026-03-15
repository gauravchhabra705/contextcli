"""Integration tests: run ctx learn end-to-end and verify CLAUDE.md output."""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ctxcli.cli import app

runner = CliRunner()


def _make_node_project(root: Path) -> None:
    """Write a minimal Next.js-style project into root."""
    (root / "package.json").write_text(json.dumps({
        "name": "my-nextjs-app",
        "dependencies": {"next": "14.0.0", "react": "^18.0.0", "react-dom": "^18.0.0"},
        "devDependencies": {"typescript": "^5.0", "jest": "^29.0"},
    }))
    (root / "README.md").write_text("A Next.js application for demo purposes.\n")
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "index.ts").write_text(
        "const appName: string = 'myApp';\n"
        "function getUserData(userId: string) { return userId; }\n"
    )
    (root / "tests" / "app.test.ts").write_text(
        "import { render } from '@testing-library/react';\n"
        "test('renders', () => {});\n"
    )
    (root / "Dockerfile").write_text("FROM node:20-alpine\nCMD []\n")


# ------------------------------------------------------------------ #
# 1. ctx learn creates CLAUDE.md with correct content                 #
# ------------------------------------------------------------------ #

def test_ctx_learn_creates_claude_md(tmp_path):
    _make_node_project(tmp_path)
    result = runner.invoke(app, ["learn", str(tmp_path)])

    assert result.exit_code == 0, result.output
    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md was not created"

    content = claude_md.read_text()
    assert "# Project Overview" in content
    assert "# Tech Stack" in content
    assert "# Development Commands" in content


def test_ctx_learn_detects_nextjs_stack(tmp_path):
    _make_node_project(tmp_path)
    runner.invoke(app, ["learn", str(tmp_path)])

    content = (tmp_path / "CLAUDE.md").read_text()
    assert "Next.js" in content
    # TypeScript detected from devDependencies
    assert "TypeScript" in content


def test_ctx_learn_includes_readme_description(tmp_path):
    _make_node_project(tmp_path)
    runner.invoke(app, ["learn", str(tmp_path)])

    content = (tmp_path / "CLAUDE.md").read_text()
    assert "Next.js application for demo purposes" in content


def test_ctx_learn_detects_docker(tmp_path):
    _make_node_project(tmp_path)
    runner.invoke(app, ["learn", str(tmp_path)])

    content = (tmp_path / "CLAUDE.md").read_text()
    assert "Dockerfile" in content


def test_ctx_learn_prints_line_count(tmp_path):
    _make_node_project(tmp_path)
    result = runner.invoke(app, ["learn", str(tmp_path)])

    assert "lines written" in result.output


# ------------------------------------------------------------------ #
# 2. ctx learn with existing CLAUDE.md — decline overwrite           #
# ------------------------------------------------------------------ #

def test_ctx_learn_respects_no_overwrite(tmp_path):
    _make_node_project(tmp_path)
    original = "# Original content\nDo not overwrite me.\n"
    (tmp_path / "CLAUDE.md").write_text(original)

    # Simulate user pressing Enter (default = N = no overwrite)
    result = runner.invoke(app, ["learn", str(tmp_path)], input="\n")

    assert result.exit_code == 0
    assert (tmp_path / "CLAUDE.md").read_text() == original


# ------------------------------------------------------------------ #
# 3. ctx show — prints content when CLAUDE.md exists                 #
# ------------------------------------------------------------------ #

def test_ctx_show_prints_existing_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        "# Project Overview\n\n**Language:** Python\n\n# Tech Stack\n\npip\n"
    )
    result = runner.invoke(app, ["show", str(tmp_path)])
    assert result.exit_code == 0
    assert "Python" in result.output


def test_ctx_show_errors_when_no_claude_md(tmp_path):
    result = runner.invoke(app, ["show", str(tmp_path)])
    assert result.exit_code != 0


# ------------------------------------------------------------------ #
# 4. ctx update — always writes, preserves old content in Notes      #
# ------------------------------------------------------------------ #

def test_ctx_update_preserves_previous_content(tmp_path):
    _make_node_project(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Old Notes\nAlways use TypeScript strict mode.\n")

    result = runner.invoke(app, ["update", str(tmp_path)])
    assert result.exit_code == 0

    content = (tmp_path / "CLAUDE.md").read_text()
    # Fresh scan sections present
    assert "# Project Overview" in content
    # Previous CLAUDE.md preserved under Notes
    assert "Previously you knew:" in content
    assert "Always use TypeScript strict mode." in content
