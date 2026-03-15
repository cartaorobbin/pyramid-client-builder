# Generated Output

This page explains the structure and contents of the client packages produced by `pclient-build`.

## Multi-variant output

A single invocation generates three client variants, each in its own subdirectory:

```
generated/
├── python_requests/         Python client using requests
│   └── payments_client/
├── python_httpx/            Python client using httpx
│   └── payments_client/
└── go/                      Go client using net/http
    └── payments-client/
```

---

## Python output

Both Python variants (`python_requests/` and `python_httpx/`) produce the same package structure. The only difference is the HTTP transport library used.

### Flat layout (no versioning)

When your API paths don't contain version prefixes, the generator produces a flat package:

```
payments_client/
├── __init__.py      # Package init with imports
├── client.py        # HTTP client class
├── ext.py           # Pyramid includeme extension
└── schemas.py       # Marshmallow schemas (only if schemas exist)
```

### Versioned layout

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

### Python file-by-file breakdown

#### `client.py`

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

#### `schemas.py`

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

#### `ext.py`

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

#### `__init__.py`

Package init that imports the client class and schemas for convenience:

```python
from payments_client.client import PaymentsClient
from payments_client.schemas import ChargesRequestSchema, ChargeResponseSchema
```

#### Version sub-client (`v1/client.py`)

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

Authentication is configured once on the root client and shared across all versions.

---

## Go output

The Go variant produces an idiomatic Go module with structs, functional options, and standard library HTTP.

### Flat layout (no versioning)

```
payments-client/
├── go.mod           # Go module definition
├── README.md        # Usage documentation
├── client.go        # Client struct, NewClient, methods
└── types.go         # Go structs from Marshmallow schemas (if any)
```

### Versioned layout

```
payments-client/
├── go.mod
├── README.md
├── client.go        # Root client with version sub-client fields
├── types.go         # Structs for unversioned schemas (if any)
├── v1/
│   ├── client.go    # V1Client with v1 methods
│   └── types.go     # Structs for v1 schemas
└── v2/
    ├── client.go    # V2Client with v2 methods
    └── types.go     # Structs for v2 schemas
```

### Go file-by-file breakdown

#### `go.mod`

Declares the Go module with no external dependencies:

```
module payments-client

go 1.21
```

#### `client.go`

The main client struct with functional options:

```go
package paymentsclient

type Client struct {
    BaseURL    string
    AuthToken  string
    Timeout    int
    HTTPClient *http.Client
    V1         *v1.V1Client
}

func NewClient(baseURL string, opts ...Option) *Client {
    c := &Client{
        BaseURL:    strings.TrimRight(baseURL, "/"),
        Timeout:    30,
        HTTPClient: &http.Client{},
    }
    for _, opt := range opts {
        opt(c)
    }
    c.HTTPClient.Timeout = time.Duration(c.Timeout) * time.Second
    c.V1 = v1.NewV1Client(c.BaseURL, c.AuthToken, c.HTTPClient)
    return c
}

type Option func(*Client)

func WithAuthToken(token string) Option {
    return func(c *Client) { c.AuthToken = token }
}

func WithTimeout(seconds int) Option {
    return func(c *Client) { c.Timeout = seconds }
}
```

Key behaviors:

- **Path parameters** become individual `string` arguments
- **Request body** is accepted as a pointer to a request struct (e.g., `*CreateChargeRequest`)
- **Responses** return `(*ChargeResponseSchema, error)` when a schema exists, or `(map[string]interface{}, error)` otherwise
- **Errors** are returned as Go's `(T, error)` pattern — non-2xx status codes produce an error

#### `types.go`

Go structs generated from Marshmallow schemas:

```go
package paymentsclient

type ChargesRequestSchema struct {
    Amount   int    `json:"amount"`
    Currency string `json:"currency"`
}

type ChargeResponseSchema struct {
    ID       *int    `json:"id,omitempty"`
    Amount   *int    `json:"amount,omitempty"`
    Currency *string `json:"currency,omitempty"`
    Status   *string `json:"status,omitempty"`
}
```

Type mapping from Marshmallow to Go:

| Marshmallow field | Go type (required) | Go type (optional) |
|---|---|---|
| `fields.String` | `string` | `*string` |
| `fields.Integer` | `int` | `*int` |
| `fields.Float` | `float64` | `*float64` |
| `fields.Boolean` | `bool` | `*bool` |
| `fields.DateTime` | `time.Time` | `*time.Time` |
| `fields.List` | `[]interface{}` | `[]interface{}` |
| `fields.Dict` | `map[string]interface{}` | `map[string]interface{}` |
| Other | `interface{}` | `interface{}` |

Optional fields use pointer types with `omitempty` JSON tags, following Go convention for distinguishing zero values from absent values.

#### Version sub-client (`v1/client.go`)

```go
package v1

type V1Client struct {
    baseURL    string
    authToken  string
    httpClient *http.Client
}

func NewV1Client(baseURL, authToken string, httpClient *http.Client) *V1Client {
    return &V1Client{
        baseURL:    baseURL,
        authToken:  authToken,
        httpClient: httpClient,
    }
}

func (c *V1Client) ListCharges(req *ChargesQuerySchema) (*ChargesResponseSchema, error) {
    // ...
}
```

Authentication is configured once on the root client and passed down to version sub-clients.

---

## Conditional generation

- **`schemas.py` / `types.go`** are only generated when endpoints have Marshmallow schemas. Plain Pyramid routes without Cornice/Marshmallow still produce a working client — Python methods return raw `response.json()`, Go methods return `map[string]interface{}`.
- **Version subdirectories** are only created when versioned paths are detected. If all your paths are flat, you get the simple flat layout.
