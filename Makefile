.PHONY: test install publish build clean

# Run the full test suite
test:
	.venv/bin/pytest --tb=short -q

# Install in editable mode (creates venv if missing)
install:
	python3 -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q -e .
	.venv/bin/pip install -q pytest
	@echo "✓ Installed. Activate with: source .venv/bin/activate"

# Build source distribution and wheel
build:
	.venv/bin/pip install -q build
	.venv/bin/python -m build
	@echo "✓ Built: dist/"
	@ls dist/

# Publish to PyPI (requires PYPI_TOKEN env var or ~/.pypirc)
publish: build
	.venv/bin/pip install -q twine
	.venv/bin/twine upload dist/*

# Remove build artefacts
clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"
