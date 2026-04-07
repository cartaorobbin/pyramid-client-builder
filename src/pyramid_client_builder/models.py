"""Data models for the client generation pipeline.

Shared introspection models (ParameterInfo, SchemaInfo, SchemaFieldInfo)
come from pyramid_introspector. This module defines the client-builder-specific
models that flatten route/view pairs into endpoints and bundle them into a spec.
"""

import re
from dataclasses import dataclass, field

from pyramid_introspector import ParameterInfo, SchemaInfo

_PARAM_BLOCK = re.compile(r"\{[^}]*\}")


@dataclass
class EndpointInfo:
    """A single HTTP endpoint discovered from a Pyramid app."""

    name: str
    path: str
    method: str
    description: str = ""
    parameters: list[ParameterInfo] = field(default_factory=list)
    request_schema: SchemaInfo | None = None
    querystring_schema: SchemaInfo | None = None
    response_schema: SchemaInfo | None = None
    response_schemas: dict[int, SchemaInfo] = field(default_factory=dict)

    @property
    def is_wildcard(self) -> bool:
        """True when path contains a Pyramid wildcard (``*name``).

        Regex patterns inside path parameters (e.g. ``{uuid:.*}``) are
        stripped before checking so they are not mistaken for wildcards.
        """
        return "*" in _PARAM_BLOCK.sub("", self.path)

    @property
    def path_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "path"]

    @property
    def querystring_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "querystring"]

    @property
    def body_parameters(self) -> list[ParameterInfo]:
        return [p for p in self.parameters if p.location == "body"]

    @property
    def has_body(self) -> bool:
        return len(self.body_parameters) > 0


@dataclass
class CustomFieldInfo:
    """A custom Marshmallow field that must be shipped with the generated client.

    Captured during introspection when a schema uses a field type that is
    not part of the standard ``marshmallow.fields`` module.
    """

    class_name: str
    base_type: str


@dataclass
class ClientSpec:
    """Full specification for generating a client package."""

    name: str
    endpoints: list[EndpointInfo] = field(default_factory=list)
    settings_prefix: str = ""
    schemas: list[SchemaInfo] = field(default_factory=list)
    custom_fields: list[CustomFieldInfo] = field(default_factory=list)

    def __post_init__(self):
        if not self.settings_prefix:
            self.settings_prefix = self.name
