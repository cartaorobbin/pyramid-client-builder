"""Tests for the Go client generator."""

import pytest
from pyramid_introspector import ParameterInfo, SchemaFieldInfo, SchemaInfo

from pyramid_client_builder.generator.go_core import GoClientGenerator
from pyramid_client_builder.introspection import PyramidIntrospector
from pyramid_client_builder.models import ClientSpec, EndpointInfo


@pytest.fixture()
def simple_spec():
    """A minimal ClientSpec for testing Go generation."""
    return ClientSpec(
        name="testapp",
        endpoints=[
            EndpointInfo(name="home", path="/", method="GET", description="Home page"),
            EndpointInfo(
                name="items",
                path="/api/v1/items",
                method="GET",
                description="List items",
                parameters=[
                    ParameterInfo(
                        name="status",
                        location="querystring",
                        required=False,
                        type_hint="str",
                    ),
                ],
            ),
            EndpointInfo(
                name="items",
                path="/api/v1/items",
                method="POST",
                description="Create item",
                parameters=[
                    ParameterInfo(name="name", location="body", type_hint="str"),
                    ParameterInfo(name="price", location="body", type_hint="int"),
                ],
            ),
            EndpointInfo(
                name="item_detail",
                path="/api/v1/items/{item_id}",
                method="GET",
                description="Get item",
                parameters=[
                    ParameterInfo(name="item_id", location="path"),
                ],
            ),
        ],
    )


@pytest.fixture()
def flat_spec():
    """A ClientSpec with NO versioned paths — triggers flat output."""
    return ClientSpec(
        name="myapp",
        endpoints=[
            EndpointInfo(name="home", path="/", method="GET", description="Home"),
            EndpointInfo(
                name="items",
                path="/items",
                method="POST",
                description="Create",
                parameters=[
                    ParameterInfo(name="name", location="body", type_hint="str"),
                ],
            ),
        ],
    )


@pytest.fixture()
def example_spec(example_registry):
    """ClientSpec built from the real example app."""
    introspector = PyramidIntrospector(example_registry)
    return introspector.build_client_spec("example")


# ======================================================================
# Simple spec (has versioned /api/v1/ endpoints -> versioned output)
# ======================================================================


class TestGoGeneratorWithSimpleSpec:

    def test_creates_output_directory(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        result = gen.generate(tmp_path)
        assert result.exists()

    def test_generates_go_mod(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "go.mod").exists()

    def test_go_mod_contains_module(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        content = (tmp_path / "go.mod").read_text()
        assert "module testapp-client" in content
        assert "go 1.21" in content

    def test_generates_client_go(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "client.go").exists()

    def test_generates_readme(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "README.md").exists()

    def test_generates_v1_directory(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "v1").is_dir()
        assert (tmp_path / "v1" / "client.go").exists()

    def test_no_types_file_without_schemas(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "types.go").exists()
        assert not (tmp_path / "v1" / "types.go").exists()

    def test_root_client_has_package_declaration(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "package testappclient" in source

    def test_root_client_has_v1_field(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "V1 *v1.Client" in source

    def test_root_client_has_new_client(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func NewClient(baseURL string, opts ...Option) *Client" in source

    def test_root_client_has_option_pattern(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "type Option func(*Client)" in source
        assert "func WithAuthToken(token string) Option" in source
        assert "func WithHTTPClient(hc *http.Client) Option" in source

    def test_root_client_has_unversioned_methods(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func (c *Client) GetHome()" in source

    def test_root_client_imports_version_package(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert '"testapp-client/v1"' in source

    def test_v1_client_has_package_declaration(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "package v1" in source

    def test_v1_client_has_versioned_methods(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "func (c *Client) ListItems(" in source
        assert "func (c *Client) CreateItem(" in source
        assert "func (c *Client) GetItem(" in source

    def test_v1_client_has_constructor(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        expected = (
            "func NewClient(baseURL string, httpClient *http.Client,"
            " authToken string, authTokenFunc func() string)"
        )
        assert expected in source

    def test_custom_go_module(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec, go_module="github.com/org/testapp-client")
        gen.generate(tmp_path)
        content = (tmp_path / "go.mod").read_text()
        assert "module github.com/org/testapp-client" in content

    def test_custom_go_module_in_version_import(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec, go_module="github.com/org/testapp-client")
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert '"github.com/org/testapp-client/v1"' in source


# ======================================================================
# Flat spec (no versioned paths -> flat output)
# ======================================================================


class TestGoGeneratorWithFlatSpec:

    def test_flat_output_has_no_version_dirs(self, flat_spec, tmp_path):
        gen = GoClientGenerator(flat_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "v1").exists()

    def test_flat_output_methods_on_root_client(self, flat_spec, tmp_path):
        gen = GoClientGenerator(flat_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func (c *Client) GetHome()" in source
        assert "func (c *Client) CreateItems(" in source

    def test_flat_client_has_no_version_imports(self, flat_spec, tmp_path):
        gen = GoClientGenerator(flat_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "/v1" not in source


# ======================================================================
# Example app (real Pyramid + Cornice -> versioned output)
# ======================================================================


class TestGoGeneratorWithExampleApp:

    def test_generates_from_real_app(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "client.go").exists()
        assert (tmp_path / "v1" / "client.go").exists()

    def test_go_mod_exists(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "go.mod").exists()

    def test_verb_naming_in_v1_client(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "func (c *Client) CancelCharge(" in source

    def test_list_naming_for_collections(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "func (c *Client) ListCharges(" in source
        assert "func (c *Client) ListInvoices(" in source

    def test_root_has_unversioned_endpoints(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func (c *Client) GetHome()" in source
        assert "func (c *Client) GetHealth()" in source

    def test_root_has_v1_field(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "V1 *v1.Client" in source


# ======================================================================
# Schema generation (Go structs)
# ======================================================================


class TestGoSchemaGeneration:

    def test_generates_types_file_with_schemas(self, tmp_path):
        schema = SchemaInfo(
            name="ChargesRequestSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
                SchemaFieldInfo(name="currency", field_type="String", required=True),
                SchemaFieldInfo(
                    name="description", field_type="String", required=False
                ),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                        ParameterInfo(
                            name="currency", location="body", type_hint="str"
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        assert (tmp_path / "v1" / "types.go").exists()

    def test_types_file_contains_struct(self, tmp_path):
        schema = SchemaInfo(
            name="ChargesRequestSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
                SchemaFieldInfo(name="currency", field_type="String", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargesRequestSchema struct" in source

    def test_types_file_has_json_tags(self, tmp_path):
        schema = SchemaInfo(
            name="ItemSchema",
            fields=[
                SchemaFieldInfo(name="item_name", field_type="String", required=True),
                SchemaFieldInfo(name="price", field_type="Integer", required=True),
            ],
        )
        spec = ClientSpec(
            name="shop",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="item_name", location="body", type_hint="str"
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert '`json:"item_name"`' in source
        assert '`json:"price"`' in source

    def test_optional_field_has_omitempty(self, tmp_path):
        schema = SchemaInfo(
            name="ItemSchema",
            fields=[
                SchemaFieldInfo(
                    name="description", field_type="String", required=False
                ),
            ],
        )
        spec = ClientSpec(
            name="shop",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="description", location="body", type_hint="str"
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert '`json:"description,omitempty"`' in source

    def test_optional_field_has_pointer_type(self, tmp_path):
        schema = SchemaInfo(
            name="ItemSchema",
            fields=[
                SchemaFieldInfo(
                    name="description", field_type="String", required=False
                ),
            ],
        )
        spec = ClientSpec(
            name="shop",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="description", location="body", type_hint="str"
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "*string" in source

    def test_types_file_has_go_types(self, tmp_path):
        schema = SchemaInfo(
            name="ChargeSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
                SchemaFieldInfo(name="currency", field_type="String", required=True),
                SchemaFieldInfo(name="active", field_type="Boolean", required=True),
                SchemaFieldInfo(name="rate", field_type="Float", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "int" in source
        assert "string" in source
        assert "bool" in source
        assert "float64" in source

    def test_datetime_field_imports_time(self, tmp_path):
        schema = SchemaInfo(
            name="EventSchema",
            fields=[
                SchemaFieldInfo(
                    name="created_at", field_type="DateTime", required=True
                ),
            ],
        )
        spec = ClientSpec(
            name="events",
            endpoints=[
                EndpointInfo(
                    name="events",
                    path="/api/v1/events",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="created_at", location="body", type_hint="str"
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert '"time"' in source
        assert "time.Time" in source

    def test_no_types_file_without_schemas(self, tmp_path):
        spec = ClientSpec(
            name="simple",
            endpoints=[
                EndpointInfo(name="home", path="/", method="GET"),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "types.go").exists()


# ======================================================================
# Method signatures
# ======================================================================


class TestGoMethodSignatures:

    def test_schema_body_uses_struct_param(self, tmp_path):
        schema = SchemaInfo(
            name="ChargesRequestSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "req *ChargesRequestSchema" in source

    def test_no_schema_body_uses_individual_params(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "func (c *Client) CreateItem(name string, price int)" in source

    def test_path_params_are_string(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "func (c *Client) GetItem(itemId string)" in source

    def test_query_schema_uses_struct_param(self, tmp_path):
        schema = SchemaInfo(
            name="ChargesQuerySchema",
            fields=[
                SchemaFieldInfo(name="status", field_type="String", required=False),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="GET",
                    querystring_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="status",
                            location="querystring",
                            required=False,
                            type_hint="str",
                        ),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "query *ChargesQuerySchema" in source

    def test_no_schema_query_uses_pointer_params(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "status *string" in source

    def test_response_schema_returns_pointer(self, tmp_path):
        response_schema = SchemaInfo(
            name="ChargeResponseSchema",
            fields=[
                SchemaFieldInfo(name="id", field_type="String", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="GET",
                    response_schema=response_schema,
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "(*ChargeResponseSchema, error)" in source

    def test_no_response_schema_returns_map(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "(map[string]interface{}, error)" in source


# ======================================================================
# HTTP method handling
# ======================================================================


class TestGoHttpMethods:

    def test_get_uses_nil_body(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert 'http.NewRequest("GET"' in source
        assert "nil)" in source

    def test_post_uses_body(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert 'http.NewRequest("POST"' in source
        assert "json.Marshal" in source

    def test_error_handling(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "resp.StatusCode >= 400" in source
        assert "io.ReadAll" in source


# ======================================================================
# Import management
# ======================================================================


class TestGoImports:

    def test_root_with_no_unversioned_endpoints_minimal_imports(self, tmp_path):
        spec = ClientSpec(
            name="versioned",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="GET",
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert '"net/http"' in source
        assert '"encoding/json"' not in source

    def test_root_with_unversioned_endpoints_full_imports(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert '"net/http"' in source
        assert '"encoding/json"' in source
        assert '"fmt"' in source
        assert '"io"' in source

    def test_v1_client_has_full_imports(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert '"net/http"' in source
        assert '"encoding/json"' in source
        assert '"bytes"' in source

    def test_v1_client_no_bytes_without_body(self, tmp_path):
        spec = ClientSpec(
            name="readonly",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="GET",
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert '"bytes"' not in source


# ======================================================================
# Schema renaming
# ======================================================================


class TestGoSchemaRenaming:

    def test_generic_schema_renamed_for_request(self, tmp_path):
        schema = SchemaInfo(
            name="ChargeSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargesRequestSchema struct" in source
        assert "ChargeSchema" not in source

    def test_role_suffixed_schema_not_renamed(self, tmp_path):
        schema = SchemaInfo(
            name="ChargeRequestSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="amount", location="body", type_hint="int"),
                    ],
                ),
            ],
        )
        gen = GoClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargeRequestSchema struct" in source


# ======================================================================
# Method name deduplication
# ======================================================================


class TestGoMethodNameDeduplication:

    def test_duplicate_names_get_suffix(self):
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
            ],
        )
        gen = GoClientGenerator(spec)
        gen._annotate_endpoints(spec.endpoints)
        names = [ep.method_name for ep in spec.endpoints]  # type: ignore[attr-defined]
        assert names[0] == "ListThings"
        assert names[1] == "ListThings1"


# ======================================================================
# Example app with schemas
# ======================================================================


class TestGoExampleAppSchemas:

    def test_v1_types_file_exists(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "v1" / "types.go").exists()

    def test_v1_types_has_request_struct(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargeRequestSchema struct" in source

    def test_v1_types_has_response_struct(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargeResponseSchema struct" in source

    def test_v1_types_has_query_struct(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "types.go").read_text()
        assert "type ChargesQuerySchema struct" in source

    def test_v1_client_uses_schema_param(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "req *ChargeRequestSchema" in source

    def test_v1_client_uses_query_schema_param(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "query *ChargesQuerySchema" in source

    def test_v1_client_returns_response_schema(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "*ChargeResponseSchema" in source

    def test_no_root_types_file(self, example_spec, tmp_path):
        gen = GoClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "types.go").exists()


# ======================================================================
# Callable token provider
# ======================================================================


class TestGoCallableTokenProvider:
    """Verify generated Go client supports authTokenFunc."""

    def test_root_client_has_auth_token_func_field(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "authTokenFunc func() string" in source

    def test_root_client_has_with_auth_token_func_option(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func WithAuthTokenFunc(fn func() string) Option" in source

    def test_root_client_do_checks_func_first(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "if c.authTokenFunc != nil" in source

    def test_root_client_do_falls_back_to_static(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert '} else if c.authToken != ""' in source

    def test_v1_client_has_auth_token_func_field(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "authTokenFunc func() string" in source

    def test_v1_client_do_checks_func_first(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "v1" / "client.go").read_text()
        assert "if c.authTokenFunc != nil" in source

    def test_root_passes_func_to_subclient(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "c.authTokenFunc)" in source

    def test_with_auth_token_still_works(self, simple_spec, tmp_path):
        gen = GoClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "client.go").read_text()
        assert "func WithAuthToken(token string) Option" in source
        assert "c.authToken = token" in source
