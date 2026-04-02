"""Introspection adapter.

Delegates route and view discovery to pyramid-introspector, then converts
the result into the flat EndpointInfo list that the generator expects.
"""

import fnmatch
import logging
from typing import Any

import marshmallow.fields
from pyramid_introspector import PyramidIntrospector as UpstreamIntrospector
from pyramid_introspector import SchemaInfo

from pyramid_client_builder.models import ClientSpec, CustomFieldInfo, EndpointInfo

logger = logging.getLogger(__name__)

_CLIENT_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


class PyramidIntrospector:
    """Introspects a Pyramid application to build a ClientSpec."""

    def __init__(self, registry: Any):
        self.registry = registry

    def build_client_spec(
        self,
        name: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> ClientSpec:
        """Introspect the app and produce a ClientSpec.

        Args:
            name: Client name (e.g. "payments").
            include_patterns: If set, only routes matching these globs are kept.
            exclude_patterns: Routes matching these globs are dropped.

        Returns:
            A ClientSpec ready for code generation.
        """
        routes = UpstreamIntrospector(self.registry).introspect()

        custom_fields = _detect_custom_fields(routes)

        endpoints = _routes_to_endpoints(routes)

        endpoints = _drop_wildcard_routes(endpoints)

        endpoints = _drop_non_client_methods(endpoints)

        endpoints = _filter_endpoints(endpoints, include_patterns, exclude_patterns)

        endpoints = _deduplicate(endpoints)

        schemas = _collect_schemas(endpoints)

        return ClientSpec(
            name=name,
            endpoints=endpoints,
            schemas=schemas,
            custom_fields=custom_fields,
        )


def _routes_to_endpoints(routes: list) -> list[EndpointInfo]:
    """Flatten RouteInfo/ViewInfo hierarchy into a flat EndpointInfo list."""
    endpoints: list[EndpointInfo] = []
    for route in routes:
        for view in route.views:
            endpoints.append(
                EndpointInfo(
                    name=route.name,
                    path=route.pattern,
                    method=view.method,
                    description=view.description,
                    parameters=list(view.parameters),
                    request_schema=view.request_schema,
                    querystring_schema=view.querystring_schema,
                    response_schema=view.response_schema,
                    response_schemas=dict(view.response_schemas),
                )
            )
    return endpoints


def _drop_wildcard_routes(endpoints: list[EndpointInfo]) -> list[EndpointInfo]:
    """Remove routes with wildcard patterns (e.g. static/*subpath).

    Pyramid uses ``*name`` for traversal and static views — these are
    never API endpoints and would produce invalid Python identifiers.
    """
    return [ep for ep in endpoints if "*" not in ep.path]


def _drop_non_client_methods(endpoints: list[EndpointInfo]) -> list[EndpointInfo]:
    """Remove HEAD, OPTIONS, and other methods irrelevant to an RPC-style client."""
    return [ep for ep in endpoints if ep.method in _CLIENT_METHODS]


def _filter_endpoints(
    endpoints: list[EndpointInfo],
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> list[EndpointInfo]:
    """Apply include/exclude glob filters on route paths."""
    result = endpoints

    if include_patterns:
        result = [
            ep
            for ep in result
            if any(fnmatch.fnmatch(ep.path, pat) for pat in include_patterns)
        ]

    if exclude_patterns:
        result = [
            ep
            for ep in result
            if not any(fnmatch.fnmatch(ep.path, pat) for pat in exclude_patterns)
        ]

    return result


def _deduplicate(endpoints: list[EndpointInfo]) -> list[EndpointInfo]:
    """Remove duplicate path+method combinations, keeping the first."""
    seen: set[tuple[str, str]] = set()
    unique: list[EndpointInfo] = []
    for ep in endpoints:
        key = (ep.path, ep.method)
        if key not in seen:
            seen.add(key)
            unique.append(ep)
    return unique


def _collect_schemas(endpoints: list[EndpointInfo]) -> list[SchemaInfo]:
    """Gather all unique schemas referenced by endpoints."""
    seen: set[str] = set()
    schemas: list[SchemaInfo] = []

    def _add(schema: SchemaInfo | None) -> None:
        if schema is not None and schema.name not in seen:
            seen.add(schema.name)
            schemas.append(schema)

    for ep in endpoints:
        _add(ep.request_schema)
        _add(ep.querystring_schema)
        _add(ep.response_schema)
        for schema in ep.response_schemas.values():
            _add(schema)

    return schemas


# ------------------------------------------------------------------
# Custom Marshmallow field detection
# ------------------------------------------------------------------

_STANDARD_FIELD_NAMES: set[str] = {
    name
    for name, obj in vars(marshmallow.fields).items()
    if isinstance(obj, type) and issubclass(obj, marshmallow.fields.Field)
}


def _detect_custom_fields(routes: list) -> list[CustomFieldInfo]:
    """Scan routes for Marshmallow schemas that use non-standard field types.

    Walks through the live schema classes stored in Cornice/pycornmarsh
    args (``view.extra["cornice_args"]``), instantiates each schema, and
    checks whether any field is a custom subclass not in the standard
    ``marshmallow.fields`` module.
    """
    schema_classes = _collect_schema_classes(routes)
    seen: set[str] = set()
    custom_fields: list[CustomFieldInfo] = []

    for schema_cls in schema_classes:
        instance = _safe_instantiate(schema_cls)
        if instance is None:
            continue
        for field_obj in instance.fields.values():
            field_type_name = type(field_obj).__name__
            if field_type_name in _STANDARD_FIELD_NAMES or field_type_name in seen:
                continue
            base_type = _resolve_base_marshmallow_type(type(field_obj))
            if base_type is not None:
                seen.add(field_type_name)
                custom_fields.append(
                    CustomFieldInfo(class_name=field_type_name, base_type=base_type)
                )

    return custom_fields


def _collect_schema_classes(routes: list) -> list[type]:
    """Extract actual Marshmallow schema classes from route/view metadata."""
    classes: list[type] = []
    seen_ids: set[int] = set()

    def _add(cls: Any) -> None:
        if cls is None:
            return
        if not isinstance(cls, type):
            cls = type(cls)
        if id(cls) not in seen_ids:
            seen_ids.add(id(cls))
            classes.append(cls)

    for route in routes:
        for view in route.views:
            cornice_args = view.extra.get("cornice_args", {})

            schema_cls = cornice_args.get("schema")
            if schema_cls is not None:
                _add(schema_cls)

            pcm_request = cornice_args.get("pcm_request")
            if pcm_request is not None:
                for location_schema in pcm_request.values():
                    _add(location_schema)

            pcm_responses = cornice_args.get("pcm_responses")
            if pcm_responses is not None:
                for response_schema in pcm_responses.values():
                    if not isinstance(response_schema, str):
                        _add(response_schema)

    return classes


def _resolve_base_marshmallow_type(field_cls: type) -> str | None:
    """Walk the MRO to find the first standard Marshmallow field ancestor.

    When the walk reaches the base ``Field`` class without finding a more
    specific ancestor, ``"String"`` is returned instead of ``"Field"`` so
    the generated stub provides at least basic string serialization.
    """
    for ancestor in field_cls.__mro__:
        if ancestor.__name__ in _STANDARD_FIELD_NAMES:
            if ancestor is marshmallow.fields.Field:
                return "String"
            return ancestor.__name__
    return None


def _safe_instantiate(schema_cls: Any) -> Any | None:
    """Instantiate a schema class, returning None on failure."""
    try:
        instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        return instance if hasattr(instance, "fields") else None
    except Exception:
        logger.debug("Failed to instantiate schema %s", schema_cls, exc_info=True)
        return None
