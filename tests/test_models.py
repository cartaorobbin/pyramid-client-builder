"""Tests for pyramid_client_builder.models."""

from pyramid_client_builder.models import ClientSpec, EndpointInfo, ParameterInfo


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


class TestEndpointInfo:

    def test_minimal(self):
        ep = EndpointInfo(name="home", path="/", method="GET")
        assert ep.path_parameters == []
        assert ep.querystring_parameters == []
        assert ep.body_parameters == []
        assert ep.has_body is False

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


class TestClientSpec:

    def test_settings_prefix_defaults_to_name(self):
        spec = ClientSpec(name="payments")
        assert spec.settings_prefix == "payments"
        assert spec.endpoints == []

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
