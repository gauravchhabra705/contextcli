"""Tests for BUG 1 (JS test command) and BUG 2 (Python fallback detection)."""
import json

import pytest

from ctxcli.extractor import ConventionExtractor, ConventionProfile
from ctxcli.generator import ClaudeMdGenerator, _framework_from_script
from ctxcli.scanner import StackScanner


# ================================================================== #
# BUG 1 — JS/TS test command read from package.json scripts          #
# ================================================================== #

def test_scripts_test_stored_as_test_command(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18.0.0"},
        "scripts": {"test": "vitest run --coverage"},
    }))
    profile = StackScanner(tmp_path).scan()
    assert profile.test_command == "vitest run --coverage"


def test_framework_inferred_from_vitest_script(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {"test": "vitest run"},
    }))
    stack = StackScanner(tmp_path).scan()
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    # Exact command used, not generic "npm run test"
    assert "vitest run" in result
    assert "vitest" in result   # framework shown in conventions


def test_framework_inferred_from_bun_script(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {"test": "bun test"},
    }))
    stack = StackScanner(tmp_path).scan()
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "bun test" in result
    assert "bun" in result


def test_framework_inferred_from_jest_script(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {"test": "jest --coverage"},
    }))
    stack = StackScanner(tmp_path).scan()
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "jest --coverage" in result
    assert "jest" in result


def test_no_scripts_test_falls_back_to_extractor(tmp_path):
    """No scripts.test → extractor file-pattern detection used instead."""
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {"start": "node index.js"},   # no 'test' key
        "dependencies": {"express": "^4.18.0"},
    }))
    (tmp_path / "app.test.js").write_text("test('x', () => {})")
    stack = StackScanner(tmp_path).scan()
    assert stack.test_command == ""
    conventions = ConventionExtractor(tmp_path).extract()
    result = ClaudeMdGenerator(stack, conventions).generate()
    # Extractor detected jest from *.test.js pattern
    assert "jest" in result


def test_framework_from_script_helper():
    assert _framework_from_script("vitest run") == "vitest"
    assert _framework_from_script("jest --watch") == "jest"
    assert _framework_from_script("bun test") == "bun"
    assert _framework_from_script("mocha --recursive") == "mocha"
    assert _framework_from_script("pytest -v") == "pytest"
    assert _framework_from_script("node run-tests.js") == "unknown"


# ================================================================== #
# BUG 2 — Python fallback detection                                  #
# ================================================================== #

def test_pytest_ini_triggers_python_detection(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"
    assert profile.package_manager == "pyproject"


def test_pytest_ini_sets_test_framework_in_extractor(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    conventions = ConventionExtractor(tmp_path).extract()
    assert conventions.test_framework == "pytest"


def test_init_py_triggers_python_detection(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"


def test_root_py_files_trigger_python_detection(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"


def test_src_py_files_trigger_python_detection(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("def run(): pass\n")
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"


def test_python_fallback_install_command_is_editable(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    stack = StackScanner(tmp_path).scan()
    result = ClaudeMdGenerator(stack, ConventionProfile()).generate()
    assert "pip install -e ." in result


# ================================================================== #
# action.yml in Key Files                                             #
# ================================================================== #

def test_action_yml_appears_in_key_files(tmp_path):
    (tmp_path / "action.yml").write_text("name: My Action\nruns:\n  using: node20\n")
    (tmp_path / "package.json").write_text(json.dumps({"name": "my-action"}))
    stack = StackScanner(tmp_path).scan()
    conventions = ConventionExtractor(tmp_path).extract()
    assert conventions.has_action_yml is True
    result = ClaudeMdGenerator(stack, conventions).generate()
    assert "action.yml" in result
