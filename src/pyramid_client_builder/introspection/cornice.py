"""Cornice service discovery and Marshmallow schema extraction.

Adapted from pyramid-mcp's introspection/cornice.py, focused on extracting
field-level metadata from Marshmallow schemas so we can generate typed
method signatures in the client.
"""

import logging
from typing import Any

from pyramid_client_builder.models import EndpointInfo, ParameterInfo

logger = logging.getLogger(__name__)

MARSHMALLOW_TYPE_MAP = {
    "String": "str",
    "Int": "int",
    "Integer": "int",
    "Float": "float",
    "Decimal": "str",
    "Bool": "bool",
    "Boolean": "bool",
    "UUID": "str",
    "DateTime": "str",
    "Date": "str",
    "List": "list",
    "Nested": "dict",
    "Dict": "dict",
    "Raw": "Any",
}


def enrich_endpoints_with_cornice(
    registry: Any, endpoints: list[EndpointInfo]
) -> list[EndpointInfo]:
    """Enrich route-discovered endpoints with Cornice schema metadata.

    Matches endpoints to Cornice service definitions by path+method, then
    extracts Marshmallow schema fields for querystring, body, and path
    validators.
    """
    services = _get_cornice_services()
    if not services:
        return endpoints

    service_by_path = _index_services_by_path(services)

    for endpoint in endpoints:
        service = service_by_path.get(endpoint.path)
        if not service:
            continue

        _enrich_endpoint(endpoint, service)

    return endpoints


def _get_cornice_services() -> list[Any]:
    """Get all registered Cornice services."""
    try:
        from cornice.service import get_services

        return list(get_services())
    except ImportError:
        logger.debug("Cornice not installed, skipping Cornice enrichment")
        return []
    except Exception:
        logger.debug("Failed to get Cornice services", exc_info=True)
        return []


def _index_services_by_path(services: list[Any]) -> dict[str, Any]:
    """Build a lookup from path pattern to Cornice service."""
    index: dict[str, Any] = {}
    for service in services:
        path = getattr(service, "path", "")
        if path:
            index[path] = service
    return index


def _enrich_endpoint(endpoint: EndpointInfo, service: Any) -> None:
    """Add Cornice schema parameters to an endpoint."""
    definitions = getattr(service, "definitions", [])

    for method, view_callable, args in definitions:
        if method.upper() != endpoint.method:
            continue

        if not endpoint.description:
            endpoint.description = getattr(service, "description", "") or ""

        schema_cls = args.get("schema")
        if schema_cls is None:
            break

        location = _detect_location(args)
        params = _extract_from_schema(schema_cls, location)

        existing_names = {p.name for p in endpoint.parameters}
        for p in params:
            if p.name not in existing_names:
                endpoint.parameters.append(p)
                existing_names.add(p.name)

        break


def _detect_location(args: dict) -> str:
    """Detect parameter location from Cornice validator functions.

    Cornice uses different validators for body vs querystring:
    - marshmallow_validator -> qualname "validator" -> body
    - marshmallow_querystring_validator -> qualname contains "_generate_marshmallow" -> querystring
    - marshmallow_path_validator -> similar pattern -> path
    """
    validators = args.get("validators", [])
    for v in validators:
        qualname = getattr(v, "__qualname__", "") or ""

        if qualname == "validator":
            return "body"

        if "_generate_marshmallow" in qualname:
            func = getattr(v, "func", None)
            if func:
                func_qualname = getattr(func, "__qualname__", "")
                if "querystring" in func_qualname.lower():
                    return "querystring"
                if "path" in func_qualname.lower():
                    return "path"
            return "querystring"

    return "body"


def _extract_from_schema(schema_cls: Any, location: str) -> list[ParameterInfo]:
    """Extract ParameterInfo list from a Marshmallow schema class."""
    if schema_cls is None:
        return []

    try:
        schema_instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        if not hasattr(schema_instance, "fields"):
            return []

        return _fields_to_parameters(schema_instance.fields, location)
    except Exception:
        logger.debug(
            "Failed to extract schema for location=%s", location, exc_info=True
        )
        return []


def _fields_to_parameters(fields: dict, location: str) -> list[ParameterInfo]:
    """Convert Marshmallow fields to ParameterInfo objects."""
    params = []
    for field_name, field_obj in fields.items():
        type_hint = _marshmallow_field_to_type(field_obj)
        required = getattr(field_obj, "required", False)

        metadata = getattr(field_obj, "metadata", {})
        description = metadata.get("description", "") if metadata else ""

        params.append(
            ParameterInfo(
                name=field_name,
                location=location,
                required=required,
                type_hint=type_hint,
                description=description,
            )
        )
    return params


def _marshmallow_field_to_type(field_obj: Any) -> str:
    """Map a Marshmallow field to a Python type hint string."""
    class_name = type(field_obj).__name__
    return MARSHMALLOW_TYPE_MAP.get(class_name, "Any")
