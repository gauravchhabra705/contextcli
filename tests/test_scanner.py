"""Tests for StackScanner — pure file I/O, no external calls."""
import json

import pytest

from ctxcli.scanner import StackProfile, StackScanner


# ------------------------------------------------------------------ #
# 1. Empty directory → all defaults                                   #
# ------------------------------------------------------------------ #

def test_empty_directory_returns_defaults(tmp_path):
    profile = StackScanner(tmp_path).scan()
    assert isinstance(profile, StackProfile)
    assert profile.language == "unknown"
    assert profile.framework == "unknown"
    assert profile.package_manager == "unknown"
    assert profile.key_dependencies == []
    assert profile.project_description == ""
    assert profile.existing_claude_md is None


# ------------------------------------------------------------------ #
# 2. package.json — React                                             #
# ------------------------------------------------------------------ #

def test_package_json_react(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
        "devDependencies": {"vite": "^5.0.0"},
    }))
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "JavaScript"
    assert profile.framework == "React"
    assert profile.package_manager == "npm"
    assert "react" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 3. package.json — Next.js (should win over React)                  #
# ------------------------------------------------------------------ #

def test_package_json_nextjs(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"next": "14.0.0", "react": "^18.0.0"},
    }))
    profile = StackScanner(tmp_path).scan()
    assert profile.framework == "Next.js"
    assert "next" in profile.key_dependencies
    assert "react" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 4. package.json — Vue                                               #
# ------------------------------------------------------------------ #

def test_package_json_vue(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"vue": "^3.4.0"},
    }))
    profile = StackScanner(tmp_path).scan()
    assert profile.framework == "Vue"
    assert profile.language == "JavaScript"


# ------------------------------------------------------------------ #
# 5. package.json — Express + Node version in engines                #
# ------------------------------------------------------------------ #

def test_package_json_express(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "engines": {"node": ">=20"},
        "dependencies": {"express": "^4.18.0"},
    }))
    profile = StackScanner(tmp_path).scan()
    assert profile.framework == "Express"
    assert any("node:" in d for d in profile.key_dependencies)


# ------------------------------------------------------------------ #
# 6. requirements.txt — Django                                        #
# ------------------------------------------------------------------ #

def test_requirements_txt_django(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "Django>=4.2\n"
        "psycopg2-binary==2.9.9\n"
        "# a comment\n"
        "celery>=5.0\n"
    )
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"
    assert profile.framework == "Django"
    assert profile.package_manager == "pip"
    assert "django" in profile.key_dependencies
    assert "celery" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 7. requirements.txt — FastAPI                                       #
# ------------------------------------------------------------------ #

def test_requirements_txt_fastapi(tmp_path):
    (tmp_path / "requirements.txt").write_text(
        "fastapi>=0.110.0\n"
        "uvicorn[standard]>=0.29\n"
        "pydantic>=2.0\n"
    )
    profile = StackScanner(tmp_path).scan()
    assert profile.framework == "FastAPI"
    assert "fastapi" in profile.key_dependencies
    assert "pydantic" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 8. pyproject.toml — Flask (PEP 621 format)                         #
# ------------------------------------------------------------------ #

def test_pyproject_toml_flask(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n'
        'name = "myapp"\n'
        'dependencies = ["flask>=2.3", "sqlalchemy>=2.0"]\n'
    )
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Python"
    assert profile.framework == "Flask"
    assert "flask" in profile.key_dependencies
    assert "sqlalchemy" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 9. go.mod — Go module + dependencies                               #
# ------------------------------------------------------------------ #

def test_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text(
        "module github.com/acme/myservice\n\n"
        "go 1.22\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.1\n"
        "\tgolang.org/x/net v0.20.0\n"
        ")\n"
    )
    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Go"
    assert profile.framework == "github.com/acme/myservice"
    assert profile.package_manager == "go modules"
    assert "github.com/gin-gonic/gin" in profile.key_dependencies
    assert "golang.org/x/net" in profile.key_dependencies


# ------------------------------------------------------------------ #
# 10. Cargo.toml + README + CLAUDE.md                                #
# ------------------------------------------------------------------ #

def test_cargo_toml_with_readme_and_claude_md(tmp_path):
    (tmp_path / "Cargo.toml").write_text(
        '[package]\n'
        'name = "blazing-api"\n'
        'version = "0.1.0"\n\n'
        '[dependencies]\n'
        'tokio = { version = "1", features = ["full"] }\n'
        'serde = "1.0"\n'
    )
    long_description = "A" * 600
    (tmp_path / "README.md").write_text(long_description)
    (tmp_path / "CLAUDE.md").write_text("# Existing context\nUse async everywhere.")

    profile = StackScanner(tmp_path).scan()
    assert profile.language == "Rust"
    assert profile.framework == "blazing-api"
    assert profile.package_manager == "cargo"
    assert "tokio" in profile.key_dependencies
    assert "serde" in profile.key_dependencies
    # README truncated to 500 chars
    assert profile.project_description == "A" * 500
    # CLAUDE.md stored verbatim
    assert profile.existing_claude_md == "# Existing context\nUse async everywhere."
