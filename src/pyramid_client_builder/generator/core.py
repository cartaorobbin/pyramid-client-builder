"""Client code generator.

Takes a ClientSpec and renders Jinja2 templates into a Python package
on disk.  Uses a template directory tree that mirrors the output structure.
An ``@each(versions)`` directory handles per-version subdirectories.
"""

import logging
import re
from importlib.resources import files as package_files
from pathlib import Path

from jinja2 import Environment
from pyramid_introspector import SchemaFieldInfo, SchemaInfo

from pyramid_client_builder.generator.naming import (
    extract_version,
    needs_schema_rename,
    to_class_name,
    to_method_name,
    to_package_name,
    to_project_name,
    to_request_attr,
    to_schema_name,
)
from pyramid_client_builder.generator.renderer import render_tree
from pyramid_client_builder.models import ClientSpec, EndpointInfo

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = package_files("pyramid_client_builder.generator").joinpath("templates")


class ClientGenerator:
    """Generates a Python client package from a ClientSpec."""

    def __init__(
        self,
        spec: ClientSpec,
        version: str = "0.1.0",
        http_client: str = "requests",
    ):
        self.spec = spec
        self.version = version
        self.http_client = http_client
        self.class_name = to_class_name(spec.name)
        self.package_name = to_package_name(spec.name)
        self.project_name = to_project_name(spec.name)
        self.request_attr = to_request_attr(spec.name)
        self._env = self._create_jinja_env()

    def generate(self, output_dir: str | Path) -> Path:
        """Write the generated client project to output_dir.

        The template directory tree is walked once.  A ``{{package_name}}``
        directory in the tree mirrors the Python package, while project-level
        files (``pyproject.toml``, ``README.md``) sit at the root.  An
        ``@each(versions)`` subdirectory creates per-version output
        directories automatically.  When no versioned endpoints exist, the
        versions dict is empty and the loop creates nothing (flat layout).
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        versioned, unversioned = _group_by_version(self.spec.endpoints)

        versions_ctx: dict[str, dict] = {}
        for version in sorted(versioned.keys()):
            endpoints = versioned[version]
            _rename_schemas(endpoints)
            self._annotate_endpoints(endpoints)
            schemas = _collect_schemas(endpoints)
            versions_ctx[version] = {
                "version": version,
                "version_class_name": _version_class_name(version),
                "endpoints": endpoints,
                "schemas": schemas,
            }

        _rename_schemas(unversioned)
        self._annotate_endpoints(unversioned)
        unversioned_schemas = _collect_schemas(unversioned)

        has_schemas = bool(unversioned_schemas) or any(
            v["schemas"] for v in versions_ctx.values()
        )

        context = {
            "spec": self.spec,
            "class_name": self.class_name,
            "package_name": self.package_name,
            "project_name": self.project_name,
            "client_version": self.version,
            "http_client": self.http_client,
            "has_schemas": has_schemas,
            "request_attr": self.request_attr,
            "versions": versions_ctx,
            "endpoints": unversioned,
            "schemas": unversioned_schemas,
        }

        render_tree(_TEMPLATES_DIR, output_path, context, self._env)

        package_dir = output_path / self.package_name

        logger.info(
            "Generated %s with %d endpoints in %s",
            self.class_name,
            len(self.spec.endpoints),
            package_dir,
        )

        return package_dir

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _annotate_endpoints(self, endpoints: list[EndpointInfo]) -> None:
        """Add computed ``method_name`` attribute for template rendering."""
        seen_names: dict[str, int] = {}

        for endpoint in endpoints:
            base_name = to_method_name(endpoint.name, endpoint.method, endpoint.path)
            count = seen_names.get(base_name, 0)
            seen_names[base_name] = count + 1

            method_name = base_name if count == 0 else f"{base_name}_{count}"
            endpoint.method_name = method_name  # type: ignore[attr-defined]

    def _create_jinja_env(self) -> Environment:
        env = Environment(
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
        env.filters["version_class_name"] = _version_class_name
        return env


# ======================================================================
# Module-level helpers
# ======================================================================


def _group_by_version(
    endpoints: list[EndpointInfo],
) -> tuple[dict[str, list[EndpointInfo]], list[EndpointInfo]]:
    """Split endpoints into versioned groups and an unversioned remainder."""
    versioned: dict[str, list[EndpointInfo]] = {}
    unversioned: list[EndpointInfo] = []

    for ep in endpoints:
        version = extract_version(ep.path)
        if version:
            versioned.setdefault(version, []).append(ep)
        else:
            unversioned.append(ep)

    return versioned, unversioned


def _rename_schemas(endpoints: list[EndpointInfo]) -> None:
    """Rename schemas that lack a role suffix based on endpoint path + role.

    Mutates ``SchemaInfo.name`` in place.  Skips schemas whose name
    already ends with a recognized role suffix (e.g. ``RequestSchema``).
    Skips schemas where the generated name conflicts with another schema's
    original name or where the same schema would get different names from
    different endpoints.
    """
    rename_map: dict[str, str] = {}
    conflicts: set[str] = set()
    all_original_names: set[str] = set()

    for ep in endpoints:
        for schema in _iter_schemas(ep):
            all_original_names.add(schema.name)

    role_attrs = [
        ("request_schema", "request"),
        ("querystring_schema", "querystring"),
        ("response_schema", "response"),
    ]
    for ep in endpoints:
        for attr, role in role_attrs:
            schema = getattr(ep, attr)
            if schema is None or not needs_schema_rename(schema.name):
                continue
            new_name = to_schema_name(ep.path, role)
            if new_name is None or new_name in all_original_names:
                continue
            original = schema.name
            if original in conflicts:
                continue
            if original in rename_map:
                if rename_map[original] != new_name:
                    conflicts.add(original)
                continue
            rename_map[original] = new_name

    for name in conflicts:
        rename_map.pop(name, None)

    if not rename_map:
        return

    for ep in endpoints:
        for schema in _iter_schemas(ep):
            if schema.name in rename_map:
                schema.name = rename_map[schema.name]


def _iter_schemas(endpoint: EndpointInfo):
    """Yield all non-None SchemaInfo objects from an endpoint."""
    for attr in ("request_schema", "querystring_schema", "response_schema"):
        schema = getattr(endpoint, attr)
        if schema is not None:
            yield schema
    yield from endpoint.response_schemas.values()


def _collect_schemas(endpoints: list[EndpointInfo]) -> list[SchemaInfo]:
    """Gather unique schemas referenced by endpoints (by name)."""
    seen: set[str] = set()
    schemas: list[SchemaInfo] = []

    for ep in endpoints:
        for schema in _iter_schemas(ep):
            if schema.name not in seen:
                seen.add(schema.name)
                schemas.append(schema)

    return schemas


def _version_class_name(version: str) -> str:
    """Convert a version string to a PascalCase class name: v1 -> V1Client."""
    return f"{version.upper()}Client"


# ======================================================================
# Jinja2 filters
# ======================================================================


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

    Pyramid patterns with regex like {id:\\d+} become {id}.
    """
    return re.sub(r"\{(\w+)(?::.*?)\}", r"{\1}", endpoint.path)


def _format_doc_path_filter(endpoint: EndpointInfo) -> str:
    """Clean regex from path for use in docstrings."""
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
