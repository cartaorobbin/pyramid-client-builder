# Architecture

## Overview

Introspect Pyramid views and generate a client for the app. The library inspects a Pyramid application's route and view configuration at runtime, extracts endpoint metadata (paths, methods, parameters), and produces typed client code that can call those endpoints.

## Components

### Models

Shared introspection models (`ParameterInfo`, `SchemaFieldInfo`, `SchemaInfo`) are imported directly from `pyramid_introspector`. Client-builder-specific models live in `pyramid_client_builder.models`:

- **`EndpointInfo`** — One HTTP method on one path: route name, path pattern, method, description, list of `ParameterInfo`, optional `request_schema`, `querystring_schema`, `response_schema` (`SchemaInfo` references), and `response_schemas` (dict mapping HTTP status codes to `SchemaInfo`).
- **`ClientSpec`** — The full specification for a client: name, list of `EndpointInfo`, deduplicated list of `SchemaInfo`, and the settings prefix for `base_url`.

### Introspection (`pyramid_client_builder.introspection`)

A thin adapter over `pyramid-introspector` that converts its route/view hierarchy into the flat `EndpointInfo` list the generator expects.

- **`core.py`** — `PyramidIntrospector` delegates to `pyramid_introspector.PyramidIntrospector` to discover routes and views (including Cornice and pycornmarsh metadata via the extension system), then flattens `RouteInfo`/`ViewInfo` into `EndpointInfo`. Post-processing: filter out non-client methods (HEAD, OPTIONS), apply include/exclude glob patterns, deduplicate, and collect unique schemas into a `ClientSpec`.

### Generator (`pyramid_client_builder.generator`)

Turns a `ClientSpec` into Python source files.

- **`naming.py`** — Naming conventions for class, package, method, schema, and attribute names. Uses **NLTK WordNet** to detect verbs at the end of paths so `/charges/{id}/cancel` becomes `cancel_charge` rather than `create_charge_cancel`. Also provides `to_schema_name()` for role-based schema renaming, `needs_schema_rename()` for detecting generic schema names, and `extract_version()` for detecting API version prefixes in paths.
- **`renderer.py`** — `render_tree()` walks a template directory tree and renders files/directories through Jinja2. Supports an `@each(var)` loop directive in directory names for dynamic repeated directories (e.g., per-version subdirectories). Files that render to whitespace-only are skipped (conditional file generation).
- **`core.py`** — `ClientGenerator` builds a unified context (endpoints, schemas, versions dict), then calls `render_tree()` once. The template tree mirrors the output structure; no explicit per-file wiring needed.
- **`templates/`** — Jinja2 template tree that mirrors the output directory structure:
  - `__init__.py.j2` — Package init with imports. Uses `{% if versions %}` and `{% if schemas %}` for conditional content.
  - `client.py.j2` — Unified HTTP client class. Handles both flat (all endpoints) and versioned (root client with version sub-client properties + unversioned endpoints) via `{% for version in versions %}` conditionals.
  - `ext.py.j2` — Pyramid `includeme` that registers the client on the request.
  - `schemas.py.j2` — Marshmallow schema classes. Wrapped in `{% if schemas %}` guard; skipped when no schemas exist.
  - `@each(versions)/` — Loop directory: one subdirectory per API version. Contains `__init__.py.j2`, `client.py.j2` (version sub-client), and `schemas.py.j2` (version schemas).

### CLI (`pyramid_client_builder.cli`)

A single Click command `pclient-build` that wires everything together:

```
pclient-build <config.ini> --name <client-name> --output <dir> [--http-client requests|httpx] [--debug]
```

## Data Flow

```
INI file
  → pyramid.paster.bootstrap (boots the WSGI app)
  → PyramidIntrospector (adapter)
      ├── pyramid_introspector.PyramidIntrospector.introspect()
      │     → RouteInfo/ViewInfo list (with Cornice/pycornmarsh extensions)
      ├── _routes_to_endpoints() → flat EndpointInfo list
      ├── _drop_non_client_methods() → removes HEAD/OPTIONS
      ├── _filter_endpoints() → include/exclude glob patterns
      ├── _deduplicate() → first occurrence per path+method
      └── _collect_schemas() → unique schemas
  → ClientSpec (endpoints + deduplicated schemas)
  → ClientGenerator
      ├── _group_by_version() → splits endpoints into versioned/unversioned
      ├── _rename_schemas() → renames generic schema names by role + path
      ├── _annotate_endpoints() → assigns Python method names (with verb detection)
      └── render_tree(templates/, package_dir, context)
            ├── Root templates → __init__.py, client.py, ext.py, schemas.py (if schemas)
            └── @each(versions)/ → per version: v{n}/__init__.py, v{n}/client.py, v{n}/schemas.py (if schemas)
  → Output package on disk
```

## External Dependencies

| Dependency | Purpose |
|---|---|
| `pyramid-introspector[cornice]` | Route/view discovery, Cornice/pycornmarsh schema extraction (brings in `pyramid` and `setuptools` transitively) |
| `click` | CLI interface |
| `jinja2` | Template rendering for code generation |
| `requests` or `httpx` | HTTP transport in the generated client (selected via `--http-client`) |
| `marshmallow` | Schema-based serialization/deserialization in the generated client (when schemas are present) |
| `nltk` | WordNet verb detection for smarter method naming |
