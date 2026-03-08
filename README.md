# pyramid-client-builder

Introspect Pyramid views and generate a client for the app.

## Installation

```bash
pip install pyramid-client-builder
```

Or with uv:

```bash
uv add pyramid-client-builder
```

## Usage

```python
import pyramid_client_builder
```

## Development

### Setup

```bash
git clone https://github.com/your-org/pyramid-client-builder.git
cd pyramid-client-builder
uv sync --dev
```

### Run tests

```bash
uv run pytest
```

### Lint and format

```bash
uv run ruff check .
uv run black .
```

### Build docs

```bash
uv run mkdocs serve
```

## License

MIT
