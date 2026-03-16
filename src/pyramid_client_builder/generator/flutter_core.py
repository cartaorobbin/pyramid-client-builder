"""Flutter/Dart client code generator.

Takes a ClientSpec and renders Jinja2 templates into a Dart package
on disk.  Uses the same template tree renderer as the Python and Go generators.
"""

import logging
import re
from importlib.resources import files as package_files
from pathlib import Path

from jinja2 import Environment
from pyramid_introspector import SchemaFieldInfo

from pyramid_client_builder.generator.common import (
    collect_schemas,
    group_by_version,
    rename_schemas,
)
from pyramid_client_builder.generator.flutter_naming import (
    snake_to_camel,
    to_dart_class_name,
    to_dart_field_name,
    to_dart_method_name,
    to_dart_package_name,
    to_dart_type,
    to_dart_version_class,
    to_dart_version_field,
)
from pyramid_client_builder.generator.renderer import render_tree
from pyramid_client_builder.models import ClientSpec, EndpointInfo

logger = logging.getLogger(__name__)

_FLUTTER_TEMPLATES_DIR = package_files("pyramid_client_builder.generator").joinpath(
    "flutter_templates"
)

PYTHON_TO_DART_TYPE = {
    "str": "String",
    "int": "int",
    "float": "double",
    "bool": "bool",
    "dict": "Map<String, dynamic>",
    "list": "List<dynamic>",
}


class FlutterClientGenerator:
    """Generates a Flutter/Dart client package from a ClientSpec."""

    def __init__(
        self,
        spec: ClientSpec,
        version: str = "0.1.0",
        flutter_package: str = "",
    ):
        self.spec = spec
        self.version = version
        self.package_name = flutter_package or to_dart_package_name(spec.name)
        self.class_name = to_dart_class_name(spec.name)
        self._env = self._create_jinja_env()

    def generate(self, output_dir: str | Path) -> Path:
        """Write the generated Dart package to output_dir.

        The Dart package files (pubspec.yaml, lib/, README.md)
        are rendered at the root of output_dir.  Versioned sub-directories
        are created via the @each(versions) directive.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        versioned, unversioned = group_by_version(self.spec.endpoints)

        versions_ctx: dict[str, dict] = {}
        for ver in sorted(versioned.keys()):
            endpoints = versioned[ver]
            rename_schemas(endpoints)
            self._annotate_endpoints(endpoints)
            schemas = collect_schemas(endpoints)
            versions_ctx[ver] = {
                "version": ver,
                "version_field": to_dart_version_field(ver),
                "version_class": to_dart_version_class(ver),
                "endpoints": endpoints,
                "schemas": schemas,
                "has_body": any(ep.has_body for ep in endpoints),
            }

        rename_schemas(unversioned)
        self._annotate_endpoints(unversioned)
        unversioned_schemas = collect_schemas(unversioned)

        context = {
            "spec": self.spec,
            "package_name": self.package_name,
            "class_name": self.class_name,
            "client_version": self.version,
            "versions": versions_ctx,
            "endpoints": unversioned,
            "schemas": unversioned_schemas,
            "has_body": any(ep.has_body for ep in unversioned),
        }

        render_tree(_FLUTTER_TEMPLATES_DIR, output_path, context, self._env)

        logger.info(
            "Generated Flutter client %s with %d endpoints in %s",
            self.package_name,
            len(self.spec.endpoints),
            output_path,
        )

        return output_path

    def _annotate_endpoints(self, endpoints: list[EndpointInfo]) -> None:
        """Add computed ``method_name`` attribute (camelCase Dart method)."""
        seen_names: dict[str, int] = {}

        for endpoint in endpoints:
            base_name = to_dart_method_name(
                endpoint.name, endpoint.method, endpoint.path
            )
            count = seen_names.get(base_name, 0)
            seen_names[base_name] = count + 1

            method_name = base_name if count == 0 else f"{base_name}{count}"
            endpoint.method_name = method_name  # type: ignore[attr-defined]

    def _create_jinja_env(self) -> Environment:
        env = Environment(
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["dart_method_params"] = _dart_method_params_filter
        env.filters["dart_return_type"] = _dart_return_type_filter
        env.filters["dart_format_url"] = _dart_format_url_filter
        env.filters["dart_doc_path"] = _dart_doc_path_filter
        env.filters["dart_field_name"] = to_dart_field_name
        env.filters["dart_field_type"] = _dart_field_type_filter
        env.filters["dart_param_name"] = snake_to_camel
        env.filters["dart_version_field"] = to_dart_version_field
        env.filters["dart_version_class"] = to_dart_version_class
        env.filters["dart_json_key"] = _dart_json_key_filter
        env.filters["dart_from_json_value"] = _dart_from_json_value_filter
        env.filters["dart_to_json_value"] = _dart_to_json_value_filter
        return env


# ======================================================================
# Jinja2 filters
# ======================================================================


def _param_type_to_dart(type_hint: str) -> str:
    """Convert a Python-style type hint to a Dart type."""
    return PYTHON_TO_DART_TYPE.get(type_hint, "dynamic")


def _dart_method_params_filter(endpoint: EndpointInfo) -> str:
    """Build a Dart method parameter list.

    Path parameters are required positional, body/query are named parameters
    wrapped in curly braces.
    """
    positional: list[str] = []
    named: list[str] = []

    for p in endpoint.path_parameters:
        positional.append(f"String {snake_to_camel(p.name)}")

    if endpoint.request_schema:
        positional.append(f"{endpoint.request_schema.name} req")
    else:
        for p in endpoint.body_parameters:
            dart_type = _param_type_to_dart(p.type_hint)
            if p.required:
                named.append(f"required {dart_type} {snake_to_camel(p.name)}")
            else:
                named.append(f"{dart_type}? {snake_to_camel(p.name)}")

    if endpoint.querystring_schema:
        named.append(f"{endpoint.querystring_schema.name}? query")
    else:
        for p in endpoint.querystring_parameters:
            dart_type = _param_type_to_dart(p.type_hint)
            named.append(f"{dart_type}? {snake_to_camel(p.name)}")

    parts = positional[:]
    if named:
        parts.append("{" + ", ".join(named) + "}")
    return ", ".join(parts)


def _dart_return_type_filter(endpoint: EndpointInfo) -> str:
    """Return the Dart return type for an endpoint method."""
    if endpoint.response_schema:
        return endpoint.response_schema.name
    return "Map<String, dynamic>"


def _dart_format_url_filter(endpoint: EndpointInfo) -> str:
    """Convert a Pyramid path to a Dart string interpolation.

    Path parameters (including those with regex) are replaced with
    Dart interpolation expressions.
    """
    path = re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)

    def _replace_param(match):
        param_name = match.group(1)
        return f"${snake_to_camel(param_name)}"

    return re.sub(r"\{(\w+)\}", _replace_param, path)


def _dart_doc_path_filter(endpoint: EndpointInfo) -> str:
    """Clean regex from path for use in Dart doc comments."""
    return re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)


def _dart_field_type_filter(field_info: SchemaFieldInfo) -> str:
    """Map a SchemaFieldInfo to its Dart type."""
    return to_dart_type(field_info.field_type, field_info.required)


def _dart_json_key_filter(field_info: SchemaFieldInfo) -> str:
    """Return the JSON key name for a field (original snake_case name)."""
    return field_info.name


def _dart_from_json_value_filter(field_info: SchemaFieldInfo) -> str:
    """Build the Dart expression to deserialize a field from JSON.

    Handles type casting and DateTime.parse for temporal types.
    """
    dart_type = to_dart_type(field_info.field_type, field_info.required)
    key = f"json['{field_info.name}']"
    base_type = dart_type.rstrip("?")
    is_nullable = dart_type.endswith("?")

    if base_type == "DateTime":
        if is_nullable:
            return f"{key} != null ? DateTime.parse({key}) : null"
        return f"DateTime.parse({key})"

    if base_type in ("List<dynamic>", "Map<String, dynamic>", "dynamic"):
        return key

    if is_nullable:
        return f"{key} as {dart_type}"

    return f"{key} as {base_type}"


def _dart_to_json_value_filter(field_info: SchemaFieldInfo) -> str:
    """Build the Dart expression to serialize a field to JSON.

    Handles DateTime.toIso8601String() for temporal types.
    """
    dart_type = to_dart_type(field_info.field_type, field_info.required)
    field_name = to_dart_field_name(field_info.name)
    base_type = dart_type.rstrip("?")
    is_nullable = dart_type.endswith("?")

    if base_type == "DateTime":
        if is_nullable:
            return f"{field_name}?.toIso8601String()"
        return f"{field_name}.toIso8601String()"

    return field_name
