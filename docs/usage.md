# Usage Guide

## Python client

### Standalone usage

The generated Python client works as a regular HTTP client with no Pyramid dependency:

```python
from payments_client.client import PaymentsClient

client = PaymentsClient(
    base_url="http://localhost:6543",
    auth_token="your-bearer-token",
    timeout=30,
)
```

#### Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | (required) | Base URL of the target service. Trailing slashes are stripped. |
| `auth_token` | `str` | `None` | Bearer token added to the `Authorization` header. |
| `timeout` | `int` | `30` | Request timeout in seconds. |

#### Session access

The client exposes its HTTP session for advanced configuration:

```python
client = PaymentsClient(base_url="http://localhost:6543")

# Custom headers
client.session.headers["X-Request-ID"] = "abc-123"

# Client certificates
client.session.cert = ("/path/to/client.cert", "/path/to/client.key")

# Retry logic (via requests adapters)
from requests.adapters import HTTPAdapter
adapter = HTTPAdapter(max_retries=3)
client.session.mount("http://", adapter)
```

### Pyramid integration

For Pyramid-to-Pyramid service calls, the generated `ext.py` provides seamless integration.

#### Setup

1. Add settings to your INI file:

    ```ini
    # Required
    payments.base_url = http://payments-service:6543

    # Optional
    payments.auth_token = secret-token
    ```

2. Include the extension in your app configuration:

    ```python
    def main(global_config, **settings):
        config = Configurator(settings=settings)
        config.include("payments_client.ext")
        # ...
        return config.make_wsgi_app()
    ```

3. Use it in views:

    ```python
    def checkout_view(request):
        charge = request.payments_client.create_charge(
            amount=1000, currency="usd"
        )
        return {"charge_id": charge["id"]}
    ```

The client is created once per request (`reify=True`) — multiple accesses within the same request reuse the same instance.

### Python method signatures

Every generated method follows consistent conventions:

#### Path parameters → positional arguments

URL path parameters become required arguments:

```python
# GET /api/v1/charges/{id}
charge = client.get_charge(id=42)

# PUT /api/v1/customers/{customer_id}/cards/{card_id}
card = client.update_card(customer_id=1, card_id=5, last4="1234")
```

#### Body parameters → keyword arguments

Request body fields become keyword arguments:

```python
# POST /api/v1/charges  (body: amount, currency)
charge = client.create_charge(amount=1000, currency="usd")
```

When a request schema exists, the arguments are passed through `schema.dump()` before being sent as JSON. This gives you the same validation and type coercion the server applies on its end.

#### Querystring parameters → optional keyword arguments

Querystring fields become optional keyword arguments:

```python
# GET /api/v1/charges?status=pending&limit=10
charges = client.list_charges(status="pending", limit=10)
```

`None` values are excluded from the query string.

### Python schema serialization

When your endpoints have Marshmallow schemas, the generated client uses them for serialization:

- **Outgoing requests**: `schema.dump()` serializes the body or querystring — the mirror of the server's `schema.load()`
- **Incoming responses**: `schema.load()` deserializes the JSON response — the mirror of the server's `schema.dump()`

```python
# Under the hood, create_charge does:
# 1. body = ChargesRequestSchema().dump({"amount": 1000, "currency": "usd"})
# 2. response = session.post(url, json=body)
# 3. return ChargeResponseSchema().load(response.json())
charge = client.create_charge(amount=1000, currency="usd")
```

Endpoints without schemas fall back to raw dicts — `response.json()` is returned directly.

### Python error handling

The generated client calls `response.raise_for_status()` on every response. This raises `requests.HTTPError` for 4xx/5xx status codes:

```python
from requests.exceptions import HTTPError

try:
    charge = client.get_charge(id=999)
except HTTPError as e:
    print(f"Status: {e.response.status_code}")
    print(f"Body: {e.response.json()}")
```

### Python versioned APIs

When your API has versioned paths, the root client provides sub-client properties:

```python
client = PaymentsClient(base_url="http://localhost:6543")

# Access version-specific endpoints
v1_charges = client.v1.list_charges()
v2_charges = client.v2.list_charges()

# Unversioned endpoints (e.g., /health) stay on the root client
health = client.get_health()
```

All version sub-clients share the root client's session, so authentication and other session configuration is set up once.

---

## Go client

### Standalone usage

The generated Go client uses only the standard library (`net/http` and `encoding/json`):

```go
import paymentsclient "payments-client"

client := paymentsclient.NewClient(
    "http://localhost:6543",
    paymentsclient.WithAuthToken("your-token"),
    paymentsclient.WithTimeout(60),
)
```

#### Constructor

`NewClient(baseURL string, opts ...Option) *Client` creates a client with functional options:

| Option | Description |
|---|---|
| `WithAuthToken(token)` | Set the Bearer token for the `Authorization` header. |
| `WithTimeout(seconds)` | Set the request timeout (default: 30s). |
| `WithHTTPClient(client)` | Provide a custom `*http.Client` for full control. |

### Go method signatures

Methods follow idiomatic Go patterns. When a request schema exists, the method accepts a pointer to a request struct:

#### Path parameters → individual string arguments

```go
// GET /api/v1/charges/{id}
charge, err := client.V1.GetCharge("42")
```

#### Request body → struct pointer

```go
// POST /api/v1/charges
charge, err := client.V1.CreateCharge(&v1.ChargesRequestSchema{
    Amount:   1000,
    Currency: "usd",
})
```

Pass `nil` when you have no body to send (e.g., for GET requests with no query schema).

#### Return types

Methods return a tuple of the response type and an error:

```go
// When a response schema exists:
charge, err := client.V1.GetCharge("42")
// charge is *ChargeResponseSchema

// When no response schema exists:
result, err := client.GetHealth()
// result is map[string]interface{}
```

### Go error handling

Non-2xx responses produce a Go error with the status code:

```go
charge, err := client.V1.GetCharge("999")
if err != nil {
    // err contains the HTTP status code and response body
    log.Printf("request failed: %v", err)
}
```

### Go versioned APIs

When your API has versioned paths, the root client exposes version sub-clients as exported fields:

```go
client := paymentsclient.NewClient("http://localhost:6543")

// Access version-specific endpoints
v1Charges, err := client.V1.ListCharges(nil)
v2Charges, err := client.V2.ListCharges(nil)

// Unversioned endpoints stay on the root client
health, err := client.GetHealth()
```

All version sub-clients share the root client's `*http.Client` and auth configuration.

### Go JSON serialization

Request structs are serialized with `encoding/json` before sending. Response bodies are deserialized into the corresponding struct via `json.NewDecoder`. Struct fields have `json:"name"` tags, and optional fields use `omitempty`:

```go
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

Optional fields use pointer types so that zero values (`0`, `""`, `false`) can be distinguished from absent values.
