# Architecture

## Overview

Introspect Pyramid views and generate a client for the app. The library inspects a Pyramid application's route and view configuration at runtime, extracts endpoint metadata (paths, methods, parameters), and produces typed client code that can call those endpoints. Generates clients for multiple language/transport variants: Python (requests), Python (httpx), and Go.

## Components

### Models

Shared introspection models (`ParameterInfo`, `SchemaFieldInfo`, `SchemaInfo`) are imported directly from `pyramid_introspector`. Client-builder-specific models live in `pyramid_client_builder.models`:

- **`EndpointInfo`** — One HTTP method on one path: route name, path pattern, method, description, list of `ParameterInfo`, optional `request_schema`, `querystring_schema`, `response_schema` (`SchemaInfo` references), and `response_schemas` (dict mapping HTTP status codes to `SchemaInfo`).
- **`ClientSpec`** — The full specification for a client: name, list of `EndpointInfo`, deduplicated list of `SchemaInfo`, and the settings prefix for `base_url`.

### Introspection (`pyramid_client_builder.introspection`)

A thin adapter over `pyramid-introspector` that converts its route/view hierarchy into the flat `EndpointInfo` list the generator expects.

- **`core.py`** — `PyramidIntrospector` delegates to `pyramid_introspector.PyramidIntrospector` to discover routes and views (including Cornice and pycornmarsh metadata via the extension system), then flattens `RouteInfo`/`ViewInfo` into `EndpointInfo`. Post-processing: filter out non-client methods (HEAD, OPTIONS), apply include/exclude glob patterns, deduplicate, and collect unique schemas into a `ClientSpec`.

### Generator (`pyramid_client_builder.generator`)

Turns a `ClientSpec` into client source files for multiple languages.

- **`common.py`** — Language-agnostic shared logic: `group_by_version()` splits endpoints into versioned/unversioned groups, `rename_schemas()` renames generic schema names by role + path, `collect_schemas()` gathers unique schemas, and `iter_schemas()` iterates all schemas on an endpoint. Used by both Python and Go generators.
- **`naming.py`** — Python naming conventions for class, package, method, schema, and attribute names. Uses **NLTK WordNet** to detect verbs at the end of paths so `/charges/{id}/cancel` becomes `cancel_charge` rather than `create_charge_cancel`. Also provides `to_schema_name()` for role-based schema renaming, `needs_schema_rename()` for detecting generic schema names, and `extract_version()` for detecting API version prefixes in paths.
- **`go_naming.py`** — Go naming conventions: `to_go_package_name()` (lowercase, no separators), `to_go_method_name()` (PascalCase, reuses Python naming logic), `to_go_field_name()` (PascalCase for exports), `to_go_type()` (Marshmallow field type to Go type mapping), and `snake_to_camel()`/`snake_to_pascal()` for case conversion.
- **`renderer.py`** — `render_tree()` walks a template directory tree and renders files/directories through Jinja2. Supports an `@each(var)` loop directive in directory names for dynamic repeated directories (e.g., per-version subdirectories). Files that render to whitespace-only are skipped (conditional file generation).
- **`core.py`** — `ClientGenerator` builds a unified context (endpoints, schemas, versions dict), then calls `render_tree()` once with the Python templates. The template tree mirrors the output structure; no explicit per-file wiring needed.
- **`go_core.py`** — `GoClientGenerator` follows the same pattern as `ClientGenerator` but uses Go templates and Go-specific Jinja filters. Produces a Go module with `net/http` standard library client, functional options, struct params for schemas, and JSON struct tags.
- **`templates/`** — Python Jinja2 template tree:
  - `pyproject.toml.j2`, `README.md.j2` — Project packaging files.
  - `{{package_name}}/` — Python package: `__init__.py.j2`, `client.py.j2`, `ext.py.j2`, `schemas.py.j2`.
  - `{{package_name}}/@each(versions)/` — Per-version: `__init__.py.j2`, `client.py.j2`, `schemas.py.j2`.
- **`go_templates/`** — Go Jinja2 template tree:
  - `go.mod.j2`, `README.md.j2` — Module files.
  - `client.go.j2` — Root Client struct with functional options, unversioned methods.
  - `types.go.j2` — Go structs from schemas (conditional, skipped when empty).
  - `@each(versions)/` — Per-version: `client.go.j2` (sub-client), `types.go.j2` (version structs).

### CLI (`pyramid_client_builder.cli`)

A single Click command `pclient-build` that generates all client variants:

```
pclient-build <config.ini> --name <client-name> --output <dir> [--go-module <module>] [--debug]
```

Generates three variant subdirectories under `--output`:
- `python_requests/` — Python client using `requests`
- `python_httpx/` — Python client using `httpx`
- `go/` — Go client using `net/http`

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
  → CLI loops over generators:
      ├── ClientGenerator(http_client="requests")
      │     └── render_tree(templates/, python_requests/, context)
      ├── ClientGenerator(http_client="httpx")
      │     └── render_tree(templates/, python_httpx/, context)
      └── GoClientGenerator
            └── render_tree(go_templates/, go/, context)
  → Output variants on disk
```

## External Dependencies

| Dependency | Purpose |
|---|---|
| `pyramid-introspector[cornice]` | Route/view discovery, Cornice/pycornmarsh schema extraction (brings in `pyramid` and `setuptools` transitively) |
| `click` | CLI interface |
| `jinja2` | Template rendering for code generation |
| `requests` or `httpx` | HTTP transport in the generated Python client (both variants generated) |
| `marshmallow` | Schema-based serialization/deserialization in the generated Python client (when schemas are present) |
| `nltk` | WordNet verb detection for smarter method naming |
| `net/http` (Go stdlib) | HTTP transport in the generated Go client (no external Go dependencies) |
