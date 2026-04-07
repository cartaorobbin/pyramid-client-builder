"""Tests for pyramid_client_builder.models."""

from pyramid_introspector import ParameterInfo, SchemaFieldInfo, SchemaInfo

from pyramid_client_builder.models import ClientSpec, EndpointInfo


class TestParameterInfo:

    def test_defaults(self):
        param = ParameterInfo(name="id", location="path")
        assert param.required is True
        assert param.type_hint == "str"
        assert param.description == ""

    def test_all_fields(self):
        param = ParameterInfo(
            name="amount",
            location="body",
            required=True,
            type_hint="int",
            description="Amount in cents",
        )
        assert param.name == "amount"
        assert param.location == "body"
        assert param.type_hint == "int"
        assert param.description == "Amount in cents"


class TestSchemaFieldInfo:

    def test_defaults(self):
        field = SchemaFieldInfo(name="id", field_type="String")
        assert field.required is False
        assert field.metadata == {}

    def test_all_fields(self):
        field = SchemaFieldInfo(
            name="amount",
            field_type="Integer",
            required=True,
            metadata={"description": "Amount in cents"},
        )
        assert field.name == "amount"
        assert field.field_type == "Integer"
        assert field.required is True
        assert field.metadata == {"description": "Amount in cents"}


class TestSchemaInfo:

    def test_defaults(self):
        schema = SchemaInfo(name="ChargeRequestSchema")
        assert schema.fields == []

    def test_with_fields(self):
        fields = [
            SchemaFieldInfo(name="amount", field_type="Integer", required=True),
            SchemaFieldInfo(name="currency", field_type="String", required=True),
        ]
        schema = SchemaInfo(name="ChargeRequestSchema", fields=fields)
        assert schema.name == "ChargeRequestSchema"
        assert len(schema.fields) == 2
        assert schema.fields[0].name == "amount"


class TestEndpointInfo:

    def test_minimal(self):
        ep = EndpointInfo(name="home", path="/", method="GET")
        assert ep.path_parameters == []
        assert ep.querystring_parameters == []
        assert ep.body_parameters == []
        assert ep.has_body is False
        assert ep.request_schema is None
        assert ep.querystring_schema is None
        assert ep.response_schema is None

    def test_path_parameters_filtered(self):
        ep = EndpointInfo(
            name="charge_detail",
            path="/charges/{charge_id}",
            method="GET",
            parameters=[
                ParameterInfo(name="charge_id", location="path"),
                ParameterInfo(name="status", location="querystring", required=False),
            ],
        )
        assert len(ep.path_parameters) == 1
        assert ep.path_parameters[0].name == "charge_id"

    def test_querystring_parameters_filtered(self):
        ep = EndpointInfo(
            name="charges",
            path="/charges",
            method="GET",
            parameters=[
                ParameterInfo(name="status", location="querystring", required=False),
                ParameterInfo(name="page", location="querystring", required=False),
            ],
        )
        assert len(ep.querystring_parameters) == 2
        assert ep.path_parameters == []

    def test_body_parameters_and_has_body(self):
        ep = EndpointInfo(
            name="charges",
            path="/charges",
            method="POST",
            parameters=[
                ParameterInfo(name="amount", location="body", type_hint="int"),
                ParameterInfo(name="currency", location="body"),
            ],
        )
        assert ep.has_body is True
        assert len(ep.body_parameters) == 2

    def test_mixed_parameter_locations(self):
        ep = EndpointInfo(
            name="update",
            path="/charges/{id}",
            method="PUT",
            parameters=[
                ParameterInfo(name="id", location="path"),
                ParameterInfo(name="amount", location="body", type_hint="int"),
                ParameterInfo(name="expand", location="querystring", required=False),
            ],
        )
        assert len(ep.path_parameters) == 1
        assert len(ep.body_parameters) == 1
        assert len(ep.querystring_parameters) == 1

    def test_schema_references(self):
        req = SchemaInfo(name="ChargeRequestSchema")
        qs = SchemaInfo(name="ChargesQuerySchema")
        resp = SchemaInfo(name="ChargeResponseSchema")
        ep = EndpointInfo(
            name="charges",
            path="/charges",
            method="POST",
            request_schema=req,
            querystring_schema=qs,
            response_schema=resp,
        )
        assert ep.request_schema.name == "ChargeRequestSchema"
        assert ep.querystring_schema.name == "ChargesQuerySchema"
        assert ep.response_schema.name == "ChargeResponseSchema"

    def test_response_schemas_default_empty(self):
        ep = EndpointInfo(name="home", path="/", method="GET")
        assert ep.response_schemas == {}

    def test_response_schemas_dict(self):
        success = SchemaInfo(name="SuccessSchema")
        error = SchemaInfo(name="ErrorSchema")
        ep = EndpointInfo(name="charges", path="/charges", method="POST")
        ep.response_schemas = {200: success, 400: error}
        assert ep.response_schemas[200].name == "SuccessSchema"
        assert ep.response_schemas[400].name == "ErrorSchema"


class TestIsWildcard:
    """EndpointInfo.is_wildcard must detect Pyramid wildcards, not regex params."""

    def test_true_for_pyramid_wildcard(self):
        ep = EndpointInfo(name="static", path="static/*subpath", method="GET")
        assert ep.is_wildcard is True

    def test_true_for_traverse_wildcard(self):
        ep = EndpointInfo(name="traverse", path="/*traverse", method="GET")
        assert ep.is_wildcard is True

    def test_false_for_regex_path_param(self):
        ep = EndpointInfo(name="part", path="/api/v1/parts/{uuid:.*}", method="GET")
        assert ep.is_wildcard is False

    def test_false_for_digit_regex_param(self):
        ep = EndpointInfo(name="item", path="/items/{id:\\d+}", method="GET")
        assert ep.is_wildcard is False

    def test_false_for_clean_path(self):
        ep = EndpointInfo(name="items", path="/api/v1/items", method="GET")
        assert ep.is_wildcard is False

    def test_false_for_simple_param(self):
        ep = EndpointInfo(name="item", path="/items/{id}", method="GET")
        assert ep.is_wildcard is False

    def test_true_for_wildcard_alongside_regex_param(self):
        ep = EndpointInfo(
            name="mixed",
            path="/api/{version:\\d+}/*remainder",
            method="GET",
        )
        assert ep.is_wildcard is True


class TestClientSpec:

    def test_settings_prefix_defaults_to_name(self):
        spec = ClientSpec(name="payments")
        assert spec.settings_prefix == "payments"
        assert spec.endpoints == []
        assert spec.schemas == []

    def test_custom_settings_prefix(self):
        spec = ClientSpec(name="payments", settings_prefix="pay")
        assert spec.settings_prefix == "pay"

    def test_with_endpoints(self):
        endpoints = [
            EndpointInfo(name="home", path="/", method="GET"),
            EndpointInfo(name="health", path="/health", method="GET"),
        ]
        spec = ClientSpec(name="example", endpoints=endpoints)
        assert len(spec.endpoints) == 2

    def test_with_schemas(self):
        schemas = [
            SchemaInfo(name="ChargeRequestSchema"),
            SchemaInfo(name="ChargesQuerySchema"),
        ]
        spec = ClientSpec(name="example", schemas=schemas)
        assert len(spec.schemas) == 2
        assert spec.schemas[0].name == "ChargeRequestSchema"
