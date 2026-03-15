"""Git hook generation and management for ctxcli."""
from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

# Embed in every generated hook so we can identify our own files.
HOOK_SIGNATURE = "# installed by ctxcli — https://github.com/gauravchhabra705/contextcli"

_WATCHED_CONFIG_FILES = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
]


def find_ctx_binary() -> str:
    """Resolve the full path to the ctx binary at install time.

    Priority:
      1. ctx found in PATH via shutil.which
      2. <python_bin>/ctx (same venv / prefix as the running interpreter)
      3. Bare "ctx" as last resort (relies on PATH at commit time)
    """
    found = shutil.which("ctx")
    if found:
        return found
    python_bin = Path(sys.executable).parent
    candidate = python_bin / "ctx"
    if candidate.exists():
        return str(candidate)
    return "ctx"


def generate_hook_content(ctx_bin: str) -> str:
    """Return the text of a post-commit shell hook that calls ctx update selectively."""
    watched = " ".join(_WATCHED_CONFIG_FILES)
    # Shell function curly braces must be doubled in an f-string.
    return f"""\
#!/bin/sh
{HOOK_SIGNATURE}

CTX_BIN="{ctx_bin}"

# Returns 0 (true) if this commit warrants a CLAUDE.md refresh.
should_update() {{
    CHANGED=$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null)

    # Watched config files
    for f in {watched}; do
        if echo "$CHANGED" | grep -qx "$f"; then
            return 0
        fi
    done

    # New source files (.py .js .ts .jsx .tsx)
    if echo "$CHANGED" | grep -qE '\\.(py|js|ts|jsx|tsx)$'; then
        return 0
    fi

    # New top-level directory created in this commit
    NEW_TOP=$(git diff-tree --no-commit-id -r --diff-filter=A --name-only HEAD 2>/dev/null | \\
              grep '/' | cut -d/ -f1 | sort -u)
    if [ -n "$NEW_TOP" ]; then
        PREV=$(git ls-tree HEAD^ --name-only 2>/dev/null || echo "")
        for d in $NEW_TOP; do
            if ! echo "$PREV" | grep -qx "$d"; then
                return 0
            fi
        done
    fi

    return 1
}}

if should_update; then
    "$CTX_BIN" update .
fi
"""


def make_executable(path: Path) -> None:
    """Set executable bits on a file (owner, group, other)."""
    current = path.stat().st_mode
    path.chmod(current | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def is_ctxcli_hook(content: str) -> bool:
    """Return True if the hook file was written by ctxcli."""
    return HOOK_SIGNATURE in content
