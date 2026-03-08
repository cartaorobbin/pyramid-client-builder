"""Data models for representing introspected Pyramid endpoints."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParameterInfo:
    """A single parameter extracted from a route or schema."""

    name: str
    location: str  # "path", "querystring", "body"
    required: bool = True
    type_hint: str = "str"
    description: str = ""


@dataclass
class SchemaFieldInfo:
    """A single field in a Marshmallow schema, captured for code generation."""

    name: str
    field_type: str  # Marshmallow field class name, e.g. "Integer", "String"
    required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaInfo:
    """A Marshmallow schema captured from introspection, ready for generation."""

    name: str
    fields: list[SchemaFieldInfo] = field(default_factory=list)


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
class ClientSpec:
    """Full specification for generating a client package."""

    name: str
    endpoints: list[EndpointInfo] = field(default_factory=list)
    settings_prefix: str = ""
    schemas: list[SchemaInfo] = field(default_factory=list)

    def __post_init__(self):
        if not self.settings_prefix:
            self.settings_prefix = self.name
