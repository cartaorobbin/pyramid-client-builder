.PHONY: lint fix test check

lint:
	uv run ruff check .
	uv run black --check .

fix:
	uv run ruff check . --fix
	uv run black .

test:
	uv run pytest

check: lint test
