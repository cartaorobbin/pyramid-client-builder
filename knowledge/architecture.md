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

- **`naming.py`** — Naming conventions for class, package, method, and attribute names. Uses **NLTK WordNet** to detect verbs at the end of paths so `/charges/{id}/cancel` becomes `cancel_charge` rather than `create_charge_cancel`.
- **`core.py`** — `ClientGenerator` annotates endpoints with method names, renders Jinja2 templates, and writes the output package.
- **`templates/`** — Jinja2 templates:
  - `schemas.py.j2` — Generated Marshmallow schema classes (only rendered when schemas exist).
  - `client.py.j2` — The HTTP client class with one method per endpoint. Uses `schema.dump()` for request serialization and `schema.load()` for response deserialization when schemas are available.
  - `ext.py.j2` — Pyramid `includeme` that registers the client on the request.
  - `__init__.py.j2` — Package init with imports.

### CLI (`pyramid_client_builder.cli`)

A single Click command `pclient-build` that wires everything together:

```
pclient-build <config.ini> --name <client-name> --output <dir> [--debug]
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
      ├── _annotate_endpoints() → assigns Python method names (with verb detection)
      └── _render_template() × 4 → writes schemas.py, client.py, ext.py, __init__.py
  → Output package on disk
```

## External Dependencies

| Dependency | Purpose |
|---|---|
| `pyramid-introspector[cornice]` | Route/view discovery, Cornice/pycornmarsh schema extraction (brings in `pyramid` and `setuptools` transitively) |
| `click` | CLI interface |
| `jinja2` | Template rendering for code generation |
| `requests` | HTTP transport in the generated client |
| `marshmallow` | Schema-based serialization/deserialization in the generated client (when schemas are present) |
| `nltk` | WordNet verb detection for smarter method naming |
