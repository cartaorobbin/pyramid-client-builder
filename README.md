# pyramid-client-builder

[![PyPI version](https://img.shields.io/pypi/v/pyramid-client-builder.svg)](https://pypi.org/project/pyramid-client-builder/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyramid-client-builder.svg)](https://pypi.org/project/pyramid-client-builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Introspect a [Pyramid](https://trypyramid.com/) application and generate a typed HTTP client package — like [protoc](https://grpc.io/docs/protoc-installation/) for gRPC, but for your Pyramid REST API.

## What it does

`pclient-build` boots your Pyramid app from its INI file, discovers routes and [Cornice](https://cornice.readthedocs.io/) services, and writes a Python client package to disk. The generated client has one method per endpoint with natural names, Marshmallow schema serialization, and a Pyramid `includeme` for easy integration.

```
Pyramid app (INI file)
  → introspect routes, views, schemas
  → generate Python package
  → client.py, schemas.py, ext.py
```

## Quick example

Generate a client from your payments service:

```bash
pclient-build development.ini --name payments --output ./generated/
```

Use the generated client:

```python
from payments_client.client import PaymentsClient

client = PaymentsClient(base_url="http://localhost:6543")

# Methods are named from your URL paths
charges = client.list_charges()
charge = client.get_charge(id=42)
new_charge = client.create_charge(amount=1000, currency="usd")
client.cancel_charge(id=42)

# Versioned APIs get sub-clients
items = client.v1.list_items()
```

## Installation

```bash
pip install pyramid-client-builder
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add pyramid-client-builder
```

## Documentation

Full documentation is available at the [project docs site](https://cartaorobbin.github.io/pyramid-client-builder/), including:

- [Getting Started](https://cartaorobbin.github.io/pyramid-client-builder/getting-started/) — installation and first client
- [CLI Reference](https://cartaorobbin.github.io/pyramid-client-builder/cli-reference/) — all `pclient-build` options
- [Generated Output](https://cartaorobbin.github.io/pyramid-client-builder/generated-output/) — what files are produced
- [Usage Guide](https://cartaorobbin.github.io/pyramid-client-builder/usage/) — standalone and Pyramid integration
- [Features](https://cartaorobbin.github.io/pyramid-client-builder/features/) — naming, schemas, versioning

## Development

```bash
git clone https://github.com/cartaorobbin/pyramid-client-builder.git
cd pyramid-client-builder
uv sync --dev
```

Run tests:

```bash
uv run pytest          # single Python version
uv run tox             # full matrix (3.10–3.13)
```

Lint and format:

```bash
uv run ruff check .
uv run black .
```

Build docs locally:

```bash
uv run mkdocs serve
```

## License

MIT
