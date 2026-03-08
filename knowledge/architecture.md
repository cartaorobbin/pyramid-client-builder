# Architecture

## Overview

Introspect Pyramid views and generate a client for the app. The library inspects a Pyramid application's route and view configuration at runtime, extracts endpoint metadata (paths, methods, parameters), and produces typed client code that can call those endpoints.

## Components

### Models (`pyramid_client_builder.models`)

Data classes that represent the introspected API surface:

- **`ParameterInfo`** — A single parameter (path, query, body) with name, location, type hint, and whether it's required.
- **`EndpointInfo`** — One HTTP method on one path: route name, path pattern, method, description, and a list of `ParameterInfo`.
- **`ClientSpec`** — The full specification for a client: name, list of `EndpointInfo`, and the settings prefix for `base_url`.

### Introspection (`pyramid_client_builder.introspection`)

Boots a Pyramid app from an INI file and reads its route/view registry.

- **`routes.py`** — `discover_routes` walks the Pyramid introspector to extract routes, patterns, HTTP methods, path parameters, and docstrings.
- **`cornice.py`** — `enrich_endpoints_with_cornice` matches discovered endpoints to Cornice services and extracts Marshmallow schema fields (body/querystring) into `ParameterInfo`.
- **`core.py`** — `PyramidIntrospector` orchestrates the full pipeline: bootstrap → discover routes → enrich with Cornice → filter out non-client methods (HEAD, OPTIONS) → return `ClientSpec`.

### Generator (`pyramid_client_builder.generator`)

Turns a `ClientSpec` into Python source files.

- **`naming.py`** — Naming conventions for class, package, method, and attribute names. Uses **NLTK WordNet** to detect verbs at the end of paths so `/charges/{id}/cancel` becomes `cancel_charge` rather than `create_charge_cancel`.
- **`core.py`** — `ClientGenerator` annotates endpoints with method names, renders Jinja2 templates, and writes the output package.
- **`templates/`** — Jinja2 templates:
  - `client.py.j2` — The HTTP client class with one method per endpoint.
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
  → PyramidIntrospector
      ├── discover_routes() → raw EndpointInfo list
      ├── enrich_endpoints_with_cornice() → adds body/querystring params
      └── _drop_non_client_methods() → removes HEAD/OPTIONS
  → ClientSpec
  → ClientGenerator
      ├── _annotate_endpoints() → assigns Python method names (with verb detection)
      └── _render_template() × 3 → writes client.py, ext.py, __init__.py
  → Output package on disk
```

## External Dependencies

| Dependency | Purpose |
|---|---|
| `pyramid` | Bootstrap and introspect the target application |
| `click` | CLI interface |
| `jinja2` | Template rendering for code generation |
| `requests` | HTTP transport in the generated client |
| `nltk` | WordNet verb detection for smarter method naming |
| `setuptools<82` | Provides `pkg_resources` required by Pyramid 2.x |
