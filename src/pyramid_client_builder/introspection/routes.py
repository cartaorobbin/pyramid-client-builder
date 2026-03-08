"""Route discovery from the Pyramid introspection system.

Adapted from pyramid-mcp's introspection/routes.py, simplified for
client generation (we need path, method, and parameter info rather than
MCP tool definitions).
"""

import logging
import re
from typing import Any

from pyramid_client_builder.models import EndpointInfo, ParameterInfo

logger = logging.getLogger(__name__)

PATH_PARAM_RE = re.compile(r"\{(\w+)(?::.*?)?\}")


def discover_routes(registry: Any) -> list[EndpointInfo]:
    """Discover routes from a Pyramid registry and convert to EndpointInfo.

    Args:
        registry: A committed Pyramid registry (from bootstrap or make_wsgi_app).

    Returns:
        List of EndpointInfo for every route+method combination found.
    """
    introspector = registry.introspector
    route_mapper = registry.getUtility(
        _import_routes_mapper_interface()
    )

    route_objects = {route.name: route for route in route_mapper.get_routes()}
    route_category = introspector.get_category("routes") or []
    view_category = introspector.get_category("views") or []

    views_by_route: dict[str, list[Any]] = {}
    for item in view_category:
        view_intr = item["introspectable"]
        route_name = view_intr.get("route_name")
        if route_name:
            views_by_route.setdefault(route_name, []).append(view_intr)

    endpoints: list[EndpointInfo] = []

    for item in route_category:
        route_intr = item["introspectable"]
        route_name = route_intr.get("name")
        if not route_name:
            continue

        pattern = route_intr.get("pattern", "")
        views = views_by_route.get(route_name, [])

        if not views:
            continue

        has_explicit_methods = any(_extract_methods(v) for v in views)

        for view_intr in views:
            methods = _extract_methods(view_intr)
            if not methods:
                if has_explicit_methods:
                    continue
                methods = ["GET"]

            for method in methods:
                path_params = _extract_path_params(pattern)
                endpoint = EndpointInfo(
                    name=route_name,
                    path=pattern,
                    method=method.upper(),
                    description=_extract_description(view_intr),
                    parameters=path_params,
                )
                endpoints.append(endpoint)

    return endpoints


def _extract_methods(view_intr: Any) -> list[str]:
    """Extract HTTP methods from a view introspectable."""
    methods = view_intr.get("request_methods")
    if methods is None:
        return []
    if isinstance(methods, str):
        return [methods]
    return list(methods)


def _extract_path_params(pattern: str) -> list[ParameterInfo]:
    """Extract path parameters from a route pattern like /api/{id}."""
    params = []
    for match in PATH_PARAM_RE.finditer(pattern):
        params.append(
            ParameterInfo(
                name=match.group(1),
                location="path",
                required=True,
                type_hint="str",
            )
        )
    return params


def _extract_description(view_intr: Any) -> str:
    """Try to get a description from the view callable's docstring."""
    view_callable = view_intr.get("callable")
    if view_callable and hasattr(view_callable, "__doc__") and view_callable.__doc__:
        return view_callable.__doc__.strip().split("\n")[0]
    return ""


def _import_routes_mapper_interface():
    """Import IRoutesMapper lazily to avoid import-time Pyramid dependency."""
    from pyramid.interfaces import IRoutesMapper

    return IRoutesMapper
