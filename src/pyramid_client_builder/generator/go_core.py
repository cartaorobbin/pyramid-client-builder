"""Go client code generator.

Takes a ClientSpec and renders Jinja2 templates into a Go module
on disk.  Uses the same template tree renderer as the Python generator.
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
from pyramid_client_builder.generator.go_naming import (
    go_type_needs_import,
    snake_to_camel,
    to_go_field_name,
    to_go_method_name,
    to_go_module_name,
    to_go_package_name,
    to_go_type,
    to_go_version_field,
)
from pyramid_client_builder.generator.renderer import render_tree
from pyramid_client_builder.models import ClientSpec, EndpointInfo

logger = logging.getLogger(__name__)

_GO_TEMPLATES_DIR = package_files("pyramid_client_builder.generator").joinpath(
    "go_templates"
)

PYTHON_TO_GO_TYPE = {
    "str": "string",
    "int": "int",
    "float": "float64",
    "bool": "bool",
    "dict": "map[string]interface{}",
    "list": "[]interface{}",
}


class GoClientGenerator:
    """Generates a Go client module from a ClientSpec."""

    def __init__(
        self,
        spec: ClientSpec,
        version: str = "0.1.0",
        go_module: str = "",
    ):
        self.spec = spec
        self.version = version
        self.go_package = to_go_package_name(spec.name)
        self.go_module = go_module or to_go_module_name(spec.name)
        self._env = self._create_jinja_env()

    def generate(self, output_dir: str | Path) -> Path:
        """Write the generated Go module to output_dir.

        The Go module files (go.mod, client.go, types.go, README.md)
        are rendered at the root of output_dir.  Versioned sub-packages
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
                "version_field": to_go_version_field(ver),
                "endpoints": endpoints,
                "schemas": schemas,
                "type_imports": _compute_type_imports(schemas),
                "go_std_imports": _compute_std_imports(endpoints),
            }

        rename_schemas(unversioned)
        self._annotate_endpoints(unversioned)
        unversioned_schemas = collect_schemas(unversioned)

        context = {
            "spec": self.spec,
            "go_package": self.go_package,
            "go_module": self.go_module,
            "client_version": self.version,
            "versions": versions_ctx,
            "endpoints": unversioned,
            "schemas": unversioned_schemas,
            "type_imports": _compute_type_imports(unversioned_schemas),
            "go_std_imports": _compute_root_std_imports(unversioned, versioned),
            "go_version_imports": [
                f"{self.go_module}/{v}" for v in sorted(versioned.keys())
            ],
        }

        render_tree(_GO_TEMPLATES_DIR, output_path, context, self._env)

        logger.info(
            "Generated Go client %s with %d endpoints in %s",
            self.go_package,
            len(self.spec.endpoints),
            output_path,
        )

        return output_path

    def _annotate_endpoints(self, endpoints: list[EndpointInfo]) -> None:
        """Add computed ``method_name`` attribute (PascalCase Go export)."""
        seen_names: dict[str, int] = {}

        for endpoint in endpoints:
            base_name = to_go_method_name(endpoint.name, endpoint.method, endpoint.path)
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
        env.filters["go_method_params"] = _go_method_params_filter
        env.filters["go_return_type"] = _go_return_type_filter
        env.filters["go_zero_return"] = _go_zero_return_filter
        env.filters["go_format_url"] = _go_format_url_filter
        env.filters["go_url_args"] = _go_url_args_filter
        env.filters["go_doc_path"] = _go_doc_path_filter
        env.filters["go_version_field"] = to_go_version_field
        env.filters["go_field_name"] = to_go_field_name
        env.filters["go_field_type"] = _go_field_type_filter
        env.filters["go_json_omitempty"] = _go_json_omitempty_filter
        env.filters["go_param_name"] = snake_to_camel
        return env


# ======================================================================
# Import computation
# ======================================================================


def _compute_type_imports(schemas) -> list[str]:
    """Compute Go imports needed for schema struct fields."""
    imports: set[str] = set()
    for schema in schemas:
        for field in schema.fields:
            imp = go_type_needs_import(field.field_type)
            if imp:
                imports.add(imp)
    return sorted(imports)


def _compute_std_imports(endpoints: list[EndpointInfo]) -> list[str]:
    """Compute standard library imports for a set of endpoints."""
    imports = {"encoding/json", "fmt", "io", "net/http"}
    if any(ep.has_body for ep in endpoints):
        imports.add("bytes")
    return sorted(imports)


def _compute_root_std_imports(
    unversioned: list[EndpointInfo],
    versioned: dict[str, list[EndpointInfo]],
) -> list[str]:
    """Compute standard library imports for the root client.go."""
    imports: set[str] = {"net/http"}
    if unversioned:
        imports.update({"encoding/json", "fmt", "io"})
        if any(ep.has_body for ep in unversioned):
            imports.add("bytes")
    return sorted(imports)


# ======================================================================
# Jinja2 filters
# ======================================================================


def _param_type_to_go(type_hint: str) -> str:
    """Convert a Python-style type hint to a Go type."""
    return PYTHON_TO_GO_TYPE.get(type_hint, "interface{}")


def _go_method_params_filter(endpoint: EndpointInfo) -> str:
    """Build a Go method parameter list."""
    parts: list[str] = []

    for p in endpoint.path_parameters:
        parts.append(f"{snake_to_camel(p.name)} string")

    if endpoint.request_schema:
        parts.append(f"req *{endpoint.request_schema.name}")
    else:
        for p in endpoint.body_parameters:
            go_type = _param_type_to_go(p.type_hint)
            if p.required:
                parts.append(f"{snake_to_camel(p.name)} {go_type}")
            else:
                parts.append(f"{snake_to_camel(p.name)} *{go_type}")

    if endpoint.querystring_schema:
        parts.append(f"query *{endpoint.querystring_schema.name}")
    else:
        for p in endpoint.querystring_parameters:
            go_type = _param_type_to_go(p.type_hint)
            parts.append(f"{snake_to_camel(p.name)} *{go_type}")

    return ", ".join(parts)


def _go_return_type_filter(endpoint: EndpointInfo) -> str:
    """Return the Go return type for an endpoint method."""
    if endpoint.response_schema:
        return f"*{endpoint.response_schema.name}"
    return "map[string]interface{}"


def _go_zero_return_filter(endpoint: EndpointInfo) -> str:
    """Return the zero value for the endpoint's return type."""
    return "nil"


def _go_format_url_filter(endpoint: EndpointInfo) -> str:
    """Convert a Pyramid path to a Go fmt.Sprintf format string.

    Path parameters (including those with regex) are replaced with %s.
    """
    path = re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)
    return re.sub(r"\{(\w+)\}", "%s", path)


def _go_url_args_filter(endpoint: EndpointInfo) -> str:
    """Build the fmt.Sprintf arguments for path parameters."""
    args = [snake_to_camel(p.name) for p in endpoint.path_parameters]
    if not args:
        return ""
    return ", " + ", ".join(args)


def _go_doc_path_filter(endpoint: EndpointInfo) -> str:
    """Clean regex from path for use in Go comments."""
    return re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)


def _go_field_type_filter(field_info: SchemaFieldInfo) -> str:
    """Map a SchemaFieldInfo to its Go type."""
    return to_go_type(field_info.field_type, field_info.required)


def _go_json_omitempty_filter(field_info: SchemaFieldInfo) -> str:
    """Return ',omitempty' for optional fields, empty string otherwise."""
    if not field_info.required:
        return ",omitempty"
    return ""
