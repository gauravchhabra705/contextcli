# Contributing to ctxcli

Thanks for your interest. ctxcli is intentionally small — contributions should stay that way.

## Quick start

```bash
git clone https://github.com/gauravchhabra705/contextcli
cd ctxcli
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
```

## What we accept

| Type | Welcome? | Notes |
|------|----------|-------|
| New language detector | Yes | Add to `scanner.py`, add tests |
| New framework detection | Yes | Add to priority list + tests |
| Bug fixes | Yes | Include a failing test that your fix makes pass |
| Performance improvements | Yes | Benchmark before/after |
| New CLI commands | Discuss first | Open an issue |
| Refactoring | No | Keep it lean |

## How to add a new language detector

1. Add a `_scan_<lang>` method to `StackScanner` in `scanner.py`
2. Add the detection trigger to `scan()` (ordered by typical priority)
3. Add `"Language:package_manager"` → key file in `generator.py`
4. Add `"package_manager"` → install command in `generator.py`
5. Add at least 2 tests in `tests/test_scanner.py`

## Code style

- No external dependencies beyond `typer`, `click`, `rich`
- No network calls — pure file I/O only
- Each module stays under 300 lines
- All new code requires tests; coverage must not drop

## Running tests

```bash
make test              # run full suite
pytest tests/test_scanner.py -v   # run one file
pytest -k "django"     # run matching tests
```

## Submitting a PR

1. Fork and create a feature branch: `git checkout -b feat/ruby-support`
2. Write tests first (they should fail)
3. Implement the change (tests should pass)
4. Run `make test` — must be green
5. Open a PR with a clear description of what and why

## Reporting bugs

Open a GitHub issue with:
- The command you ran
- Your OS and Python version (`python --version`)
- The project structure that triggered the bug (anonymised is fine)
- Expected vs actual output
