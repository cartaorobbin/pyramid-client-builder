"""Client code generator.

Takes a ClientSpec and renders Jinja2 templates into a Python package
on disk.
"""

import logging
import re
from pathlib import Path

from jinja2 import Environment, PackageLoader
from pyramid_introspector import SchemaFieldInfo

from pyramid_client_builder.generator.naming import (
    to_class_name,
    to_method_name,
    to_package_name,
    to_request_attr,
)
from pyramid_client_builder.models import ClientSpec, EndpointInfo

logger = logging.getLogger(__name__)


class ClientGenerator:
    """Generates a Python client package from a ClientSpec."""

    def __init__(self, spec: ClientSpec):
        self.spec = spec
        self.class_name = to_class_name(spec.name)
        self.package_name = to_package_name(spec.name)
        self.request_attr = to_request_attr(spec.name)
        self._env = self._create_jinja_env()

    def generate(self, output_dir: str | Path) -> Path:
        """Write the generated client package to output_dir.

        Args:
            output_dir: Directory to create the package in. The package
                subdirectory is created inside this path.

        Returns:
            Path to the generated package directory.
        """
        output_path = Path(output_dir)
        package_dir = output_path / self.package_name
        package_dir.mkdir(parents=True, exist_ok=True)

        self._annotate_endpoints()

        context = {
            "spec": self.spec,
            "class_name": self.class_name,
            "package_name": self.package_name,
            "request_attr": self.request_attr,
        }

        self._render_template("__init__.py.j2", package_dir / "__init__.py", context)
        if self.spec.schemas:
            self._render_template(
                "schemas.py.j2", package_dir / "schemas.py", context
            )
        self._render_template("client.py.j2", package_dir / "client.py", context)
        self._render_template("ext.py.j2", package_dir / "ext.py", context)

        logger.info(
            "Generated %s with %d endpoints in %s",
            self.class_name,
            len(self.spec.endpoints),
            package_dir,
        )

        return package_dir

    def _annotate_endpoints(self) -> None:
        """Add computed attributes to endpoints for template rendering."""
        seen_names: dict[str, int] = {}

        for endpoint in self.spec.endpoints:
            base_name = to_method_name(endpoint.name, endpoint.method, endpoint.path)
            count = seen_names.get(base_name, 0)
            seen_names[base_name] = count + 1

            method_name = base_name if count == 0 else f"{base_name}_{count}"
            endpoint.method_name = method_name  # type: ignore[attr-defined]

    def _render_template(
        self, template_name: str, output_file: Path, context: dict
    ) -> None:
        """Render a single template to a file."""
        template = self._env.get_template(template_name)
        content = template.render(**context)
        output_file.write_text(content + "\n")

    def _create_jinja_env(self) -> Environment:
        """Create a Jinja2 environment with custom filters."""
        env = Environment(
            loader=PackageLoader(
                "pyramid_client_builder.generator", "templates"
            ),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["method_signature"] = _method_signature_filter
        env.filters["format_url"] = _format_url_filter
        env.filters["format_doc_path"] = _format_doc_path_filter
        env.filters["field_kwargs"] = _field_kwargs_filter
        env.filters["body_dict_literal"] = _body_dict_literal_filter
        env.filters["qs_dict_literal"] = _qs_dict_literal_filter
        return env


def _method_signature_filter(endpoint: EndpointInfo) -> str:
    """Build a Python method signature string from endpoint parameters.

    Required parameters come first (path, then required body), followed
    by optional parameters (optional body, then querystring) with None
    defaults.
    """
    required: list[str] = []
    optional: list[str] = []

    for p in endpoint.path_parameters:
        required.append(f"{p.name}: {p.type_hint}")

    for p in endpoint.body_parameters:
        if p.required:
            required.append(f"{p.name}: {p.type_hint}")
        else:
            optional.append(f"{p.name}: {p.type_hint} | None = None")

    for p in endpoint.querystring_parameters:
        optional.append(f"{p.name}: {p.type_hint} | None = None")

    parts = required + optional
    if not parts:
        return ""
    return ", " + ", ".join(parts)


def _format_url_filter(endpoint: EndpointInfo) -> str:
    """Convert a Pyramid path pattern to an f-string expression.

    "/api/v1/charges/{charge_id}" -> "/api/v1/charges/{charge_id}"

    Pyramid patterns with regex like {id:\\d+} become {id}.
    """
    return re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)


def _format_doc_path_filter(endpoint: EndpointInfo) -> str:
    """Clean regex from path for use in docstrings.

    "/api/v1/charges/{charge_id:.*}" -> "/api/v1/charges/{charge_id}"
    """
    return re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)


def _field_kwargs_filter(field_info: SchemaFieldInfo) -> str:
    """Render Marshmallow field constructor keyword arguments."""
    parts: list[str] = []
    if field_info.required:
        parts.append("required=True")
    if field_info.metadata:
        parts.append(f"metadata={field_info.metadata!r}")
    return ", ".join(parts)


def _body_dict_literal_filter(endpoint: EndpointInfo) -> str:
    """Build a dict literal string from body parameters for schema.dump()."""
    pairs = [f'"{p.name}": {p.name}' for p in endpoint.body_parameters]
    return ", ".join(pairs)


def _qs_dict_literal_filter(endpoint: EndpointInfo) -> str:
    """Build a dict literal string from querystring parameters for schema.dump()."""
    pairs = [f'"{p.name}": {p.name}' for p in endpoint.querystring_parameters]
    return ", ".join(pairs)
