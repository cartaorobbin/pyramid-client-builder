"""Shared utilities for client code generators.

Language-agnostic helpers for grouping endpoints by version, renaming
schemas, and collecting unique schemas.  Used by both the Python and Go
generators.
"""

from pyramid_introspector import SchemaInfo

from pyramid_client_builder.generator.naming import (
    extract_version,
    needs_schema_rename,
    to_schema_name,
)
from pyramid_client_builder.models import EndpointInfo


def group_by_version(
    endpoints: list[EndpointInfo],
) -> tuple[dict[str, list[EndpointInfo]], list[EndpointInfo]]:
    """Split endpoints into versioned groups and an unversioned remainder."""
    versioned: dict[str, list[EndpointInfo]] = {}
    unversioned: list[EndpointInfo] = []

    for ep in endpoints:
        version = extract_version(ep.path)
        if version:
            versioned.setdefault(version, []).append(ep)
        else:
            unversioned.append(ep)

    return versioned, unversioned


def rename_schemas(endpoints: list[EndpointInfo]) -> None:
    """Rename schemas that lack a role suffix based on endpoint path + role.

    Mutates ``SchemaInfo.name`` in place.  Skips schemas whose name
    already ends with a recognized role suffix (e.g. ``RequestSchema``).
    Skips schemas where the generated name conflicts with another schema's
    original name or where the same schema would get different names from
    different endpoints.
    """
    rename_map: dict[str, str] = {}
    conflicts: set[str] = set()
    all_original_names: set[str] = set()

    for ep in endpoints:
        for schema in iter_schemas(ep):
            all_original_names.add(schema.name)

    role_attrs = [
        ("request_schema", "request"),
        ("querystring_schema", "querystring"),
        ("response_schema", "response"),
    ]
    for ep in endpoints:
        for attr, role in role_attrs:
            schema = getattr(ep, attr)
            if schema is None or not needs_schema_rename(schema.name):
                continue
            new_name = to_schema_name(ep.path, role)
            if new_name is None or new_name in all_original_names:
                continue
            original = schema.name
            if original in conflicts:
                continue
            if original in rename_map:
                if rename_map[original] != new_name:
                    conflicts.add(original)
                continue
            rename_map[original] = new_name

    for name in conflicts:
        rename_map.pop(name, None)

    if not rename_map:
        return

    for ep in endpoints:
        for schema in iter_schemas(ep):
            if schema.name in rename_map:
                schema.name = rename_map[schema.name]


def iter_schemas(endpoint: EndpointInfo):
    """Yield all non-None SchemaInfo objects from an endpoint."""
    for attr in ("request_schema", "querystring_schema", "response_schema"):
        schema = getattr(endpoint, attr)
        if schema is not None:
            yield schema
    yield from endpoint.response_schemas.values()


def collect_schemas(endpoints: list[EndpointInfo]) -> list[SchemaInfo]:
    """Gather unique schemas referenced by endpoints (by name).

    Recursively collects nested schemas discovered by the introspector
    (e.g. ``PhoneSchema`` inside ``PersonSchema.phones``).
    """
    seen: set[str] = set()
    schemas: list[SchemaInfo] = []

    def _add(schema: SchemaInfo) -> None:
        if schema.name in seen:
            return
        seen.add(schema.name)
        schemas.append(schema)
        for nested in schema.nested_schemas:
            _add(nested)

    for ep in endpoints:
        for schema in iter_schemas(ep):
            _add(schema)

    return schemas
