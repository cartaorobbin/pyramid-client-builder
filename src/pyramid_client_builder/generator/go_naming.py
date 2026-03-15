"""Naming conventions for generated Go client code."""

import re

from pyramid_client_builder.generator.naming import to_method_name

_SEPARATORS = re.compile(r"[-_]+")

GO_TYPE_MAP = {
    "String": "string",
    "Integer": "int",
    "Float": "float64",
    "Boolean": "bool",
    "DateTime": "time.Time",
    "Date": "time.Time",
    "Time": "time.Time",
    "UUID": "string",
    "Email": "string",
    "URL": "string",
    "Url": "string",
    "Decimal": "string",
    "Raw": "json.RawMessage",
    "Dict": "map[string]interface{}",
    "Mapping": "map[string]interface{}",
    "List": "[]interface{}",
}

IMPORTS_FOR_TYPE = {
    "time.Time": "time",
    "json.RawMessage": "encoding/json",
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


def to_go_package_name(name: str) -> str:
    """Convert a client name to a Go package name.

    Go packages are lowercase with no separators.

    Examples:
        "payments"     -> "paymentsclient"
        "legal-entity" -> "legalentityclient"
        "my_service"   -> "myserviceclient"
    """
    clean = _SEPARATORS.sub("", name).lower()
    return f"{clean}client"


def to_go_module_name(name: str) -> str:
    """Convert a client name to a default Go module path.

    Examples:
        "payments"     -> "payments-client"
        "legal_entity" -> "legal-entity-client"
    """
    return _SEPARATORS.sub("-", name).lower() + "-client"


def to_go_method_name(route_name: str, method: str, path: str = "") -> str:
    """Convert route info to a PascalCase Go method name.

    Reuses the Python naming logic then converts to PascalCase.

    Examples:
        ("charges", "GET", "/api/v1/charges")          -> "ListCharges"
        ("charge_detail", "GET", "/api/v1/charges/{id}") -> "GetCharge"
        ("charge_cancel", "POST", "/api/v1/charges/{id}/cancel") -> "CancelCharge"
        ("home", "GET", "/")                            -> "GetHome"
    """
    snake = to_method_name(route_name, method, path)
    return snake_to_pascal(snake)


def to_go_field_name(name: str) -> str:
    """Convert a field name to an exported Go field name (PascalCase).

    Examples:
        "amount"      -> "Amount"
        "part_id"     -> "PartId"
        "description" -> "Description"
    """
    return snake_to_pascal(name)


def to_go_type(field_type: str, required: bool = True) -> str:
    """Map a Marshmallow field type to a Go type.

    Optional fields use pointer types.

    Examples:
        ("String", True)   -> "string"
        ("String", False)  -> "*string"
        ("Integer", True)  -> "int"
        ("DateTime", True) -> "time.Time"
    """
    go_type = GO_TYPE_MAP.get(field_type, "interface{}")
    if not required and go_type not in (
        "[]interface{}",
        "map[string]interface{}",
        "json.RawMessage",
    ):
        return f"*{go_type}"
    return go_type


def go_type_needs_import(field_type: str) -> str | None:
    """Return the Go import path needed for a field type, or None."""
    go_type = GO_TYPE_MAP.get(field_type, "")
    return IMPORTS_FOR_TYPE.get(go_type)


def to_go_version_field(version: str) -> str:
    """Convert a version string to a Go struct field name.

    Examples:
        "v1" -> "V1"
        "v2" -> "V2"
    """
    return version.upper()
