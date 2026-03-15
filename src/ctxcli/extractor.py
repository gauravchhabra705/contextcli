"""Convention extractor: detect coding conventions from a project directory."""
from __future__ import annotations

import ast
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".env", "dist", "build"}

_MAX_FILES = 50          # files to read and analyse
_MAX_WALK = 2000         # hard cap on directory entries before we stop traversing
_MAX_LINES = 200

# Source extensions analysed for naming/import signals — prioritised over others
_SOURCE_EXTS = frozenset({".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb"})

_DIR_PURPOSES: dict[str, str] = {
    "src": "source code",
    "source": "source code",
    "lib": "library code",
    "app": "application code",
    "tests": "tests",
    "test": "tests",
    "spec": "tests",
    "__tests__": "tests",
    "docs": "documentation",
    "doc": "documentation",
    "scripts": "scripts",
    "script": "scripts",
    "config": "configuration",
    "configs": "configuration",
    "public": "static assets",
    "static": "static assets",
    "assets": "assets",
    "migrations": "database migrations",
    "templates": "templates",
    "views": "views",
    "models": "models",
    "controllers": "controllers",
    "routes": "routing",
    "api": "API layer",
    "utils": "utilities",
    "helpers": "helpers",
    "components": "UI components",
    "pages": "pages",
    "hooks": "hooks",
    "store": "state management",
    "services": "services",
    "types": "type definitions",
}


@dataclass
class ConventionProfile:
    naming_convention: str = "unknown"   # snake_case | camelCase | PascalCase | mixed
    test_framework: str = "unknown"      # pytest | jest | vitest | go test | rspec
    folder_structure: dict = field(default_factory=dict)   # {dir_name: purpose}
    import_style: str = "unknown"        # relative | absolute | mixed
    has_docker: bool = False
    has_ci: bool = False
    file_count: int = 0
    line_count: int = 0
    scanned_files: list = field(default_factory=list)   # Path objects of files read


class ConventionExtractor:
    """Scan a project directory and return a ConventionProfile."""

    def __init__(self, directory: str | Path) -> None:
        self.root = Path(directory).resolve()

    def extract(self) -> ConventionProfile:
        profile = ConventionProfile()

        # Root-level presence checks (no walking needed)
        profile.has_docker = (self.root / "Dockerfile").exists()
        profile.has_ci = (
            (self.root / ".github" / "workflows").is_dir()
            or (self.root / ".gitlab-ci.yml").exists()
        )

        # Top-level visible directories → folder_structure
        try:
            top_level = sorted(self.root.iterdir())
        except OSError:
            top_level = []
        for item in top_level:
            if item.is_dir() and not item.name.startswith("."):
                profile.folder_structure[item.name] = _DIR_PURPOSES.get(
                    item.name.lower(), "other"
                )

        # Walk files, accumulate naming + import signals
        name_counts: Counter[str] = Counter()
        import_counts: Counter[str] = Counter()

        for path in self._walk_files():
            profile.file_count += 1
            profile.scanned_files.append(path)
            lines = self._read_lines(path)
            profile.line_count += len(lines)
            text = "\n".join(lines)
            ext = path.suffix.lower()

            if profile.test_framework == "unknown":
                self._detect_test_framework(path, text, profile)

            if ext == ".py":
                self._analyze_python_names(text, name_counts)
                self._analyze_python_imports(text, import_counts)
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                self._analyze_js_names(text, name_counts)
                self._analyze_js_imports(text, import_counts)

        profile.naming_convention = _dominant(
            name_counts, {"snake_case", "camelCase", "PascalCase"}
        )
        profile.import_style = _dominant(import_counts, {"relative", "absolute"})
        return profile

    # ------------------------------------------------------------------ #
    # File traversal                                                       #
    # ------------------------------------------------------------------ #

    def _walk_files(self) -> Iterator[Path]:
        """Walk files with intelligent sampling for large codebases.

        Collects up to _MAX_WALK entries, then yields source files first
        (prioritised for signal quality) followed by other files, capped
        at _MAX_FILES total reads.
        """
        preferred: list[Path] = []   # source code files
        others: list[Path] = []      # everything else
        total_seen = 0

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for fname in sorted(filenames):
                total_seen += 1
                if total_seen > _MAX_WALK:
                    break  # stop collecting — codebase is huge
                path = Path(dirpath) / fname
                if path.suffix.lower() in _SOURCE_EXTS:
                    preferred.append(path)
                else:
                    others.append(path)
            if total_seen > _MAX_WALK:
                break

        yielded = 0
        for path in preferred + others:
            if yielded >= _MAX_FILES:
                return
            yield path
            yielded += 1

    def _read_lines(self, path: Path) -> list[str]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        return content.splitlines()[:_MAX_LINES]

    # ------------------------------------------------------------------ #
    # Test framework detection                                             #
    # ------------------------------------------------------------------ #

    def _detect_test_framework(
        self, path: Path, text: str, profile: ConventionProfile
    ) -> None:
        name = path.name
        if re.match(r"test_.+\.py$", name) or re.match(r".+_test\.py$", name):
            profile.test_framework = "pytest"
        elif re.search(r"\.(test|spec)\.(js|ts|jsx|tsx)$", name):
            # vitest imports differ from jest
            if re.search(r"""(from\s+['"]vitest['"]|import\s+.*from\s+['"]vitest['"])""", text):
                profile.test_framework = "vitest"
            else:
                profile.test_framework = "jest"
        elif re.match(r".+_test\.go$", name):
            profile.test_framework = "go test"
        elif re.match(r".+_spec\.rb$", name):
            profile.test_framework = "rspec"

    # ------------------------------------------------------------------ #
    # Python analysis (ast)                                               #
    # ------------------------------------------------------------------ #

    def _analyze_python_names(self, text: str, counts: Counter[str]) -> None:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _classify_name(node.name, counts)
            elif isinstance(node, ast.ClassDef):
                _classify_name(node.name, counts)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        _classify_name(target.id, counts)

    def _analyze_python_imports(self, text: str, counts: Counter[str]) -> None:
        # Relative: from .module or from ..module
        rel = len(re.findall(r"^from \.", text, re.MULTILINE))
        counts["relative"] += rel
        # Absolute: import foo or from foo (not starting with .)
        abs_count = len(re.findall(r"^(?:import [a-zA-Z]|from [a-zA-Z])", text, re.MULTILINE))
        counts["absolute"] += abs_count

    # ------------------------------------------------------------------ #
    # JS/TS analysis (regex)                                              #
    # ------------------------------------------------------------------ #

    def _analyze_js_names(self, text: str, counts: Counter[str]) -> None:
        patterns = [
            r"\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)",   # function name()
            r"\bconst\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=",  # const name =
            r"\blet\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=",    # let name =
            r"\bclass\s+([a-zA-Z_$][a-zA-Z0-9_$]*)",       # class Name
        ]
        for pat in patterns:
            for match in re.finditer(pat, text):
                _classify_name(match.group(1), counts)

    def _analyze_js_imports(self, text: str, counts: Counter[str]) -> None:
        # Relative: from './...' or from '../...'
        rel = len(re.findall(r"""from\s+['"]\.\.?/""", text))
        counts["relative"] += rel
        # Absolute: from 'package' where path doesn't start with .
        abs_count = len(re.findall(r"""from\s+['"][^.'"][^'"]*['"]""", text))
        counts["absolute"] += abs_count


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

_SKIP_NAMES = frozenset({"self", "cls", "args", "kwargs", "i", "j", "k", "x", "y", "n"})


def _classify_name(name: str, counts: Counter[str]) -> None:
    """Classify one identifier into snake_case, camelCase, or PascalCase."""
    if (
        not name
        or len(name) < 2
        or name.startswith("__")
        or name.upper() == name          # ALL_CAPS constant
        or name in _SKIP_NAMES
    ):
        return

    if "_" in name:
        counts["snake_case"] += 1
    elif name[0].isupper():
        counts["PascalCase"] += 1
    elif name[0].islower() and any(c.isupper() for c in name[1:]):
        counts["camelCase"] += 1
    # single lowercase word — ambiguous, skip


def _dominant(counts: Counter[str], keys: set[str]) -> str:
    """Return dominant key, 'mixed' if no clear winner, or 'unknown' if empty."""
    relevant = {k: counts[k] for k in keys if counts[k] > 0}
    if not relevant:
        return "unknown"
    if len(relevant) == 1:
        return next(iter(relevant))
    vals = sorted(relevant.values(), reverse=True)
    # mixed if runner-up is >= 33 % of winner
    if vals[1] >= vals[0] * 0.33:
        return "mixed"
    return max(relevant, key=lambda k: relevant[k])
