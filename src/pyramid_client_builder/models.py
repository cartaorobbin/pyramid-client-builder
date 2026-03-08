"""Data models for representing introspected Pyramid endpoints."""

from dataclasses import dataclass, field


@dataclass
class ParameterInfo:
    """A single parameter extracted from a route or schema."""

    name: str
    location: str  # "path", "querystring", "body"
    required: bool = True
    type_hint: str = "str"
    description: str = ""


@dataclass
class EndpointInfo:
    """A single HTTP endpoint discovered from a Pyramid app."""

    name: str
    path: str
    method: str
    description: str = ""
    parameters: list[ParameterInfo] = field(default_factory=list)
    response_schema_name: str | None = None

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

    def __post_init__(self):
        if not self.settings_prefix:
            self.settings_prefix = self.name
