"""Edge-case and robustness tests added in Chunk 6."""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ctxcli.cli import app
from ctxcli.extractor import ConventionExtractor
from ctxcli.generator import ClaudeMdGenerator
from ctxcli.scanner import StackProfile, StackScanner

runner = CliRunner()


# ------------------------------------------------------------------ #
# 1. hatchling pyproject.toml → install cmd is "pip install -e ."    #
# ------------------------------------------------------------------ #

def test_hatchling_pyproject_uses_editable_install(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\n'
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n\n'
        '[project]\n'
        'name = "myapp"\n'
        'dependencies = ["flask>=2.3"]\n'
    )
    stack = StackScanner(tmp_path).scan()
    assert stack.package_manager == "pyproject"

    from ctxcli.extractor import ConventionProfile
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "pip install -e ." in result
    assert "pip install -r requirements.txt" not in result


# ------------------------------------------------------------------ #
# 2. pyproject.toml always listed in Key Files                       #
# ------------------------------------------------------------------ #

def test_pyproject_toml_in_key_files_for_hatchling(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n'
        '[project]\nname = "x"\ndependencies = []\n'
    )
    stack = StackScanner(tmp_path).scan()
    from ctxcli.extractor import ConventionProfile
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "pyproject.toml" in result


def test_pyproject_toml_in_key_files_for_poetry(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "x"\nversion = "0.1.0"\n\n'
        '[tool.poetry.dependencies]\npython = "^3.11"\nflask = "^2.0"\n'
    )
    stack = StackScanner(tmp_path).scan()
    from ctxcli.extractor import ConventionProfile
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "pyproject.toml" in result


# ------------------------------------------------------------------ #
# 3. --dry-run: prints output but does NOT write CLAUDE.md           #
# ------------------------------------------------------------------ #

def test_dry_run_does_not_write_file(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires=["hatchling"]\nbuild-backend="hatchling.build"\n'
        '[project]\nname="x"\ndependencies=[]\n'
    )
    result = runner.invoke(app, ["learn", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    assert not (tmp_path / "CLAUDE.md").exists()
    # Content should be printed to stdout
    assert "Project Overview" in result.output


# ------------------------------------------------------------------ #
# 4. Empty directory → minimal CLAUDE.md (no crash, no empty file)  #
# ------------------------------------------------------------------ #

def test_empty_directory_produces_minimal_claude_md(tmp_path):
    result = runner.invoke(app, ["learn", str(tmp_path)])
    assert result.exit_code == 0
    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert len(content.strip()) > 0
    assert "No recognized stack detected" in content


# ------------------------------------------------------------------ #
# 5. --verbose: lists scanned files in output                        #
# ------------------------------------------------------------------ #

def test_verbose_lists_scanned_files(tmp_path):
    (tmp_path / "main.py").write_text("def hello(): pass\n")
    (tmp_path / "utils.py").write_text("def helper(): pass\n")

    result = runner.invoke(app, ["learn", str(tmp_path), "--verbose"])
    assert result.exit_code == 0
    # Verbose output should mention the scanned files
    assert "Scanned" in result.output
    assert "main.py" in result.output or "utils.py" in result.output
