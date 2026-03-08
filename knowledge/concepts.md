# Domain Concepts

Key domain concepts, terminology, and mental models for this project.

## Glossary

| Term | Definition |
|---|---|
| **ClientSpec** | The complete metadata describing a generated client: name, endpoints, and configuration prefix. The intermediate representation between introspection and code generation. |
| **EndpointInfo** | One callable operation: an HTTP method on a specific URL path, with its parameters and description. |
| **ParameterInfo** | A single input to an endpoint: its name, location (path/query/body), type, and whether it's required. |
| **Introspection** | The process of booting a Pyramid app and reading its route/view registry to discover endpoints. |
| **Cornice enrichment** | An optional introspection step that extracts Marshmallow schema metadata from Cornice service definitions, producing richer parameter info (body fields, querystring filters). |
| **Code generation** | Rendering Jinja2 templates with a `ClientSpec` to produce Python source files (client class, Pyramid extension, package init). |
| **Pyramid extension (`includeme`)** | A function that Pyramid calls during configuration to register the client on the request object (e.g., `request.payments_client`). |
| **Verb detection** | Using NLTK WordNet to identify action verbs at the end of URL paths, enabling method names like `cancel_charge` instead of `create_charge_cancel`. |
| **Detail endpoint** | A path that ends with a path parameter (e.g., `/charges/{id}`), representing a single resource. Methods are singularized: `get_charge`. |
| **Collection endpoint** | A path that ends with a resource name (e.g., `/charges`), representing a list. GET uses `list_` prefix: `list_charges`. |
| **SchemaInfo** | A captured Marshmallow schema (name + fields) ready for code generation. Attached to endpoints for request body, querystring, or response serialization. |
| **SchemaFieldInfo** | A single field within a `SchemaInfo`: its name, Marshmallow field type (e.g., `"Integer"`), required flag, and metadata. |
| **Schema-based serialization** | The generated client uses copies of the server's Marshmallow schemas. `dump()` serializes outgoing requests (mirror of server's `load()`), `load()` deserializes incoming responses (mirror of server's `dump()`). |
| **pycornmarsh metadata** | An alternative schema declaration pattern using custom Pyramid view predicates (`pcm_request`, `pcm_responses`). Provides explicit location-to-schema mapping and per-status-code response schemas. Takes precedence over Cornice's `schema` kwarg when present. |
| **pcm_request** | A dict passed to Cornice decorators mapping locations (`"body"`, `"querystring"`) to Marshmallow schema classes. Provides more explicit schema location info than the `schema` kwarg + validator inference pattern. |
| **pcm_responses** | A dict passed to Cornice decorators mapping HTTP status codes (e.g., `200`, `400`) to Marshmallow schema classes. Enables per-status-code response typing. The first 2xx schema becomes the endpoint's primary `response_schema`. |

## Mental Models

### The protoc analogy

Think of `pclient-build` like `protoc` for gRPC: you define your API in one place (Pyramid routes + Cornice services), run a build tool, and get a typed client package on disk. The generated code is committed to the consuming project's repo and treated as source.

### Three-layer pipeline

```
Introspection → ClientSpec → Code Generation
```

Each layer is independent and testable:
- Introspection only reads Pyramid's registry — it doesn't generate any code.
- ClientSpec is a plain data structure — it can be built manually for testing.
- Code generation only reads a ClientSpec and renders templates — it doesn't touch Pyramid.

### Method naming as path interpretation

URL paths encode intent: `/charges` is a collection, `/charges/{id}` is a detail, and `/charges/{id}/cancel` is an action. The naming module interprets this structure to produce natural Python method names without requiring explicit annotations in the source app.

## Invariants

- Every generated method maps to exactly one HTTP method on one URL path.
- Path parameters in the URL become required positional arguments in the method signature.
- Querystring parameters become optional keyword arguments.
- Body parameters become individual keyword arguments; when a schema exists, the body is serialized through `schema.dump()` before sending.
- Querystring parameters with a schema are serialized through `schema.dump()`; without a schema, they fall back to a raw params dict.
- Response deserialization uses `schema.load()` when a response schema is declared; otherwise returns raw `response.json()`.
- The generated client is a standalone package that depends on `requests` and `marshmallow` (when schemas are present).
- Re-running `pclient-build` with the same inputs produces identical output (deterministic generation).
