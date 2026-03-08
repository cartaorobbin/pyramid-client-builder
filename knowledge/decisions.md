# Architectural Decisions

Record of key technical and architectural decisions for this project.

## Template

Use this format when adding a new decision:

### YYYY-MM-DD — Decision Title

**Status**: Accepted | Superseded | Deprecated

**Context**: What is the issue or situation that motivates this decision?

**Decision**: What is the change that we're proposing or have agreed to?

**Consequences**: What are the trade-offs and results of this decision?

---

## Decisions

### 2026-03-07 — Initial project setup

**Status**: Accepted

**Context**: Starting a new project that needs a solid foundation.

**Decision**: Using uv with src layout, ruff + black for linting/formatting, pytest for testing, and MkDocs for documentation.

**Consequences**: Consistent project structure that follows Python best practices. All team members and AI assistants can rely on the same conventions.

---

### 2026-03-07 — Build-time CLI code generation

**Status**: Accepted

**Context**: Need to decide how the client gets created — at import time (dynamic proxy), or ahead of time (code generation).

**Decision**: Generate concrete Python source files via a CLI command (`pclient-build`), similar to how `protoc` generates gRPC stubs.

**Consequences**: Generated code is inspectable, type-checkable, and debuggable. No runtime magic. Requires re-running the CLI when routes change.

---

### 2026-03-07 — HTTP transport via `requests`

**Status**: Accepted

**Context**: The generated client needs a transport layer to call the remote Pyramid app.

**Decision**: Use the `requests` library for synchronous HTTP calls. Each generated method maps 1:1 to an HTTP request.

**Consequences**: Simple, well-understood transport. Async support (`httpx`) can be added later as an alternative template.

---

### 2026-03-07 — Introspection via Pyramid's introspector + Cornice

**Status**: Accepted

**Context**: Need to discover routes, methods, and parameter schemas from an existing Pyramid app.

**Decision**: Bootstrap the Pyramid app from its INI file, then query the built-in introspector for routes/views. For Cornice apps, also inspect service registrations and extract Marshmallow schema fields.

**Consequences**: Works with any Pyramid app. Cornice/Marshmallow enrichment is optional — plain Pyramid routes still generate usable clients with path parameters.

---

### 2026-03-07 — Single Click command (not a group)

**Status**: Accepted

**Context**: The CLI could be a Click group with subcommands or a single command.

**Decision**: Start with a single `pclient-build` command. Defer subcommands until more features warrant them.

**Consequences**: Simpler UX and implementation. Easy to extend later.

---

### 2026-03-07 — NLTK WordNet for verb detection in method naming

**Status**: Accepted

**Context**: REST API paths like `/charges/{id}/cancel` produce awkward method names (`create_charge_cancel`) when the HTTP method is naively used as the prefix. Detecting that `cancel` is a verb allows generating `cancel_charge` instead.

**Decision**: Use NLTK's WordNet corpus to check if the last path segment is a verb. The corpus is downloaded on first use if not already present. NLTK is acceptable as a dependency because `pyramid-client-builder` is a dev/build-time tool, not a runtime dependency.

**Consequences**: Method names are more natural and idiomatic. Adds ~1.5 MB dependency. False positives are possible for words that are both verbs and nouns (e.g., "charge"), but the heuristic only triggers when the word appears after a resource segment, reducing false matches.

---

### 2026-03-07 — Method naming heuristics

**Status**: Accepted

**Context**: Different URL patterns need different naming strategies.

**Decision**: Three-tier naming strategy:
1. **Verb paths** (`/resource/{id}/action`) → `action_resource` (verb detected via WordNet)
2. **API paths** (`/api/v1/resource` or `/api/v1/resource/{id}`) → `list_resources` (collection GET), `get_resource` / `create_resource` / etc. (detail/mutate)
3. **Non-API paths** (`/`, `/health`) → route-name fallback: `get_home`, `get_health`

**Consequences**: Produces clean, predictable method names for REST APIs while handling edge cases gracefully.

---

### 2026-03-08 — Schema-based client serialization

**Status**: Accepted

**Context**: The introspection pipeline was decomposing Marshmallow schemas into individual `ParameterInfo` objects with string type hints via a `MARSHMALLOW_TYPE_MAP`. The generated client sent raw dicts and received raw `response.json()`, losing the schema's validation, type coercion, and field-level constraints.

**Decision**: Generate copies of the server's Marshmallow schemas into the client package. The introspection captures full schema metadata (`SchemaInfo` / `SchemaFieldInfo`) alongside the existing `ParameterInfo`. The generator renders a `schemas.py` file with Marshmallow schema classes. The client uses `schema.dump()` to serialize outgoing requests and `schema.load()` to deserialize incoming responses — the mirror of what the server does. Method signatures keep individual parameters for good DX; schemas are used internally. Only schemas that are explicitly declared are generated — no guessing. Response schemas are discovered via a `response_schema` attribute on the view callable.

**Consequences**: Client and server share the same data contract through generated schema copies. The generated client now depends on `marshmallow` in addition to `requests`. Endpoints without schemas gracefully fall back to raw dicts.

---

### 2026-03-08 — Composite schema unwrapping

**Status**: Accepted

**Context**: Cornice supports two schema patterns: (1) **flat** schemas where all fields are direct parameters and the location is determined by the validator function, and (2) **composite** schemas where top-level fields are named by location (`body`, `querystring`, `path`) and each is a `Nested` field wrapping the actual parameter schema. The payments app uses pattern (2). The introspection was treating `body`, `querystring`, and `path` as literal parameter names of type `dict`, producing `def create_charge(self, body: dict)` instead of expanding individual fields.

**Decision**: Detect composite schemas by checking if any top-level field is a `Nested` type whose name matches a known location (`body`, `querystring`, `path`). When detected, unwrap the inner schemas: extract their fields as individual parameters with the correct location, and capture the inner schema class (not the wrapper) as the `SchemaInfo` for code generation. Flat schemas continue to work as before.

**Consequences**: Both Cornice schema patterns now produce correct individual-parameter signatures and schema-based serialization. The composite wrapper schema is never generated — only the inner schemas appear in the client's `schemas.py`.

---

### 2026-03-08 — pycornmarsh metadata support

**Status**: Accepted

**Context**: Some Pyramid/Cornice apps use [pycornmarsh](https://github.com/debonzi/pycornmarsh) to attach explicit schema metadata to Cornice service decorators via custom Pyramid view predicates. Instead of inferring schemas from the `schema` kwarg and validator functions, pycornmarsh uses `pcm_request=dict(body=BodySchema, querystring=QSSchema)` for explicit location-to-schema mapping and `pcm_responses={200: SuccessSchema, 400: ErrorSchema}` for per-status-code response schemas.

**Decision**: When `pcm_request` or `pcm_responses` are present in a Cornice service definition's args dict, use them as the primary schema source — they take precedence over the `schema` kwarg (for requests) and the `view_callable.response_schema` attribute (for responses). No dependency on pycornmarsh itself is required; the metadata is read directly from Cornice's `service.definitions`. A new `response_schemas: dict[int, SchemaInfo]` field on `EndpointInfo` stores all per-status-code response schemas; `response_schema` continues to hold the success (2xx) schema for backward compatibility. Error schemas from `response_schemas` are collected into `ClientSpec.schemas` and generated in the client's `schemas.py`.

**Consequences**: Apps using pycornmarsh now generate correct clients with explicit schema mappings. The `pcm_request` body schema may differ from the Cornice `schema` kwarg (the latter is for validation, the former for documentation), and the more explicit `pcm_request` is preferred. Multiple response schemas per status code are captured, enabling future error handling features in the generated client.

---

### 2026-03-08 — Delegate introspection to pyramid-introspector

**Status**: Accepted (supersedes "Introspection via Pyramid's introspector + Cornice")

**Context**: The introspection module (`routes.py`, `cornice.py`, `core.py`) contained ~550 lines of route discovery, Cornice service matching, Marshmallow schema extraction, composite schema unwrapping, and pycornmarsh metadata handling. This logic is general-purpose and useful beyond client generation. It was extracted into a standalone library, `pyramid-introspector`, which provides the same capabilities via an extension system.

**Decision**: Replace the `introspection/routes.py` and `introspection/cornice.py` modules with `pyramid-introspector[cornice]` as a dependency. The local `introspection/core.py` becomes a thin adapter that calls `pyramid_introspector.PyramidIntrospector.introspect()`, flattens the `RouteInfo`/`ViewInfo` hierarchy into flat `EndpointInfo` objects, and applies client-builder-specific post-processing (method filtering, glob patterns, deduplication, schema collection). Shared models (`ParameterInfo`, `SchemaFieldInfo`, `SchemaInfo`) are imported directly from `pyramid_introspector` — no local copies or re-exports.

**Consequences**: ~550 lines of introspection code removed. Route discovery, Cornice enrichment, and the extension system are now `pyramid-introspector`'s responsibility. This project focuses on what only it does: converting introspected metadata into a generated client package. Low-level introspection tests were removed (owned by the upstream library); integration tests that verify the full pipeline remain.
