"""Tests for ClaudeMdGenerator — pure in-memory, no filesystem."""
from ctxcli.extractor import ConventionProfile
from ctxcli.generator import ClaudeMdGenerator
from ctxcli.scanner import StackProfile


def _gen(stack: StackProfile | None = None, conventions: ConventionProfile | None = None) -> str:
    return ClaudeMdGenerator(
        stack or StackProfile(),
        conventions or ConventionProfile(),
    ).generate()


# ------------------------------------------------------------------ #
# 1. Project Overview contains language, framework, description       #
# ------------------------------------------------------------------ #

def test_project_overview_contains_detected_values():
    stack = StackProfile(
        language="Python",
        framework="Django",
        project_description="Inventory management system.",
    )
    result = _gen(stack)
    assert "# Project Overview" in result
    assert "Python" in result
    assert "Django" in result
    assert "Inventory management system." in result


# ------------------------------------------------------------------ #
# 2. Tech Stack lists package manager and key dependencies           #
# ------------------------------------------------------------------ #

def test_tech_stack_lists_deps_and_package_manager():
    stack = StackProfile(
        language="Python",
        framework="Django",
        package_manager="pip",
        key_dependencies=["django", "celery", "redis"],
    )
    result = _gen(stack)
    assert "# Tech Stack" in result
    assert "pip" in result
    assert "django" in result
    assert "celery" in result
    assert "redis" in result


# ------------------------------------------------------------------ #
# 3. "unknown" values are never written to the output                #
# ------------------------------------------------------------------ #

def test_unknown_values_are_omitted():
    # All defaults → everything is "unknown"
    result = _gen()
    assert "unknown" not in result


# ------------------------------------------------------------------ #
# 4. Conventions section shows naming style and test framework        #
# ------------------------------------------------------------------ #

def test_conventions_section_shows_naming_and_test_framework():
    stack = StackProfile(language="Python")
    conventions = ConventionProfile(
        naming_convention="snake_case",
        test_framework="pytest",
        import_style="absolute",
    )
    result = _gen(stack, conventions)
    assert "# Conventions" in result
    assert "snake_case" in result
    assert "pytest" in result
    assert "absolute" in result


# ------------------------------------------------------------------ #
# 5. Notes section includes "Previously you knew:" + old content     #
# ------------------------------------------------------------------ #

def test_notes_includes_previous_claude_md():
    stack = StackProfile(existing_claude_md="Always use type hints.\nPrefer async.")
    result = _gen(stack)
    assert "# Notes" in result
    assert "Previously you knew:" in result
    assert "Always use type hints." in result
    assert "Prefer async." in result


def test_notes_section_absent_when_no_existing_claude_md():
    result = _gen(StackProfile(existing_claude_md=None))
    assert "# Notes" not in result
    assert "Previously you knew:" not in result


# ------------------------------------------------------------------ #
# 6. Development Commands inferred correctly from detected stack      #
# ------------------------------------------------------------------ #

def test_development_commands_inferred_from_stack():
    stack = StackProfile(
        language="Python",
        framework="Django",
        package_manager="pip",
    )
    conventions = ConventionProfile(test_framework="pytest")
    result = _gen(stack, conventions)
    assert "# Development Commands" in result
    assert "pip install -r requirements.txt" in result
    assert "pytest" in result
    assert "python manage.py runserver" in result


def test_development_commands_inferred_for_nextjs():
    stack = StackProfile(
        language="JavaScript",
        framework="Next.js",
        package_manager="npm",
    )
    conventions = ConventionProfile(test_framework="jest")
    result = _gen(stack, conventions)
    assert "npm install" in result
    assert "npm test" in result
    assert "npm run dev" in result


# ------------------------------------------------------------------ #
# Bonus: output stays under 150 lines for a full profile             #
# ------------------------------------------------------------------ #

def test_output_under_150_lines():
    stack = StackProfile(
        language="Python",
        framework="Django",
        package_manager="pip",
        key_dependencies=["django", "celery", "redis", "psycopg2", "gunicorn",
                          "whitenoise", "boto3", "sentry-sdk", "pydantic", "httpx"],
        project_description="A large-scale inventory management platform.",
        existing_claude_md="Use Django REST framework. Always write docstrings.",
    )
    conventions = ConventionProfile(
        naming_convention="snake_case",
        test_framework="pytest",
        import_style="absolute",
        folder_structure={
            "src": "source code", "tests": "tests", "docs": "documentation",
            "scripts": "scripts", "config": "configuration", "api": "API layer",
            "models": "models", "views": "views", "utils": "utilities",
        },
        has_docker=True,
        has_ci=True,
    )
    result = _gen(stack, conventions)
    line_count = len(result.splitlines())
    assert line_count < 150, f"Output was {line_count} lines — must be under 150"
