"""Tests for ConventionExtractor — pure file I/O, no external calls."""
import pytest

from ctxcli.extractor import ConventionExtractor, ConventionProfile


# ------------------------------------------------------------------ #
# 1. Empty directory → all defaults                                   #
# ------------------------------------------------------------------ #

def test_empty_directory_returns_defaults(tmp_path):
    profile = ConventionExtractor(tmp_path).extract()
    assert isinstance(profile, ConventionProfile)
    assert profile.naming_convention == "unknown"
    assert profile.test_framework == "unknown"
    assert profile.folder_structure == {}
    assert profile.import_style == "unknown"
    assert profile.has_docker is False
    assert profile.has_ci is False
    assert profile.file_count == 0
    assert profile.line_count == 0


# ------------------------------------------------------------------ #
# 2. Dockerfile present → has_docker = True                          #
# ------------------------------------------------------------------ #

def test_detects_dockerfile(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\nCMD []\n")
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.has_docker is True


def test_no_dockerfile(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.has_docker is False   # docker-compose alone doesn't count


# ------------------------------------------------------------------ #
# 3. CI detection — GitHub Actions and GitLab                        #
# ------------------------------------------------------------------ #

def test_detects_github_actions_ci(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\non: [push]\n")
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.has_ci is True


def test_detects_gitlab_ci(tmp_path):
    (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - test\n")
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.has_ci is True


# ------------------------------------------------------------------ #
# 4. Test framework — pytest                                          #
# ------------------------------------------------------------------ #

def test_detects_pytest(tmp_path):
    (tmp_path / "test_calculator.py").write_text(
        "def test_add():\n    assert 1 + 1 == 2\n"
    )
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.test_framework == "pytest"


# ------------------------------------------------------------------ #
# 5. Test framework — jest                                            #
# ------------------------------------------------------------------ #

def test_detects_jest(tmp_path):
    (tmp_path / "utils.test.js").write_text(
        "import { add } from './utils';\n"
        "test('adds numbers', () => { expect(add(1, 2)).toBe(3); });\n"
    )
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.test_framework == "jest"


# ------------------------------------------------------------------ #
# 6. Naming convention — snake_case from Python AST                  #
# ------------------------------------------------------------------ #

def test_snake_case_detected_from_python(tmp_path):
    (tmp_path / "service.py").write_text(
        "def calculate_total(item_count, unit_price):\n"
        "    total_amount = item_count * unit_price\n"
        "    return total_amount\n"
        "\n"
        "def get_user_name(user_id):\n"
        "    display_name = str(user_id)\n"
        "    return display_name\n"
        "\n"
        "def fetch_order_list():\n"
        "    order_items = []\n"
        "    return order_items\n"
    )
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.naming_convention == "snake_case"


# ------------------------------------------------------------------ #
# 7. Folder structure mapped to purposes                             #
# ------------------------------------------------------------------ #

def test_folder_structure_maps_known_dirs(tmp_path):
    for d in ("src", "tests", "docs", "utils", "api"):
        (tmp_path / d).mkdir()
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.folder_structure["src"] == "source code"
    assert profile.folder_structure["tests"] == "tests"
    assert profile.folder_structure["docs"] == "documentation"
    assert profile.folder_structure["utils"] == "utilities"
    assert profile.folder_structure["api"] == "API layer"


def test_folder_structure_unknown_dir_labelled_other(tmp_path):
    (tmp_path / "quirky_module").mkdir()
    profile = ConventionExtractor(tmp_path).extract()
    assert profile.folder_structure.get("quirky_module") == "other"


# ------------------------------------------------------------------ #
# 8. File count + line count accuracy                                #
# ------------------------------------------------------------------ #

def test_file_count_and_line_count(tmp_path):
    # 3 files × 40 lines each = 120 total lines
    for i in range(3):
        lines = "\n".join(f"x_{i}_{j} = {j}" for j in range(40))
        (tmp_path / f"module_{i}.py").write_text(lines)

    profile = ConventionExtractor(tmp_path).extract()
    assert profile.file_count == 3
    assert profile.line_count == 120


def test_files_in_skip_dirs_not_counted(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    node_modules = tmp_path / "node_modules" / "lodash"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("module.exports = {};\n")

    profile = ConventionExtractor(tmp_path).extract()
    # Only main.py should be counted; node_modules skipped
    assert profile.file_count == 1
