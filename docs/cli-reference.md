# CLI Reference

## `pclient-build`

Generate HTTP clients from a Pyramid application's routes. Produces Python (requests + httpx) and Go client variants in a single invocation.

```
pclient-build [OPTIONS] INI_FILE
```

### Arguments

| Argument | Description |
|---|---|
| `INI_FILE` | Path to the PasteDeploy INI configuration file (e.g., `development.ini`). The Pyramid app is bootstrapped from this file. Must exist and be readable. |

### Options

| Option | Required | Description |
|---|---|---|
| `--name TEXT` | Yes | Client name (e.g., `payments`). Used to derive class names, package names, module paths, and settings prefixes. |
| `--output PATH` | Yes | Output directory for the generated client variants. Three subdirectories are created: `python_requests/`, `python_httpx/`, and `go/`. |
| `--include TEXT` | No | Glob pattern to include routes. Only matching paths are generated. Can be specified multiple times. When omitted, all routes are included. |
| `--exclude TEXT` | No | Glob pattern to exclude routes. Matching paths are removed after include filtering. Can be specified multiple times. |
| `--client-version TEXT` | No | Version for the generated client packages. Defaults to `0.1.0`. |
| `--go-module TEXT` | No | Go module path (e.g., `github.com/org/payments-client`). Defaults to `<name>-client`. Used in `go.mod` and version sub-package import paths. |
| `--debug` | No | Enable debug logging. Prints each discovered endpoint's method and path. |
| `--version` | No | Show the installed version and exit. |
| `--help` | No | Show the help message and exit. |

### Naming conventions

The `--name` option drives all generated names:

| `--name` value | Python class | Python package | Go package | Go module |
|---|---|---|---|---|
| `payments` | `PaymentsClient` | `payments_client` | `paymentsclient` | `payments-client` |
| `user-service` | `UserServiceClient` | `user_service_client` | `userserviceclient` | `user-service-client` |
| `catalog` | `CatalogClient` | `catalog_client` | `catalogclient` | `catalog-client` |

### Output structure

A single invocation produces three variant directories:

```
<output>/
  python_requests/     Python client using requests
  python_httpx/        Python client using httpx
  go/                  Go client using net/http
```

## Examples

### Basic usage

```bash
pclient-build development.ini --name payments --output ./generated/
```

### With custom Go module path

```bash
pclient-build development.ini --name payments --output ./generated/ \
    --go-module github.com/myorg/payments-client
```

### Filtered generation

Generate only the v1 API, excluding internal endpoints:

```bash
pclient-build production.ini --name payments --output ./clients/ \
    --include "/api/v1/*" \
    --exclude "/api/v1/internal/*"
```

### Multiple include patterns

```bash
pclient-build development.ini --name payments --output ./generated/ \
    --include "/api/v1/*" \
    --include "/api/v2/*"
```

### Debug mode

See every endpoint that was discovered:

```bash
pclient-build development.ini --name payments --output ./generated/ --debug
```

```
Bootstrapping Pyramid from development.ini
Discovered 5 endpoints
  Generated python_requests/
  Generated python_httpx/
  Generated go/

Generated clients at ./generated/
  Name:      payments
  Variants:  python_requests, python_httpx, go
  Endpoints: 5
  Settings:  payments.base_url
    GET    /api/v1/charges
    POST   /api/v1/charges
    GET    /api/v1/charges/{id}
    PUT    /api/v1/charges/{id}
    POST   /api/v1/charges/{id}/cancel
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — all client variants generated |
| 1 | No endpoints found (check your include/exclude patterns) |
| Non-zero | Bootstrap or generation error (see stderr for details) |
