"""Introspection adapter.

Delegates route and view discovery to pyramid-introspector, then converts
the result into the flat EndpointInfo list that the generator expects.
"""

import fnmatch
import logging
from typing import Any

from pyramid_introspector import PyramidIntrospector as UpstreamIntrospector
from pyramid_introspector import SchemaInfo

from pyramid_client_builder.models import ClientSpec, EndpointInfo

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

        endpoints = _routes_to_endpoints(routes)

        endpoints = _drop_wildcard_routes(endpoints)

        endpoints = _drop_non_client_methods(endpoints)

        endpoints = _filter_endpoints(endpoints, include_patterns, exclude_patterns)

        endpoints = _deduplicate(endpoints)

        schemas = _collect_schemas(endpoints)

        return ClientSpec(name=name, endpoints=endpoints, schemas=schemas)


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
