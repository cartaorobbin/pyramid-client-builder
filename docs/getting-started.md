# Getting Started

## Prerequisites

- Python 3.10+
- A Pyramid application with a PasteDeploy INI file (e.g., `development.ini`)
- The Pyramid app must be importable (its package installed or on `PYTHONPATH`)
- (Optional) Go 1.21+ if you want to use the generated Go client

## Installation

=== "pip"

    ```bash
    pip install pyramid-client-builder
    ```

=== "uv"

    ```bash
    uv add pyramid-client-builder
    ```

`pyramid-client-builder` is a **build-time tool** — add it as a dev dependency, not a runtime one. The generated Python client packages have their own dependencies (`requests` or `httpx`, and `marshmallow` when schemas are present). The generated Go client uses only the standard library.

## Your first client

### 1. Run the generator

Point `pclient-build` at your Pyramid app's INI file:

```bash
pclient-build development.ini --name payments --output ./generated/
```

This will:

1. Boot your Pyramid app from the INI file
2. Discover all routes and Cornice services
3. Generate three client variants in `./generated/`

You'll see output like:

```
Bootstrapping Pyramid from development.ini
Discovered 12 endpoints
  Generated python_requests/
  Generated python_httpx/
  Generated go/

Generated clients at ./generated/
  Name:      payments
  Variants:  python_requests, python_httpx, go
  Endpoints: 12
  Settings:  payments.base_url
```

The output directory will contain:

```
generated/
├── python_requests/payments_client/
├── python_httpx/payments_client/
└── go/payments-client/
```

### 2. Use the Python client

The generated Python package is a regular Python package. Pick the variant for your HTTP transport preference:

```python
# From the requests variant
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

### 3. Use the Go client

Copy or reference the generated Go module in your Go project:

```go
import paymentsclient "payments-client"

func main() {
    client := paymentsclient.NewClient(
        "http://localhost:6543",
        paymentsclient.WithAuthToken("your-token"),
    )

    charges, err := client.V1.ListCharges(nil)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(charges)
}
```

For a custom Go module path, use `--go-module`:

```bash
pclient-build development.ini --name payments --output ./generated/ \
    --go-module github.com/myorg/payments-client
```

### 4. Integrate with Pyramid (optional)

If the consuming app is also a Pyramid application, you can register the Python client on the request object:

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
