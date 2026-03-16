"""Naming conventions for generated Flutter/Dart client code."""

import re

from pyramid_client_builder.generator.naming import to_method_name

_SEPARATORS = re.compile(r"[-_]+")

DART_TYPE_MAP = {
    "String": "String",
    "Integer": "int",
    "Float": "double",
    "Boolean": "bool",
    "DateTime": "DateTime",
    "Date": "DateTime",
    "Time": "DateTime",
    "UUID": "String",
    "Email": "String",
    "URL": "String",
    "Url": "String",
    "Decimal": "String",
    "Raw": "dynamic",
    "Dict": "Map<String, dynamic>",
    "Mapping": "Map<String, dynamic>",
    "List": "List<dynamic>",
}

NULLABLE_ALWAYS = {
    "dynamic",
}


def snake_to_pascal(name: str) -> str:
    """Convert a snake_case name to PascalCase.

    Examples:
        "list_charges"  -> "ListCharges"
        "get_home"      -> "GetHome"
        "cancel_charge" -> "CancelCharge"
    """
    return "".join(word.capitalize() for word in name.split("_") if word)


def snake_to_camel(name: str) -> str:
    """Convert a snake_case name to camelCase.

    Examples:
        "charge_id" -> "chargeId"
        "item_name" -> "itemName"
        "status"    -> "status"
    """
    parts = name.split("_")
    if not parts:
        return ""
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


def to_dart_package_name(name: str) -> str:
    """Convert a client name to a Dart package name (snake_case).

    Examples:
        "payments"     -> "payments_client"
        "legal-entity" -> "legal_entity_client"
        "my_service"   -> "my_service_client"
    """
    clean = _SEPARATORS.sub("_", name).lower()
    return f"{clean}_client"


def to_dart_class_name(name: str) -> str:
    """Convert a client name to a PascalCase Dart class name.

    Examples:
        "payments"     -> "PaymentsClient"
        "legal-entity" -> "LegalEntityClient"
        "my_service"   -> "MyServiceClient"
    """
    parts = _SEPARATORS.split(name)
    pascal = "".join(part.capitalize() for part in parts if part)
    return f"{pascal}Client"


def to_dart_method_name(route_name: str, method: str, path: str = "") -> str:
    """Convert route info to a camelCase Dart method name.

    Reuses the Python naming logic then converts to camelCase.

    Examples:
        ("charges", "GET", "/api/v1/charges")            -> "listCharges"
        ("charge_detail", "GET", "/api/v1/charges/{id}") -> "getCharge"
        ("charge_cancel", "POST", "/api/v1/charges/{id}/cancel") -> "cancelCharge"
        ("home", "GET", "/")                              -> "getHome"
    """
    snake = to_method_name(route_name, method, path)
    return snake_to_camel(snake)


def to_dart_field_name(name: str) -> str:
    """Convert a field name to a camelCase Dart field name.

    Examples:
        "amount"      -> "amount"
        "part_id"     -> "partId"
        "created_at"  -> "createdAt"
    """
    return snake_to_camel(name)


def to_dart_type(field_type: str, required: bool = True) -> str:
    """Map a Marshmallow field type to a Dart type.

    Optional fields use nullable types (String?).

    Examples:
        ("String", True)   -> "String"
        ("String", False)  -> "String?"
        ("Integer", True)  -> "int"
        ("DateTime", True) -> "DateTime"
        ("List", True)     -> "List<dynamic>"
    """
    dart_type = DART_TYPE_MAP.get(field_type, "dynamic")
    if not required and dart_type not in NULLABLE_ALWAYS:
        return f"{dart_type}?"
    return dart_type


def to_dart_version_prefix(version: str) -> str:
    """Convert a version string to a Dart import prefix.

    Uses a distinct name to avoid shadowing the field name.

    Examples:
        "v1" -> "v1_api"
        "v2" -> "v2_api"
    """
    return f"{version.lower()}_api"


def to_dart_version_field(version: str) -> str:
    """Convert a version string to a Dart field name.

    Examples:
        "v1" -> "v1"
        "v2" -> "v2"
    """
    return version.lower()


def to_dart_version_class(version: str) -> str:
    """Convert a version string to a Dart class name prefix.

    Examples:
        "v1" -> "V1"
        "v2" -> "V2"
    """
    return version.upper()
