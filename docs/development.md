# Development

## Setup

Clone the repository and install dependencies:

```bash
git clone https://github.com/cartaorobbin/pyramid-client-builder.git
cd pyramid-client-builder
uv sync --dev
```

This installs all development dependencies: ruff, black, pytest, mkdocs-material, tox, and test utilities.

## Running tests

### Single Python version

```bash
uv run pytest
```

### Full matrix (Python 3.10–3.13)

```bash
uv run tox
```

Tox uses `tox-uv` for fast environment creation and runs tests across all supported Python versions.

### Verbose output

```bash
uv run pytest -v
```

## Linting and formatting

### Check for issues

```bash
uv run ruff check .
```

### Auto-fix lint issues

```bash
uv run ruff check . --fix
```

### Format code

```bash
uv run black .
```

### Check formatting without changes

```bash
uv run black --check .
```

## Documentation

### Serve locally

```bash
uv run mkdocs serve
```

Opens a local preview at `http://127.0.0.1:8000/` with live reload.

### Build static site

```bash
uv run mkdocs build --strict
```

The `--strict` flag treats warnings as errors, ensuring all links and references are valid.

## Project structure

```
pyramid-client-builder/
├── src/pyramid_client_builder/    # Source code
│   ├── cli.py                     # pclient-build Click command
│   ├── introspection.py           # Adapter over pyramid-introspector
│   ├── models.py                  # EndpointInfo, ClientSpec
│   └── generator/                 # Code generation
│       ├── core.py                # ClientGenerator orchestration
│       ├── naming.py              # Method and schema naming
│       ├── renderer.py            # Template tree renderer
│       └── templates/             # Jinja2 output templates
├── tests/
│   ├── example_app/               # Test Pyramid app (Cornice + Marshmallow)
│   ├── test_cli.py
│   ├── test_generator.py
│   └── test_introspection.py
├── docs/                          # MkDocs documentation (this site)
└── knowledge/                     # AI context (architecture, decisions, concepts)
```

## Architecture overview

The codebase follows a three-layer pipeline:

```
Introspection → ClientSpec → Code Generation
```

- **Introspection** — boots the Pyramid app and reads its route registry via `pyramid-introspector`. The local adapter flattens routes/views into `EndpointInfo` objects and applies filtering.
- **ClientSpec** — a plain data structure containing the client name, endpoints, and schemas. Bridges introspection and generation.
- **Code Generation** — renders Jinja2 templates from a template tree that mirrors the output directory structure. The `@each(var)` directive handles dynamic directories (e.g., per-version subdirs).

For detailed architecture documentation, see `knowledge/architecture.md` in the repository.
