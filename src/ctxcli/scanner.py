"""Stack scanner: detect language, framework, and dependencies from project files."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class StackProfile:
    language: str = "unknown"
    framework: str = "unknown"
    package_manager: str = "unknown"
    key_dependencies: list[str] = field(default_factory=list)
    project_description: str = ""
    existing_claude_md: Optional[str] = None


_JS_FRAMEWORK_PRIORITY = [
    ("next", "Next.js"),
    ("react", "React"),
    ("vue", "Vue"),
    ("express", "Express"),
    ("@angular/core", "Angular"),
    ("nuxt", "Nuxt"),
    ("svelte", "Svelte"),
]

_PYTHON_FRAMEWORK_PRIORITY = [
    ("django", "Django"),
    ("fastapi", "FastAPI"),
    ("flask", "Flask"),
    ("tornado", "Tornado"),
    ("starlette", "Starlette"),
]


class StackScanner:
    """Scan a project directory and return a StackProfile."""

    def __init__(self, directory: str | Path) -> None:
        self.root = Path(directory).resolve()

    def scan(self) -> StackProfile:
        profile = StackProfile()

        readme = self.root / "README.md"
        if readme.exists():
            profile.project_description = readme.read_text(encoding="utf-8")[:500]

        claude_md = self.root / "CLAUDE.md"
        if claude_md.exists():
            profile.existing_claude_md = claude_md.read_text(encoding="utf-8")

        # Detection order: JS → Go → Rust → Python (requirements) → Python (pyproject)
        # → Maven → Gradle → .NET
        if (self.root / "package.json").exists():
            self._scan_package_json(profile)
        elif (self.root / "go.mod").exists():
            self._scan_go_mod(profile)
        elif (self.root / "Cargo.toml").exists():
            self._scan_cargo_toml(profile)
        elif (self.root / "requirements.txt").exists():
            self._scan_requirements_txt(profile)
        elif (self.root / "pyproject.toml").exists():
            self._scan_pyproject_toml(profile)
        elif (self.root / "pom.xml").exists():
            self._scan_pom_xml(profile)
        elif (self.root / "build.gradle").exists():
            self._scan_build_gradle(profile)
        else:
            csproj_files = list(self.root.glob("*.csproj"))
            if csproj_files:
                self._scan_csproj(profile, csproj_files[0])

        return profile

    # ------------------------------------------------------------------ #
    # Private parsers                                                      #
    # ------------------------------------------------------------------ #

    def _scan_package_json(self, profile: StackProfile) -> None:
        profile.language = "JavaScript"
        profile.package_manager = "npm"

        try:
            data = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        all_deps: dict[str, str] = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        profile.key_dependencies = list(all_deps.keys())

        for dep_key, label in _JS_FRAMEWORK_PRIORITY:
            if dep_key in all_deps:
                profile.framework = label
                break

        if "typescript" in all_deps:
            profile.language = "TypeScript"

        if (self.root / "yarn.lock").exists():
            profile.package_manager = "yarn"
        elif (self.root / "pnpm-lock.yaml").exists():
            profile.package_manager = "pnpm"

        node_version: str = data.get("engines", {}).get("node", "")
        if node_version:
            profile.key_dependencies.insert(0, f"node:{node_version}")

    def _scan_requirements_txt(self, profile: StackProfile) -> None:
        profile.language = "Python"
        profile.package_manager = "pip"

        lines = (self.root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        packages: list[str] = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith(("#", "-")):
                continue
            name = re.split(r"[>=<!~\[ @]", line)[0].strip().lower()
            if name:
                packages.append(name)

        profile.key_dependencies = packages

        for key, label in _PYTHON_FRAMEWORK_PRIORITY:
            if key in packages:
                profile.framework = label
                break

    def _scan_pyproject_toml(self, profile: StackProfile) -> None:
        profile.language = "Python"

        text = (self.root / "pyproject.toml").read_text(encoding="utf-8")
        packages = _extract_pyproject_deps(text)
        profile.key_dependencies = packages

        for key, label in _PYTHON_FRAMEWORK_PRIORITY:
            if key in packages:
                profile.framework = label
                break

        # Detect package manager / build backend
        if "[tool.poetry]" in text:
            profile.package_manager = "poetry"
        else:
            # Any PEP 517/518 pyproject.toml (hatchling, flit, pdm, setuptools, …)
            # is installed with `pip install -e .` not `-r requirements.txt`
            profile.package_manager = "pyproject"

    def _scan_go_mod(self, profile: StackProfile) -> None:
        profile.language = "Go"
        profile.package_manager = "go modules"

        text = (self.root / "go.mod").read_text(encoding="utf-8")

        module_match = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
        if module_match:
            profile.framework = module_match.group(1)

        requires = re.findall(r"^\s+(\S+)\s+v[\w.\-+]+", text, re.MULTILINE)
        profile.key_dependencies = requires

    def _scan_cargo_toml(self, profile: StackProfile) -> None:
        profile.language = "Rust"
        profile.package_manager = "cargo"

        text = (self.root / "Cargo.toml").read_text(encoding="utf-8")

        name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if name_match:
            profile.framework = name_match.group(1)

        in_deps = False
        deps: list[str] = []
        for line in text.splitlines():
            if re.match(r"^\[dependencies\]", line):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("["):
                    break
                dep_match = re.match(r"^\s*([\w-]+)\s*=", line)
                if dep_match:
                    deps.append(dep_match.group(1))

        profile.key_dependencies = deps

    def _scan_pom_xml(self, profile: StackProfile) -> None:
        profile.language = "Java"
        profile.package_manager = "maven"

        try:
            tree = ET.parse(self.root / "pom.xml")
            root_el = tree.getroot()
        except (ET.ParseError, OSError):
            return

        ns = {"m": "http://maven.apache.org/POM/4.0.0"}

        def _find(tag: str) -> Optional[ET.Element]:
            el = root_el.find(f"m:{tag}", ns)
            return el if el is not None else root_el.find(tag)

        artifact = _find("artifactId")
        if artifact is not None and artifact.text:
            profile.framework = artifact.text

        deps_el = root_el.find("m:dependencies", ns) or root_el.find("dependencies")
        if deps_el is not None:
            for dep in deps_el:
                group_el = dep.find("m:groupId", ns) or dep.find("groupId")
                art_el = dep.find("m:artifactId", ns) or dep.find("artifactId")
                if art_el is not None and art_el.text:
                    profile.key_dependencies.append(art_el.text)
                    if group_el is not None and "springframework" in (group_el.text or ""):
                        profile.framework = "Spring Boot"

    def _scan_build_gradle(self, profile: StackProfile) -> None:
        profile.language = "Java"
        profile.package_manager = "gradle"

        text = (self.root / "build.gradle").read_text(encoding="utf-8")

        if "kotlin" in text.lower():
            profile.language = "Kotlin"

        if "springframework.boot" in text:
            profile.framework = "Spring Boot"

        deps = re.findall(r'implementation\s+["\']([^"\']+)["\']', text)
        profile.key_dependencies = deps

    def _scan_csproj(self, profile: StackProfile, path: Path) -> None:
        profile.language = "C#"
        profile.package_manager = "nuget"

        try:
            tree = ET.parse(path)
            root_el = tree.getroot()
        except (ET.ParseError, OSError):
            return

        tf = root_el.find(".//TargetFramework")
        if tf is not None and tf.text:
            profile.framework = tf.text

        for ref in root_el.findall(".//PackageReference"):
            include = ref.get("Include")
            if include:
                profile.key_dependencies.append(include)


def _extract_pyproject_deps(text: str) -> list[str]:
    """Extract package names from pyproject.toml using targeted regex.

    Handles two common formats:
      - PEP 621: dependencies = ["flask>=2.0", ...]
      - Poetry:  [tool.poetry.dependencies] / flask = "^2.0"
    """
    packages: list[str] = []

    # PEP 621 / Hatch / Flit: dependencies array
    array_match = re.search(
        r"^\s*dependencies\s*=\s*\[(.*?)\]",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if array_match:
        for match in re.finditer(r'["\']([a-zA-Z][a-zA-Z0-9_-]*)', array_match.group(1)):
            packages.append(match.group(1).lower())

    # Poetry: bare key = "version" under [tool.poetry.dependencies]
    in_poetry_deps = False
    for line in text.splitlines():
        if re.match(r"^\[tool\.poetry\.dependencies\]", line):
            in_poetry_deps = True
            continue
        if in_poetry_deps:
            if line.startswith("["):
                in_poetry_deps = False
                continue
            m = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*=", line)
            if m:
                name = m.group(1).lower()
                if name != "python":
                    packages.append(name)

    return packages
