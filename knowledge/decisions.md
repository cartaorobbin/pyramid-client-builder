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

---

### 2026-03-08 — Role-based schema renaming

**Status**: Accepted

**Context**: Server-side schemas often have generic names like `ChargeSchema` that don't communicate whether they're used for requests, responses, or querystrings. In the generated client, `ChargeSchema` is ambiguous — the consumer doesn't know if it's what they send or what they receive.

**Decision**: The generator renames schemas based on their usage role and the endpoint's URL path. Schemas whose names don't already end with a recognized role suffix (`RequestSchema`, `ResponseSchema`, `QuerySchema`, `BodySchema`, `PathSchema`, `ErrorSchema`) are renamed to `{Resource}{Role}Schema`, where the resource name is derived from the endpoint's path segments (PascalCase, stripped of API prefixes and path parameters). For example, `ChargeSchema` used as `request_schema` on `POST /api/v1/charges` becomes `ChargesRequestSchema`. Schemas that already have a clear role suffix are left unchanged. If the same schema would get conflicting names from different endpoints, the original name is preserved.

**Consequences**: Generated schema names clearly communicate their role in the client. Consumers can distinguish request schemas from response schemas at a glance. The renaming is deterministic and predictable. Schemas with explicit role naming on the server are unaffected.

---

### 2026-03-08 — Versioned client output directories

**Status**: Accepted

**Context**: Many Pyramid/Cornice APIs version their endpoints via URL prefixes (e.g., `/api/v1/charges`, `/api/v2/charges`). The flat generated client put all endpoints and schemas in a single `client.py` and `schemas.py`, making it hard to organize multi-version APIs and causing potential schema name conflicts across versions.

**Decision**: When the generator detects versioned endpoints (paths containing a `v<digits>` segment), it creates per-version subdirectories (`v1/`, `v2/`) each with their own `client.py` and `schemas.py`. A root client class aggregates version sub-clients as properties (e.g., `client.v1.list_charges()`). Version sub-clients receive the parent's `requests.Session`, so auth configuration is shared. Non-versioned endpoints (`/`, `/health`) remain as methods on the root client. When no versioned endpoints exist, the flat structure is preserved for backward compatibility.

**Consequences**: Multi-version APIs produce well-organized output with clear separation. Schema names can't conflict across versions since each version has its own `schemas.py`. The root client provides a clean DX: `client.v1.list_charges()`. Backward compatible — plain Pyramid apps without version prefixes generate the same flat output as before.

---

### 2026-03-08 — Tox for multi-version testing and Python >= 3.10

**Status**: Accepted

**Context**: The project declared `requires-python = ">=3.11"` but used no 3.11-specific features. There was no way to verify compatibility across Python versions locally or in CI — the single CI job ran only the default Python.

**Decision**: Lower the minimum Python version to 3.10. Add tox (with `tox-uv` for fast uv-backed environments) to run tests and linting across Python 3.10, 3.11, 3.12, and 3.13. The CI workflow uses a matrix strategy with tox, replacing the single lint-and-test job with separate lint and test jobs. Tox uses `uv-venv-lock-runner` to install from the existing `uv.lock`.

**Consequences**: The project is tested against four Python versions both locally (`tox`) and in CI. Regressions on older or newer Pythons are caught early. The `tox-uv` plugin keeps environment creation fast by reusing uv. Developers can run the full matrix locally with a single `tox` command.

---

### 2026-03-08 — Cookiecutter-style template tree rendering with @each loop directive

**Status**: Accepted

**Context**: The generator used explicit `_render_template()` calls for every output file, with separate `_generate_flat` and `_generate_versioned` methods that manually created directories, built per-file contexts, and called the render method. Adding a new file to the generated output required changes in three places: (1) create the Jinja2 template, (2) add a `_render_template()` call in Python, (3) pass the right context. The versioned layout required a Python `for` loop over versions, and conditional files (like `schemas.py` only when schemas exist) were handled by Python `if` statements.

**Decision**: Replace the explicit file-wiring approach with a cookiecutter-inspired template tree renderer. A new `render_tree()` function in `generator/renderer.py` walks a template directory tree that mirrors the output structure, rendering file names and contents through Jinja2. Files that render to whitespace-only are skipped (handling conditional generation). A custom `@each(var)` directive in directory names handles dynamic directory loops: `@each(versions)/` iterates over a context dict, creating one subdirectory per key with merged context. A single template tree handles both flat and versioned layouts — when `versions` is an empty dict, the `@each` loop creates nothing.

**Consequences**: Adding a new file to the generated output = drop a `.j2` file in the template tree (no Python changes). The template directory visually documents the output structure. `core.py` is simplified: `_generate_flat`, `_generate_versioned`, and `_render_template` are replaced by one `render_tree()` call with a unified context. The `@each()` convention is project-specific and new contributors need to learn it. The merged `client.py.j2` uses `{% if versions %}` conditionals to handle both layouts.

---

### 2026-03-08 — GitHub release tag as authoritative package version

**Status**: Accepted

**Context**: The package version was hardcoded in both `pyproject.toml` and `version.py`. When a GitHub release tag (e.g., `v0.5.4`) didn't match the source version (e.g., `0.5.3`), the CI publish job built a wheel with the stale version and PyPI rejected the upload because that version already existed.

**Decision**: Make `version.py` the single source of truth for the local version using hatchling's `path` version source (`[tool.hatch.version] path = "src/pyramid_client_builder/version.py"`). Remove the static `version` from `pyproject.toml` in favor of `dynamic = ["version"]`. In the CI publish job, override `version.py` with the version extracted from the GitHub release tag (`v0.5.4` → `0.5.4`) before building. Developers still bump `version.py` locally during development.

**Consequences**: The published package version always matches the GitHub release tag, eliminating version mismatch errors. The version lives in one file locally instead of two. The CI override is a simple `echo` command — no new build plugins or dependencies needed. Developers must remember to bump `version.py` during development, but forgetting is harmless since CI overrides it at publish time.

---

### 2026-03-08 — Generated client as installable Python package

**Status**: Accepted

**Context**: The generated client output was just a Python package directory with source files (`__init__.py`, `client.py`, `ext.py`, `schemas.py`, versioned subdirectories). It could not be installed via `pip install` or published to PyPI because it lacked `pyproject.toml` and other packaging metadata. Users had to manually add packaging files after every regeneration.

**Decision**: Restructure the Jinja2 template tree so `render_tree` outputs a complete project directory, not just the Python package. A `{{package_name}}/` directory template wraps the existing package files, and project-level files (`pyproject.toml.j2`, `README.md.j2`) sit at the template root. The generated `pyproject.toml` uses hatchling as the build backend, declares `requests` as a core dependency, `marshmallow` conditionally (only when schemas exist), and `pyramid` as an optional extra (for `ext.py`). A new `--client-version` CLI option (default `0.1.0`) sets the package version. The `ClientGenerator` accepts a `version` parameter and includes `project_name`, `client_version`, and `has_schemas` in the template context.

**Consequences**: The generated output is immediately installable (`pip install ./generated/`) and publishable to PyPI. No manual packaging steps needed after regeneration. The `--client-version` flag lets build pipelines control the version. Backward compatible — `generate()` still returns the package directory path, all existing tests pass unchanged. The template tree restructure maintains the "template mirrors output" design philosophy.

---

### 2026-03-15 — Configurable HTTP client backend (requests/httpx)

**Status**: Accepted (extends "HTTP transport via `requests`")

**Context**: The generated client hardcoded `requests` as the HTTP transport. Some consuming projects already use `httpx` and prefer not to add `requests` as a dependency. Additionally, `httpx` provides a natural path to async support in the future.

**Decision**: Add a `--http-client` CLI option with choices `requests` (default) and `httpx`. The `ClientGenerator` accepts an `http_client` parameter and passes it into the Jinja2 template context. Templates use `{% if http_client == "httpx" %}` conditionals to switch between `import requests` / `requests.Session()` and `import httpx` / `httpx.Client()`. The generated `pyproject.toml` declares the matching dependency (`requests>=2.28` or `httpx>=0.24`). Only synchronous httpx is supported in this iteration — `httpx.Client` is a sync drop-in for `requests.Session` with an identical method API (`.get()`, `.post()`, `.headers`, `response.raise_for_status()`, `response.json()`).

**Consequences**: Users can choose their preferred HTTP library at generation time. Default behavior is unchanged (requests). The Jinja-conditional approach keeps a single template tree — no duplication. Async httpx (`httpx.AsyncClient`) can be added later as a third option. The builder itself does not depend on either library at runtime; they are only dependencies of the generated client.

---

### 2026-03-15 — Pre-commit hooks, Makefile, and agent quality gate

**Status**: Accepted

**Context**: CI caught a black formatting issue on PR #11 that could have been caught locally. There was no pre-commit hook, no convenient `make` targets, and no agent rule to enforce checks before creating PRs.

**Decision**: Add three layers of quality assurance: (1) a `.pre-commit-config.yaml` with ruff (auto-fix) and black hooks that run on every commit, (2) a `Makefile` with `lint`, `fix`, `test`, and `check` targets (`make check` = lint + test, the full gate), and (3) a Cursor agent rule (`.cursor/rules/pre-pr-check.mdc`) that requires running `make check` before creating any PR. The dev-workflow skill is updated with a "Quality Gate" step between execution and PR creation.

**Consequences**: Formatting and lint issues are caught at commit time (pre-commit) or at PR time (agent rule + `make check`). Developers get convenient shortcuts (`make fix`, `make check`). The agent cannot skip checks before PRs. Three layers provide defense in depth: pre-commit for devs, `make check` for the agent, and CI as the final backstop.

---

### 2026-03-15 — Go client generation and multi-variant output

**Status**: Accepted (extends "Build-time CLI code generation", supersedes "HTTP transport via `requests`" option behavior)

**Context**: The generated client only supported Python. Users wanted Go clients from the same introspected Pyramid APIs. Additionally, generating both `requests` and `httpx` Python variants required separate CLI invocations with `--http-client`.

**Decision**: Add Go client generation using the same `ClientSpec` pipeline. Restructure the CLI to generate all language/transport variants (python_requests, python_httpx, go) in a single invocation, each into its own subdirectory under `--output`. Remove the `--http-client` option (both Python variants are always generated). Add `--go-module` for customizing the Go module path. Shared logic (version grouping, schema renaming, schema collecting) is extracted from `core.py` into `generator/common.py` for reuse by both `ClientGenerator` and `GoClientGenerator`. Go templates use idiomatic patterns: functional options, `net/http` standard library, struct params for schemas, `json` struct tags, and `(T, error)` returns.

**Consequences**: A single `pclient-build` invocation now produces three client variants. The Go client uses idiomatic Go patterns (functional options, struct params, `net/http`). The shared `common.py` module makes adding new target languages straightforward. The `--http-client` option is removed — this is a breaking CLI change but the project is pre-1.0. Go struct types are generated from Marshmallow `SchemaInfo` with proper JSON tags and Go type mapping.

---

### 2026-03-16 — Flutter/Dart client generation

**Status**: Accepted (extends "Go client generation and multi-variant output")

**Context**: The project generated clients for Python and Go. Users building mobile apps with Flutter/Dart needed a Dart client from the same introspected Pyramid APIs. The existing architecture (common.py, render_tree, template tree convention) was designed to make adding new target languages straightforward.

**Decision**: Add Flutter/Dart client generation using the same `ClientSpec` pipeline. `FlutterClientGenerator` in `flutter_core.py` follows the same pattern as `GoClientGenerator`. Dart naming conventions live in `flutter_naming.py` (reuses `to_method_name()` from the shared naming module, then converts to camelCase). The generated Dart package uses the `http` library (standard Dart HTTP), async methods returning `Future<T>`, and hand-written `fromJson`/`toJson` for model classes (no `json_serializable` or `freezed` dependency). The template tree renderer was enhanced to also render Jinja expressions in file names (not just directory names), enabling `{{package_name}}.dart.j2` for the barrel export. A `--flutter-package` CLI option allows customizing the Dart package name.

**Consequences**: A single `pclient-build` invocation now produces four client variants (python_requests, python_httpx, go, flutter). The Dart client uses idiomatic Dart patterns (async/await, nullable types, factory constructors, named parameters). The `http` package is the only external dependency — no build-runner required. The renderer enhancement (file name rendering) is backward compatible since no existing Go/Python template file names contained Jinja expressions.

---

### 2026-03-23 — Variant-suffixed PyPI project names for Python clients

**Status**: Accepted (extends "Configurable HTTP client backend")

**Context**: Both generated Python clients (`python_requests` and `python_httpx`) produced a `pyproject.toml` with the same `name` field (e.g., `name = "payments-client"`). This made it impossible to publish both variants to PyPI as separate packages.

**Decision**: Append the HTTP client variant as a suffix to the PyPI project name. `to_project_name()` accepts an optional `variant` parameter: `to_project_name("payments", variant="requests")` returns `"payments-client-requests"`, and `to_project_name("payments", variant="httpx")` returns `"payments-client-httpx"`. `ClientGenerator` passes its `http_client` value as the variant. The importable package name (`payments_client`), class name (`PaymentsClient`), and Pyramid request attribute (`payments_client`) remain unchanged — only the PyPI distribution name differs.

**Consequences**: Both Python client variants can be published to PyPI as separate packages. Consumers install with `pip install payments-client-requests` or `pip install payments-client-httpx` but import with the same `import payments_client`. The two packages cannot coexist in the same environment (same import name), which is intentional — you choose one transport. Calling `to_project_name()` without a variant still returns the base name (`payments-client`) for backward compatibility.

---

### 2026-04-01 — Callable token provider for dynamic authentication

**Status**: Accepted

**Context**: Generated clients accepted only a static `auth_token` string, set once at construction time. This made it impossible to implement token refresh or validation logic before each request — a common need in production systems with expiring JWTs or service-to-service auth.

**Decision**: Add callable/dynamic token provider support alongside the existing static token, as two independent first-class features. The provider takes precedence over the static token when both are set.

- **Python**: `auth_token` param accepts `str` or `Callable[[], str]`. A `_apply_auth()` method resolves the token via `callable()` check before each request. Version sub-clients receive `auth_token` and have their own `_apply_auth()`.
- **Go**: New `authTokenFunc func() string` field alongside existing `authToken string`. New `WithAuthTokenFunc(fn func() string)` functional option. `do()` checks `authTokenFunc` first, falls back to `authToken`. Sub-clients receive both fields.
- **Flutter/Dart**: New `authTokenProvider` parameter (`String Function()?`) alongside existing `authToken` (`String?`). `_headers` getter checks provider first, falls back to static token. Sub-clients receive both.

**Consequences**: All generated clients now support dynamic token resolution without breaking existing static-token usage. The Python approach uses duck typing (`callable()`) so a single parameter serves both use cases. Go and Dart use explicit separate fields/parameters for type safety. The Pyramid `ext.py` template is unchanged — it passes a string from settings, which works as before.

---

### 2026-04-01 — Ship custom Marshmallow fields with the generated Python client

**Status**: Accepted

**Context**: When a server-side Marshmallow schema uses a custom field subclass (e.g., `class CurrencyField(ma.fields.String)`), the introspector reports `field_type = "CurrencyField"`. The Python template generates `ma.fields.CurrencyField(...)` which crashes at runtime because `CurrencyField` is not in the standard `marshmallow.fields` namespace. Go and Dart handle this gracefully via their type maps with fallback to generic types (`interface{}` / `dynamic`), but Python has no fallback.

**Decision**: Detect custom fields during introspection and generate minimal replicas in a `fields.py` module shipped with the Python client. The detection walks the live schema classes from Cornice/pycornmarsh args (`view.extra["cornice_args"]`), checks each field against the standard `marshmallow.fields` set, and resolves the base Marshmallow type via MRO. A `CustomFieldInfo` dataclass (class name + base type) is stored on `ClientSpec`. The generator renders a `fields.py.j2` template with stub classes, and `schemas.py.j2` imports custom fields from the local `fields.py` module rather than `ma.fields`. Only affects the Python generator.

**Consequences**: Custom Marshmallow fields no longer crash the generated Python client. The generated `fields.py` contains minimal stubs (`pass` body) that preserve the class name and base type. Custom `_serialize`/`_deserialize` logic is not reproduced — for fields with complex serialization, users can manually edit the generated `fields.py`. This limitation can be addressed in the future by a `marshmallow-introspector` package that captures field source code.

---

### 2026-04-01 — Fix marshmallow field generation bugs (List, Nested, bare Field)

**Status**: Accepted

**Context**: Generated Python clients fail to import when schemas contain `List` or `Nested` marshmallow fields. `List.__init__()` requires a positional `cls_or_instance` argument and `Nested.__init__()` requires a positional `nested` schema argument. The `SchemaFieldInfo` dataclass (from `pyramid-introspector`) only carries `name`, `field_type`, `required`, and `metadata` — no inner-field or nested-schema references. Additionally, custom fields whose MRO only reaches `ma.fields.Field` generate empty stubs with no serialization logic.

**Decision**: Four fixes:
1. `fields.py.j2` generates conditional `__init__` overrides for custom fields with `List` or `Nested` base types, providing safe defaults (`ma.fields.String()` and `ma.Schema` respectively).
2. `_field_kwargs_filter` in `core.py` prepends `ma.fields.String()` as the default inner type for `List` schema fields.
3. Both `schemas.py.j2` templates fall back to `ma.fields.Dict` for `Nested` schema fields, since the nested schema reference is unavailable.
4. `_resolve_base_marshmallow_type` returns `"String"` instead of `"Field"` when the MRO walk reaches the base `Field` class, so generated stubs provide at least basic string serialization.

**Consequences**: Generated Python clients import without errors. `Nested` fields lose their nested-schema validation (degraded to `Dict`), and `List` fields assume string inner type. Both are safe defaults given the metadata available. Custom fields extending bare `Field` now serialize as strings, which matches the common case (CNPJ, CPF, phone validators). When `pyramid-introspector` gains inner/nested metadata, the generator can emit precise types.

---

### 2026-03-28 — Variant selection via --skip and --only

**Status**: Accepted (extends "Go client generation and multi-variant output")

**Context**: The CLI always generated all four client variants (python_requests, python_httpx, go, flutter) with no way to opt out. Some projects have no use for certain variants — for example, a backend-only service has no need for a Flutter client, or a mobile team only needs the Dart output. Generating unnecessary variants wastes time and clutters the output directory.

**Decision**: Add two mutually exclusive, repeatable CLI options: `--skip <variant>` to exclude specific variants and `--only <variant>` to generate only the specified variants. Valid variant names match the output directory names: `python_requests`, `python_httpx`, `go`, `flutter`. When neither option is given, all variants are generated (backward compatible). Using both `--skip` and `--only` in the same invocation is a `UsageError`. Skipping all variants is also an error. Invalid variant names are rejected by Click's `Choice` type with a helpful error message. The `ALL_VARIANTS` tuple is defined as a module-level constant for reuse.

**Consequences**: Users can tailor output to their needs without post-generation cleanup. The default behavior is unchanged — existing scripts and workflows are unaffected. The two options cover both mental models: "give me everything except X" (`--skip`) and "give me only X" (`--only`). The mutual exclusion constraint keeps semantics unambiguous.

---

### 2026-04-02 — Collection endpoint paginated response deserialization

**Status**: Accepted

**Context**: When a collection endpoint (e.g., `GET /api/v1/persons`) declares a `response_schema` describing a single item (e.g., `PersonSchema`), the API returns a paginated envelope `{"results": [...]}`. The generated client was deserializing the entire envelope as the item schema, causing marshmallow validation errors in Python and silent data loss in Go/Flutter.

**Decision**: Add collection endpoint detection and fix response deserialization across all four generated client variants. A new `is_collection_endpoint()` function in `naming.py` reuses the existing `to_method_name()` logic — if the method name starts with `list_`, the endpoint is a collection. Each generator sets `endpoint.is_collection` during annotation. Templates branch on this flag: Python uses `Schema(many=True).load(response.json()["results"])`, Go decodes into an anonymous envelope struct with a `Results []T` field, and Flutter maps over `data['results']` with `fromJson`. Return types change accordingly: Go returns `[]T` instead of `*T`, Flutter returns `List<T>` instead of `T`. The `"results"` key is hardcoded as the pagination envelope key, matching the common Pyramid/Cornice convention.

**Consequences**: Generated clients now correctly deserialize paginated list responses. Detail endpoints are unaffected. The `"results"` key is hardcoded — servers using a different envelope key (e.g., `"data"`, `"items"`) would need manual adjustment in the generated code or a future CLI option for configurability. The collection detection is consistent with method naming: if the method is named `list_*`, it deserializes as a list.

---

### 2026-04-02 — Use enriched SchemaFieldInfo from pyramid-introspector 0.3.0

**Status**: Accepted (fixes "Fix marshmallow field generation bugs")

**Context**: Generated Python marshmallow schemas had two bugs. (1) `Nested` fields were degraded to `ma.fields.Dict()` and `List` fields defaulted to `ma.fields.List(ma.fields.String())` because `SchemaFieldInfo` lacked nested schema references and the `many` flag. When the server schema used `Nested(PhoneSchema, many=True)` or `List(Nested(PhoneSchema))`, the generated client couldn't deserialize the response. (2) Nullable fields (where `allow_none=True` on the server) were generated without `allow_none=True`, causing marshmallow to reject `null` values from the API.

**Decision**: Upgrade to `pyramid-introspector>=0.3.0`, which adds three new fields to `SchemaFieldInfo`: `allow_none` (bool), `many` (bool), and `nested_schema` (str | None). It also adds `SchemaInfo.nested_schemas` for recursively discovered nested schemas. The generator now uses these fields: `_field_kwargs_filter` emits the correct first positional argument (schema name for Nested, `Nested(SchemaName)` for List-of-Nested) and adds `allow_none=True` when set. Both `schemas.py.j2` templates branch on `field.many` and `field.nested_schema` to select the correct outer type (`List`, `Nested`, or `Dict` fallback). Schema collection in both `introspection.py` and `generator/common.py` recursively flattens `nested_schemas` so all referenced schemas are generated.

**Consequences**: Generated Python clients correctly deserialize nested objects, lists of nested objects, and nullable fields. Fallback behavior is preserved: `Nested` without a schema reference still degrades to `Dict`, and `List` without a nested reference still defaults to `List(String())`. Go and Flutter generators are unaffected (they already use permissive generic types). The minimum `pyramid-introspector` version is now 0.3.0.

---

### 2026-04-07 — Verb-detection guard: only when path ends with the verb

**Status**: Accepted (refines "NLTK WordNet for verb detection in method naming")

**Context**: The verb-detection heuristic in `to_method_name` checked whether the last *segment* (after stripping path parameters) was a WordNet verb. This caused false positives for resource names that happen to also be English verbs — e.g., "parts" (to part ways), "orders" (to order), "returns" (to return). For `/api/v1/workspaces/parts/{uuid:.*}`, `_path_segments` stripped `{uuid}`, making "parts" the last segment. WordNet flagged it as a verb, producing `parts_workspace` and `parts_workspace_1` instead of `get_workspaces_part` and `delete_workspaces_part`.

**Decision**: Add a structural guard to the verb-detection condition: `not _ends_with_param(path)`. The verb-action pattern (e.g., `/charges/{id}/cancel` → `cancel_charge`) always has the verb as the **last segment of the URL itself**, not just the last segment after stripping params. When the URL ends with a path parameter, the preceding segments are resource names — not verbs.

**Consequences**: Resource names that are also English verbs are no longer misidentified as verb actions when they precede a path parameter. All existing verb-action patterns continue to work because their verbs are genuinely the last URL segment. The fix is a single added condition, using the existing `_ends_with_param` function.
