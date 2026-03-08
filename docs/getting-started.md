# Getting Started

## Prerequisites

- Python 3.10+
- A Pyramid application with a PasteDeploy INI file (e.g., `development.ini`)
- The Pyramid app must be importable (its package installed or on `PYTHONPATH`)

## Installation

=== "pip"

    ```bash
    pip install pyramid-client-builder
    ```

=== "uv"

    ```bash
    uv add pyramid-client-builder
    ```

`pyramid-client-builder` is a **build-time tool** — add it as a dev dependency, not a runtime one. The generated client package has its own dependencies (`requests`, and `marshmallow` when schemas are present).

## Your first client

### 1. Run the generator

Point `pclient-build` at your Pyramid app's INI file:

```bash
pclient-build development.ini --name payments --output ./generated/
```

This will:

1. Boot your Pyramid app from the INI file
2. Discover all routes and Cornice services
3. Generate a `payments_client` package in `./generated/`

You'll see output like:

```
Bootstrapping Pyramid from development.ini
Discovered 12 endpoints
Generated PaymentsClient at ./generated/payments_client
  Class:     PaymentsClient
  Package:   payments_client
  Request:   request.payments_client
  Settings:  payments.base_url
  Endpoints: 12
```

### 2. Use the generated client

The generated package is a regular Python package. You can use it directly:

```python
from payments_client.client import PaymentsClient

client = PaymentsClient(
    base_url="http://localhost:6543",
    auth_token="your-token",
)

# List all charges
charges = client.list_charges()

# Get a specific charge
charge = client.get_charge(id=42)

# Create a charge — body parameters become keyword arguments
new_charge = client.create_charge(amount=1000, currency="usd")
```

### 3. Integrate with Pyramid (optional)

If the consuming app is also a Pyramid application, you can register the client on the request object:

Add to your INI file:

```ini
payments.base_url = http://payments-service:6543
payments.auth_token = secret
```

Include the extension in your Pyramid configuration:

```python
config.include("payments_client.ext")
```

Then use it in any view:

```python
def my_view(request):
    charges = request.payments_client.list_charges()
    return {"charges": charges}
```

## Filtering endpoints

You don't have to generate a client for every route. Use `--include` and `--exclude` to select what you need:

```bash
# Only v1 API endpoints
pclient-build development.ini --name payments --output ./generated/ \
    --include "/api/v1/*"

# Everything except webhooks
pclient-build development.ini --name payments --output ./generated/ \
    --exclude "/api/v1/webhooks/*"

# Combine both — patterns can be repeated
pclient-build development.ini --name payments --output ./generated/ \
    --include "/api/v1/*" --include "/api/v2/*" \
    --exclude "*/internal/*"
```

## Next steps

- [CLI Reference](cli-reference.md) — all `pclient-build` options in detail
- [Generated Output](generated-output.md) — understand what files are produced
- [Usage Guide](usage.md) — method signatures, schema handling, error patterns
- [Features](features.md) — method naming, versioning, schema renaming
