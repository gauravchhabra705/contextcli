"""CLAUDE.md generator from StackProfile + ConventionProfile."""
from __future__ import annotations

from ctxcli.extractor import ConventionProfile
from ctxcli.scanner import StackProfile

# --- Command inference tables ------------------------------------------------

_INSTALL_CMDS: dict[str, str] = {
    "pip": "pip install -r requirements.txt",
    "pyproject": "pip install -e .",    # hatchling / flit / pdm / setuptools pyproject.toml
    "poetry": "poetry install",
    "npm": "npm install",
    "yarn": "yarn install",
    "pnpm": "pnpm install",
    "go modules": "go mod download",
    "cargo": "cargo build",
    "maven": "mvn install",
    "gradle": "./gradlew build",
    "nuget": "dotnet restore",
}

_TEST_CMDS: dict[str, str] = {
    "pytest": "pytest",
    "jest": "npm test",
    "vitest": "npm run test",
    "go test": "go test ./...",
    "rspec": "bundle exec rspec",
}

_DEV_CMDS: dict[str, str] = {
    "Django": "python manage.py runserver",
    "FastAPI": "uvicorn main:app --reload",
    "Flask": "flask run",
    "Next.js": "npm run dev",
    "React": "npm run start",
    "Vue": "npm run dev",
    "Express": "node index.js",
    "Go": "go run .",
    "Rust": "cargo run",
    "Spring Boot": "./mvnw spring-boot:run",
}

# Key file inferred per language / package manager
_KEY_FILES: dict[str, str] = {
    "JavaScript:npm": "package.json",
    "JavaScript:yarn": "package.json",
    "JavaScript:pnpm": "package.json",
    "TypeScript:npm": "package.json",
    "TypeScript:yarn": "package.json",
    "TypeScript:pnpm": "package.json",
    "Python:pip": "requirements.txt",
    "Python:pyproject": "pyproject.toml",   # hatchling / flit / pdm / setuptools
    "Python:poetry": "pyproject.toml",
    "Go:go modules": "go.mod",
    "Rust:cargo": "Cargo.toml",
    "Java:maven": "pom.xml",
    "Java:gradle": "build.gradle",
    "Kotlin:gradle": "build.gradle",
    "C#:nuget": "*.csproj",
}


# --- Generator ---------------------------------------------------------------

class ClaudeMdGenerator:
    """Turn detected profiles into a CLAUDE.md string."""

    def __init__(self, stack: StackProfile, conventions: ConventionProfile) -> None:
        self.stack = stack
        self.conventions = conventions

    def generate(self) -> str:
        sections = [
            self._project_overview(),
            self._tech_stack(),
            self._project_structure(),
            self._conventions(),
            self._development_commands(),
            self._key_files(),
            self._notes(),
        ]
        result = "\n\n".join(s for s in sections if s)
        if not result:
            # No stack detected — emit a minimal file so Claude Code still gets something
            result = "# Project Overview\n\nNo recognized stack detected. Add language-specific config files (package.json, pyproject.toml, go.mod, etc.) for full analysis."
        return result

    # ------------------------------------------------------------------ #
    # Sections                                                             #
    # ------------------------------------------------------------------ #

    def _project_overview(self) -> str:
        s = self.stack
        lines = ["# Project Overview", ""]

        if s.language != "unknown":
            lines.append(f"**Language:** {s.language}")
        if s.framework != "unknown":
            lines.append(f"**Framework:** {s.framework}")
        if s.project_description:
            lines.append("")
            # Keep first paragraph only to stay within line budget
            first_para = s.project_description.strip().split("\n\n")[0]
            lines.append(first_para)

        if len(lines) == 2:  # only header + blank line — nothing detected
            return ""
        return "\n".join(lines)

    def _tech_stack(self) -> str:
        s = self.stack
        lines = ["# Tech Stack", ""]

        if s.language != "unknown":
            lines.append(f"**Language:** {s.language}")
        if s.framework != "unknown":
            lines.append(f"**Framework:** {s.framework}")
        if s.package_manager != "unknown":
            lines.append(f"**Package Manager:** {s.package_manager}")

        # Strip the synthetic "node:version" entry injected by the scanner
        deps = [d for d in s.key_dependencies if not d.startswith("node:")][:10]
        if deps:
            lines.append(f"**Key Dependencies:** {', '.join(deps)}")

        if len(lines) == 2:
            return ""
        return "\n".join(lines)

    def _project_structure(self) -> str:
        c = self.conventions
        if not c.folder_structure:
            return ""

        lines = ["# Project Structure", ""]
        for name, purpose in list(c.folder_structure.items())[:10]:
            lines.append(f"- `{name}/` — {purpose}")
        return "\n".join(lines)

    def _conventions(self) -> str:
        c = self.conventions
        lines = ["# Conventions", ""]

        if c.naming_convention != "unknown":
            lines.append(f"**Naming Style:** {c.naming_convention}")
        if c.import_style != "unknown":
            lines.append(f"**Import Style:** {c.import_style}")
        if c.test_framework != "unknown":
            lines.append(f"**Test Framework:** {c.test_framework}")

        if len(lines) == 2:
            return ""
        return "\n".join(lines)

    def _development_commands(self) -> str:
        s = self.stack
        c = self.conventions
        lines = ["# Development Commands", ""]

        install = _INSTALL_CMDS.get(s.package_manager, "")
        if install:
            lines.append(f"**Install:** `{install}`")

        test_cmd = _TEST_CMDS.get(c.test_framework, "")
        if test_cmd:
            lines.append(f"**Test:** `{test_cmd}`")

        dev = _DEV_CMDS.get(s.framework, "") or _DEV_CMDS.get(s.language, "")
        if dev:
            lines.append(f"**Run:** `{dev}`")

        if len(lines) == 2:
            return ""
        return "\n".join(lines)

    def _key_files(self) -> str:
        s = self.stack
        c = self.conventions
        files: list[str] = []

        key = f"{s.language}:{s.package_manager}"
        primary = _KEY_FILES.get(key, "")
        if primary:
            files.append(primary)

        if c.has_docker:
            files.append("Dockerfile")
        if c.has_ci:
            files.append(".github/workflows/")

        if not files:
            return ""

        lines = ["# Key Files", ""]
        for f in files:
            lines.append(f"- `{f}`")
        return "\n".join(lines)

    def _notes(self) -> str:
        existing = self.stack.existing_claude_md
        if not existing:
            return ""
        lines = ["# Notes", "", "Previously you knew:", "", existing.strip()]
        return "\n".join(lines)
