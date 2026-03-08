# CLI Reference

## `pclient-build`

Generate an HTTP client from a Pyramid application's routes.

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
| `--name TEXT` | Yes | Client name (e.g., `payments`). Used to derive the class name (`PaymentsClient`), package name (`payments_client`), request attribute (`request.payments_client`), and settings prefix (`payments.base_url`). |
| `--output PATH` | Yes | Output directory for the generated client package. The package directory is created inside this path (e.g., `--output ./generated/` produces `./generated/payments_client/`). |
| `--include TEXT` | No | Glob pattern to include routes. Only matching paths are generated. Can be specified multiple times. When omitted, all routes are included. |
| `--exclude TEXT` | No | Glob pattern to exclude routes. Matching paths are removed after include filtering. Can be specified multiple times. |
| `--debug` | No | Enable debug logging. Prints each discovered endpoint's method and path. |
| `--version` | No | Show the installed version and exit. |
| `--help` | No | Show the help message and exit. |

### Naming conventions

The `--name` option drives all generated names:

| `--name` value | Class name | Package name | Request attribute | Settings prefix |
|---|---|---|---|---|
| `payments` | `PaymentsClient` | `payments_client` | `request.payments_client` | `payments.base_url` |
| `user-service` | `UserServiceClient` | `user_service_client` | `request.user_service_client` | `user_service.base_url` |
| `catalog` | `CatalogClient` | `catalog_client` | `request.catalog_client` | `catalog.base_url` |

## Examples

### Basic usage

```bash
pclient-build development.ini --name payments --output ./generated/
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
Generated PaymentsClient at ./generated/payments_client
  Class:     PaymentsClient
  Package:   payments_client
  Request:   request.payments_client
  Settings:  payments.base_url
  Endpoints: 5
    GET    /api/v1/charges
    POST   /api/v1/charges
    GET    /api/v1/charges/{id}
    PUT    /api/v1/charges/{id}
    POST   /api/v1/charges/{id}/cancel
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success — client package generated |
| 1 | No endpoints found (check your include/exclude patterns) |
| Non-zero | Bootstrap or generation error (see stderr for details) |
