# Features

## Method naming

The generator interprets your URL path structure to produce natural Python method names. No annotations or configuration needed — names are derived automatically.

### Collection endpoints

Paths ending with a resource name represent collections. GET requests use the `list_` prefix:

| Method | Path | Generated name |
|---|---|---|
| GET | `/api/v1/charges` | `list_charges()` |
| POST | `/api/v1/charges` | `create_charge()` |

### Detail endpoints

Paths ending with a path parameter represent a single resource. Names are singularized:

| Method | Path | Generated name |
|---|---|---|
| GET | `/api/v1/charges/{id}` | `get_charge()` |
| PUT | `/api/v1/charges/{id}` | `update_charge()` |
| DELETE | `/api/v1/charges/{id}` | `delete_charge()` |

### Verb detection

Paths ending with an action word use that verb as the method prefix. The generator uses NLTK WordNet to detect verbs, so `/charges/{id}/cancel` becomes `cancel_charge()` instead of the naive `create_charge_cancel()`:

| Method | Path | Generated name |
|---|---|---|
| POST | `/api/v1/charges/{id}/cancel` | `cancel_charge()` |
| POST | `/api/v1/charges/{id}/refund` | `refund_charge()` |
| POST | `/api/v1/orders/{id}/approve` | `approve_order()` |

### Non-API paths

Routes without a clear resource structure (e.g., `/`, `/health`) fall back to the route name:

| Method | Path | Route name | Generated name |
|---|---|---|---|
| GET | `/` | `home` | `get_home()` |
| GET | `/health` | `health` | `get_health()` |

## Schema renaming

Server-side schemas are named by domain concept (e.g., `ChargeSchema`). In the generated client, schemas are renamed by their **usage role** so consumers can tell what they send from what they receive.

### Role suffixes

| Role | Suffix | Used for |
|---|---|---|
| Request body | `RequestSchema` | Serializing outgoing POST/PUT bodies |
| Response | `ResponseSchema` | Deserializing incoming responses |
| Querystring | `QuerySchema` | Serializing query parameters |
| Error response | `ErrorSchema` | Error response bodies |

### Renaming rules

- Schemas without a role suffix are renamed based on the endpoint path and usage:
    - `ChargeSchema` on `POST /api/v1/charges` (request) → `ChargesRequestSchema`
    - `ChargeSchema` on `GET /api/v1/charges/{id}` (response) → `ChargeResponseSchema`
- Schemas that already have a recognized suffix (`RequestSchema`, `ResponseSchema`, `QuerySchema`, `BodySchema`, `PathSchema`, `ErrorSchema`) are left unchanged.
- If the same schema would get conflicting names from different endpoints, the original name is preserved.

## API versioning

When your endpoints have version prefixes in their paths (e.g., `/api/v1/...`, `/api/v2/...`), the generator produces a versioned output structure.

### How it works

1. The generator detects `v<digits>` segments in endpoint paths
2. Endpoints are grouped by version
3. Each version gets its own subdirectory with a dedicated client and schemas
4. A root client aggregates version sub-clients as properties

### Usage

```python
client = PaymentsClient(base_url="http://localhost:6543")

# Version sub-clients
charges_v1 = client.v1.list_charges()
charges_v2 = client.v2.list_charges()

# Unversioned endpoints stay on the root
health = client.get_health()
```

### Benefits

- Schema names can't conflict across versions (each version has its own `schemas.py`)
- You can evolve your API without breaking the existing generated client
- Auth configuration is shared — set it once on the root client

When no versioned endpoints are detected, the flat output structure is used instead.

## Include / exclude filtering

Control which endpoints are generated using glob patterns:

```bash
# Only include v1 API routes
pclient-build dev.ini --name payments --output ./gen/ \
    --include "/api/v1/*"

# Exclude internal and webhook endpoints
pclient-build dev.ini --name payments --output ./gen/ \
    --exclude "/api/v1/internal/*" \
    --exclude "/api/v1/webhooks/*"

# Combine both — include first, then exclude from the result
pclient-build dev.ini --name payments --output ./gen/ \
    --include "/api/*" \
    --exclude "*/internal/*"
```

Patterns are matched against the endpoint's URL path using Python's `fnmatch` style:

- `*` matches any sequence of characters within a single path segment
- `?` matches any single character
- Multiple `--include` and `--exclude` flags can be specified

When `--include` is used, only matching endpoints are kept. When `--exclude` is used, matching endpoints are removed. If both are specified, include is applied first, then exclude.

## Cornice and pycornmarsh support

The generator works with both Cornice schema patterns:

### Standard Cornice

Schemas declared via the `schema` kwarg on Cornice decorators:

```python
@service.post(schema=ChargeSchema, validators=(colander_body_validator,))
def create_charge(request):
    ...
```

### pycornmarsh

Explicit location-to-schema mapping via `pcm_request` and per-status-code response schemas via `pcm_responses`:

```python
@service.post(
    pcm_request=dict(body=ChargeBodySchema, querystring=ChargeQuerySchema),
    pcm_responses={200: ChargeResponseSchema, 400: ChargeErrorSchema},
)
def create_charge(request):
    ...
```

When both patterns are present, `pcm_request` takes precedence for request schemas, and `pcm_responses` takes precedence for response schemas. This gives you more explicit control over the generated client's types.

## Conditional file generation

The generated output adapts to your API:

- **`schemas.py`** is only created when endpoints have Marshmallow schemas. Plain Pyramid routes without schema declarations still produce a working client — methods return raw `response.json()`.
- **Version subdirectories** only appear when versioned paths are detected.
- **Files that would be empty** are skipped entirely (e.g., a version's `schemas.py` when that version has no schemas).
