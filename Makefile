.PHONY: check
check:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check .
	uv run --frozen mypy app
	uv run --frozen pytest
	uv lock --check
	uv run --frozen python -m scripts.schema --check
	uv run --frozen python -m compliance.validate
