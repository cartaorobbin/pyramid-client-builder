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
