# Generated Output

This page explains the structure and contents of the client package produced by `pclient-build`.

## Flat output (no versioning)

When your API paths don't contain version prefixes, the generator produces a flat package:

```
payments_client/
├── __init__.py      # Package init with imports
├── client.py        # HTTP client class
├── ext.py           # Pyramid includeme extension
└── schemas.py       # Marshmallow schemas (only if schemas exist)
```

## Versioned output

When your endpoints have version prefixes (e.g., `/api/v1/charges`, `/api/v2/charges`), the generator creates per-version subdirectories:

```
payments_client/
├── __init__.py
├── client.py        # Root client with version sub-client properties
├── ext.py
├── schemas.py       # Schemas for unversioned endpoints (if any)
├── v1/
│   ├── __init__.py
│   ├── client.py    # V1Client with v1 endpoints
│   └── schemas.py   # Schemas for v1 endpoints
└── v2/
    ├── __init__.py
    ├── client.py    # V2Client with v2 endpoints
    └── schemas.py   # Schemas for v2 endpoints
```

## File-by-file breakdown

### `client.py`

The main client class. Each endpoint becomes a method:

```python
class PaymentsClient:
    """Auto-generated HTTP client for the payments Pyramid application."""

    def __init__(self, base_url, auth_token=None, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if auth_token:
            self.session.headers["Authorization"] = f"Bearer {auth_token}"
        # Version sub-clients (only in versioned output)
        self.v1 = V1Client(self.base_url, self.session, self.timeout)

    def list_charges(self):
        """GET /api/v1/charges"""
        url = f"{self.base_url}/api/v1/charges"
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return ChargesResponseSchema().load(response.json())

    def create_charge(self, amount, currency):
        """POST /api/v1/charges"""
        url = f"{self.base_url}/api/v1/charges"
        body = ChargesRequestSchema().dump(
            {"amount": amount, "currency": currency}
        )
        response = self.session.post(url, json=body, timeout=self.timeout)
        response.raise_for_status()
        return ChargeResponseSchema().load(response.json())
```

Key behaviors:

- **Path parameters** become required positional arguments
- **Body parameters** become keyword arguments, serialized through the request schema's `dump()`
- **Querystring parameters** become optional keyword arguments
- **Responses** are deserialized through the response schema's `load()`, or returned as raw `response.json()` when no schema exists
- **Errors** raise via `response.raise_for_status()` (standard `requests` behavior)

### `schemas.py`

Copies of your server's Marshmallow schemas, renamed by role:

```python
from marshmallow import Schema, fields

class ChargesRequestSchema(Schema):
    amount = fields.Integer(required=True)
    currency = fields.String(required=True)

class ChargeResponseSchema(Schema):
    id = fields.Integer()
    amount = fields.Integer()
    currency = fields.String()
    status = fields.String()
```

This file is only generated when your endpoints have Marshmallow schemas attached. See [Features > Schema renaming](features.md#schema-renaming) for how names are derived.

### `ext.py`

A Pyramid extension that registers the client on the request:

```python
def includeme(config):
    def payments_client(request):
        return PaymentsClient(
            base_url=request.registry.settings["payments.base_url"],
            auth_token=request.registry.settings.get("payments.auth_token"),
        )

    config.add_request_method(
        payments_client, name="payments_client", reify=True
    )
```

The client is created once per request (`reify=True`) and reads its configuration from the app's INI settings.

### `__init__.py`

Package init that imports the client class and schemas for convenience:

```python
from payments_client.client import PaymentsClient
from payments_client.schemas import ChargesRequestSchema, ChargeResponseSchema
```

### Version sub-client (`v1/client.py`)

In versioned output, each version gets its own client class that shares the parent's session:

```python
class V1Client:
    """Auto-generated HTTP client for payments API v1."""

    def __init__(self, base_url, session, timeout):
        self.base_url = base_url
        self.session = session
        self.timeout = timeout

    def list_charges(self):
        """GET /api/v1/charges"""
        # ...
```

This means authentication is configured once on the root client and shared across all versions.

## Conditional generation

- **`schemas.py`** is only generated when endpoints have Marshmallow schemas. Plain Pyramid routes without Cornice/Marshmallow still produce a working client — methods just return raw `response.json()`.
- **Version subdirectories** are only created when versioned paths are detected. If all your paths are flat, you get the simple flat layout.
