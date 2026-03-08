"""Cornice service discovery and Marshmallow schema extraction.

Adapted from pyramid-mcp's introspection/cornice.py, focused on extracting
field-level metadata from Marshmallow schemas so we can generate typed
method signatures and schema-based serialization in the client.
"""

import logging
from typing import Any

from pyramid_client_builder.models import (
    EndpointInfo,
    ParameterInfo,
    SchemaFieldInfo,
    SchemaInfo,
)

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
    validators.  Also captures full SchemaInfo for code generation.
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


_LOCATION_FIELDS = {"body", "querystring", "path"}


def _enrich_endpoint(endpoint: EndpointInfo, service: Any) -> None:
    """Add Cornice schema parameters and SchemaInfo to an endpoint."""
    definitions = getattr(service, "definitions", [])

    for method, view_callable, args in definitions:
        if method.upper() != endpoint.method:
            continue

        if not endpoint.description:
            endpoint.description = getattr(service, "description", "") or ""

        pcm_request = args.get("pcm_request")
        pcm_responses = args.get("pcm_responses")

        if pcm_request is not None:
            _enrich_from_pcm_request(endpoint, pcm_request)
        else:
            schema_cls = args.get("schema")
            if schema_cls is not None:
                schema_instance = _instantiate(schema_cls)
                if schema_instance is not None:
                    if _is_composite_schema(schema_instance):
                        _enrich_from_composite(endpoint, schema_instance)
                    else:
                        _enrich_from_flat(endpoint, schema_cls, args)

        if pcm_responses is not None:
            _enrich_from_pcm_responses(endpoint, pcm_responses)
        else:
            response_schema_cls = _extract_response_schema(view_callable)
            if response_schema_cls is not None:
                response_info = _schema_to_schema_info(response_schema_cls)
                if response_info:
                    endpoint.response_schema = response_info

        break


def _is_composite_schema(schema_instance: Any) -> bool:
    """Detect Cornice composite schemas with location-named Nested fields.

    Composite schemas group fields by location::

        class MyRequestSchema(ma.Schema):
            body = ma.fields.Nested(BodySchema)
            querystring = ma.fields.Nested(QuerySchema)

    Returns True when at least one top-level field is a Nested field
    whose name matches a known location (body, querystring, path).
    """
    for name, field_obj in schema_instance.fields.items():
        if name in _LOCATION_FIELDS and type(field_obj).__name__ == "Nested":
            return True
    return False


def _enrich_from_composite(
    endpoint: EndpointInfo, schema_instance: Any
) -> None:
    """Extract parameters and schemas from a composite (location-aware) schema."""
    existing_names = {p.name for p in endpoint.parameters}

    for location_name, field_obj in schema_instance.fields.items():
        if location_name not in _LOCATION_FIELDS:
            continue
        if type(field_obj).__name__ != "Nested":
            continue

        inner_schema = _get_nested_schema(field_obj)
        if inner_schema is None:
            continue

        location = location_name
        if location == "path":
            continue

        params = _fields_to_parameters(inner_schema.fields, location)
        for p in params:
            if p.name not in existing_names:
                endpoint.parameters.append(p)
                existing_names.add(p.name)

        inner_info = _schema_to_schema_info(inner_schema)
        if inner_info:
            if location == "body":
                endpoint.request_schema = inner_info
            elif location == "querystring":
                endpoint.querystring_schema = inner_info


def _enrich_from_flat(
    endpoint: EndpointInfo, schema_cls: Any, args: dict
) -> None:
    """Extract parameters and schemas from a flat (single-location) schema."""
    location = _detect_location(args)
    params = _extract_from_schema(schema_cls, location)

    existing_names = {p.name for p in endpoint.parameters}
    for p in params:
        if p.name not in existing_names:
            endpoint.parameters.append(p)
            existing_names.add(p.name)

    schema_info = _schema_to_schema_info(schema_cls)
    if schema_info:
        if location == "body":
            endpoint.request_schema = schema_info
        elif location == "querystring":
            endpoint.querystring_schema = schema_info


def _enrich_from_pcm_request(endpoint: EndpointInfo, pcm_request: dict) -> None:
    """Extract parameters and schemas from pycornmarsh pcm_request metadata.

    ``pcm_request`` maps locations to Marshmallow schema classes::

        pcm_request=dict(body=BodySchema, querystring=QuerySchema)
    """
    existing_names = {p.name for p in endpoint.parameters}

    for location, schema_cls in pcm_request.items():
        if location not in ("body", "querystring"):
            continue

        params = _extract_from_schema(schema_cls, location)
        for p in params:
            if p.name not in existing_names:
                endpoint.parameters.append(p)
                existing_names.add(p.name)

        schema_info = _schema_to_schema_info(schema_cls)
        if schema_info:
            if location == "body":
                endpoint.request_schema = schema_info
            elif location == "querystring":
                endpoint.querystring_schema = schema_info


def _enrich_from_pcm_responses(
    endpoint: EndpointInfo, pcm_responses: dict
) -> None:
    """Extract response schemas from pycornmarsh pcm_responses metadata.

    ``pcm_responses`` maps HTTP status codes to Marshmallow schema classes::

        pcm_responses={200: SuccessSchema, 400: ErrorSchema}

    All schemas are stored in ``endpoint.response_schemas`` keyed by status
    code.  The first 2xx schema is also set as ``endpoint.response_schema``
    for backward compatibility with code that expects a single response schema.
    """
    success_set = False
    for status_code in sorted(pcm_responses, key=lambda c: int(c)):
        code = int(status_code)
        schema_info = _schema_to_schema_info(pcm_responses[status_code])
        if schema_info is None:
            continue

        endpoint.response_schemas[code] = schema_info

        if not success_set and 200 <= code < 300:
            endpoint.response_schema = schema_info
            success_set = True


def _instantiate(schema_cls: Any) -> Any | None:
    """Instantiate a schema class, handling both classes and instances."""
    try:
        instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        return instance if hasattr(instance, "fields") else None
    except Exception:
        logger.debug("Failed to instantiate schema", exc_info=True)
        return None


def _get_nested_schema(field_obj: Any) -> Any | None:
    """Get the inner schema instance from a Nested field."""
    nested = getattr(field_obj, "nested", None)
    if nested is None:
        return None
    try:
        if isinstance(nested, type):
            return nested()
        if callable(nested):
            return nested()
        return nested
    except Exception:
        logger.debug("Failed to get nested schema", exc_info=True)
        return None


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


def _extract_response_schema(view_callable: Any) -> Any | None:
    """Extract a response schema class from a view callable.

    Convention: the view function declares its response schema via a
    ``response_schema`` attribute set on the callable after definition::

        @service.post(schema=RequestSchema, validators=(...,))
        def create_thing(request):
            ...

        create_thing.response_schema = ThingResponseSchema
    """
    return getattr(view_callable, "response_schema", None)


def _schema_to_schema_info(schema_cls: Any) -> SchemaInfo | None:
    """Build a SchemaInfo from a Marshmallow schema class."""
    try:
        schema_instance = schema_cls() if isinstance(schema_cls, type) else schema_cls
        if not hasattr(schema_instance, "fields"):
            return None

        if isinstance(schema_cls, type):
            schema_name = schema_cls.__name__
        else:
            schema_name = type(schema_cls).__name__
        fields_info = _fields_to_schema_fields(schema_instance.fields)
        return SchemaInfo(name=schema_name, fields=fields_info)
    except Exception:
        logger.debug("Failed to build SchemaInfo", exc_info=True)
        return None


def _fields_to_schema_fields(fields: dict) -> list[SchemaFieldInfo]:
    """Convert Marshmallow field instances to SchemaFieldInfo objects."""
    result = []
    for field_name, field_obj in fields.items():
        field_type = type(field_obj).__name__
        required = getattr(field_obj, "required", False)
        metadata = dict(getattr(field_obj, "metadata", {}))

        result.append(
            SchemaFieldInfo(
                name=field_name,
                field_type=field_type,
                required=required,
                metadata=metadata,
            )
        )
    return result


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
