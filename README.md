# ctx — Persistent memory for Claude Code. One command, automatic.

[![PyPI version](https://img.shields.io/pypi/v/ctxcli.svg)](https://pypi.org/project/ctxcli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Works with Claude Code](https://img.shields.io/badge/Works%20with-Claude%20Code-orange.svg)](https://claude.ai/code)
[![Works with Cursor](https://img.shields.io/badge/Works%20with-Cursor-purple.svg)](https://cursor.sh)
[![Works with Windsurf](https://img.shields.io/badge/Works%20with-Windsurf-blue.svg)](https://codeium.com/windsurf)
[![Works with any CLAUDE.md reader](https://img.shields.io/badge/Works%20with-any%20AI%20coding%20tool-green.svg)](#works-with)

---

## The problem

Every Claude Code session starts from zero. You re-explain your stack, your conventions, your patterns — every time.

> "This is a Next.js app."
> "We use pytest."
> "Snake_case for Python, camelCase for JS."
> "Check the Dockerfile."

You've said it a hundred times. Claude has forgotten it a hundred times.

---

## The solution

`ctx learn` scans your codebase and writes a `CLAUDE.md` that Claude Code reads **automatically** at the start of every session.

![ctx learn demo](demo.gif)

One command. Done. Claude remembers.

---

## Install

```bash
pip install ctxcli
```

---

## Usage

### `ctx learn` — scan your project and generate CLAUDE.md

```
$ ctx learn
⠋ Scanning stack...
⠙ Extracting conventions...
⠹ Generating CLAUDE.md...
✓ CLAUDE.md generated — 31 lines written
Open Claude Code in this folder and it will read this automatically.
```

Generated `CLAUDE.md`:

```markdown
# Project Overview

**Language:** TypeScript
**Framework:** Next.js

A production e-commerce platform with server-side rendering.

# Tech Stack

**Language:** TypeScript
**Framework:** Next.js
**Package Manager:** npm
**Key Dependencies:** next, react, react-dom, tailwindcss, prisma

# Conventions

**Naming Style:** camelCase
**Import Style:** absolute
**Test Framework:** jest

# Development Commands

**Install:** `npm install`
**Test:** `npm test`
**Run:** `npm run dev`

# Key Files

- `package.json`
- `Dockerfile`
- `.github/workflows/`
```

---

### `ctx show` — pretty-print the current context

```
$ ctx show
╭──────────────── Project Overview ─────────────────╮
│ Language: TypeScript                               │
│ Framework: Next.js                                 │
╰────────────────────────────────────────────────────╯
╭────────────────── Tech Stack ──────────────────────╮
│ Package Manager: npm                               │
│ Key Dependencies: next, react, prisma, tailwindcss │
╰────────────────────────────────────────────────────╯
```

---

### `ctx update` — re-scan and merge with previous context

```
$ ctx update
⠋ Scanning stack...
⠙ Extracting conventions...
⠹ Generating CLAUDE.md...
✓ CLAUDE.md updated — 38 lines written
Open Claude Code in this folder and it will read this automatically.
```

Previous CLAUDE.md content is preserved under a `# Notes / Previously you knew:` section — nothing is lost.

---

### Flags

```
ctx learn --dry-run      # Preview CLAUDE.md without writing it
ctx learn --verbose      # Show which files were scanned
ctx learn /path/to/project   # Scan a specific directory
```

---

## How it works

- **Scans your project files** — `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `*.csproj`, and more. Detects language, framework, and key dependencies without any configuration.
- **Reads your code conventions** — uses Python's `ast` module for Python files and regex for JS/TS. Detects naming style (snake_case / camelCase / PascalCase), import style, and test framework.
- **Generates a structured `CLAUDE.md`** — seven sections covering stack, structure, conventions, commands, and key files. Always under 150 lines. Never hallucinates — only writes what was actually detected.
- **Claude Code reads it automatically** — place `CLAUDE.md` in your project root and Claude Code picks it up at session start. No plugins, no config, no API keys.

---

## Works with

`CLAUDE.md` is a plain Markdown file read by any AI coding tool that supports project context files:

| Tool | How it reads CLAUDE.md |
|------|----------------------|
| **Claude Code** | Automatically at session start |
| **Cursor** | Via `.cursorrules` or project docs |
| **Windsurf** | Via project context |
| **GitHub Copilot** | Via custom instructions |
| **Any LLM** | Paste into system prompt |

---

## Supported stacks

| Language | Detected from | Frameworks detected |
|----------|--------------|---------------------|
| JavaScript / TypeScript | `package.json` | React, Next.js, Vue, Express, Angular |
| Python | `requirements.txt`, `pyproject.toml` | Django, FastAPI, Flask |
| Go | `go.mod` | (module name) |
| Rust | `Cargo.toml` | (crate name) |
| Java / Kotlin | `pom.xml`, `build.gradle` | Spring Boot |
| C# | `*.csproj` | (target framework) |

---

## License

MIT — see [LICENSE](LICENSE).
