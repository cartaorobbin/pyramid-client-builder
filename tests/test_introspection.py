"""Tests for pyramid_client_builder.introspection."""

import marshmallow as ma
from pyramid_introspector import ParameterInfo, RouteInfo, SchemaInfo, ViewInfo

from pyramid_client_builder.introspection import (
    PyramidIntrospector,
    _detect_custom_fields,
    _resolve_base_marshmallow_type,
    _routes_to_endpoints,
)


class TestRoutesToEndpoints:
    """Tests for the RouteInfo/ViewInfo -> EndpointInfo conversion."""

    def test_flattens_routes_and_views(self):
        routes = [
            RouteInfo(
                name="things",
                pattern="/api/v1/things",
                views=[
                    ViewInfo(method="GET", description="List things"),
                    ViewInfo(method="POST", description="Create thing"),
                ],
            ),
        ]
        endpoints = _routes_to_endpoints(routes)
        assert len(endpoints) == 2
        assert endpoints[0].name == "things"
        assert endpoints[0].path == "/api/v1/things"
        assert endpoints[0].method == "GET"
        assert endpoints[0].description == "List things"
        assert endpoints[1].method == "POST"

    def test_carries_over_parameters(self):
        routes = [
            RouteInfo(
                name="thing_detail",
                pattern="/api/v1/things/{thing_id}",
                views=[
                    ViewInfo(
                        method="GET",
                        parameters=[
                            ParameterInfo(name="thing_id", location="path"),
                        ],
                    ),
                ],
            ),
        ]
        endpoints = _routes_to_endpoints(routes)
        assert len(endpoints[0].parameters) == 1
        assert endpoints[0].parameters[0].name == "thing_id"

    def test_carries_over_schemas(self):
        req = SchemaInfo(name="RequestSchema")
        resp = SchemaInfo(name="ResponseSchema")
        routes = [
            RouteInfo(
                name="things",
                pattern="/api/v1/things",
                views=[
                    ViewInfo(
                        method="POST",
                        request_schema=req,
                        response_schema=resp,
                        response_schemas={200: resp},
                    ),
                ],
            ),
        ]
        endpoints = _routes_to_endpoints(routes)
        assert endpoints[0].request_schema.name == "RequestSchema"
        assert endpoints[0].response_schema.name == "ResponseSchema"
        assert 200 in endpoints[0].response_schemas


class TestPyramidIntrospector:

    def test_build_client_spec(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        assert spec.name == "example"
        assert len(spec.endpoints) > 0

    def test_filters_out_head_and_options(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        methods = {ep.method for ep in spec.endpoints}
        assert "HEAD" not in methods
        assert "OPTIONS" not in methods

    def test_include_patterns(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec(
            "example", include_patterns=["/api/v1/charges*"]
        )
        for ep in spec.endpoints:
            assert ep.path.startswith("/api/v1/charges")

    def test_exclude_patterns(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec(
            "example", exclude_patterns=["/api/v1/invoices"]
        )
        paths = {ep.path for ep in spec.endpoints}
        assert "/api/v1/invoices" not in paths

    def test_deduplication(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        keys = [(ep.path, ep.method) for ep in spec.endpoints]
        assert len(keys) == len(set(keys))

    def test_collects_schemas(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        schema_names = {s.name for s in spec.schemas}
        assert "ChargeRequestSchema" in schema_names
        assert "ChargesQuerySchema" in schema_names
        assert "InvoiceQuerySchema" in schema_names
        assert "ChargeResponseSchema" in schema_names
        assert "RefundBodySchema" in schema_names
        assert "RefundQuerySchema" in schema_names
        assert "SimulateBodySchema" in schema_names
        assert "SimulateQuerySchema" in schema_names
        assert "SimulateResponseSchema" in schema_names

    def test_collects_error_schemas_from_response_schemas(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        schema_names = {s.name for s in spec.schemas}
        assert "RequestErrorSchema" in schema_names

    def test_schemas_are_deduplicated(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        names = [s.name for s in spec.schemas]
        assert len(names) == len(set(names))

    def test_detects_custom_fields(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        names = {cf.class_name for cf in spec.custom_fields}
        assert "CurrencyField" in names

    def test_custom_field_has_correct_base_type(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        by_name = {cf.class_name: cf for cf in spec.custom_fields}
        assert by_name["CurrencyField"].base_type == "String"

    def test_no_standard_fields_in_custom_fields(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        custom_names = {cf.class_name for cf in spec.custom_fields}
        standard = {"String", "Integer", "Float", "Boolean", "Dict", "Nested"}
        assert custom_names.isdisjoint(standard)


class TestRegexPathParamEndpoints:
    """Regex path params like {uuid:.*} must survive the full pipeline."""

    def test_get_and_delete_on_regex_path_both_in_spec(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        regex_endpoints = [
            ep for ep in spec.endpoints if "parts" in ep.path and "{uuid" in ep.path
        ]
        methods = {ep.method for ep in regex_endpoints}
        assert "GET" in methods, f"GET missing, found: {methods}"
        assert "DELETE" in methods, f"DELETE missing, found: {methods}"

    def test_regex_path_param_not_dropped_as_wildcard(self, example_registry):
        introspector = PyramidIntrospector(example_registry)
        spec = introspector.build_client_spec("example")
        paths = {ep.path for ep in spec.endpoints}
        matching = [p for p in paths if "parts" in p and "uuid" in p]
        assert len(matching) >= 1, f"No parts/uuid path found in: {paths}"


class TestResolveBaseMarshmallowType:

    def test_direct_subclass(self):
        class MyField(ma.fields.String):
            pass

        assert _resolve_base_marshmallow_type(MyField) == "String"

    def test_deep_subclass_resolves_to_nearest_standard(self):
        class MiddleField(ma.fields.Integer):
            pass

        class LeafField(MiddleField):
            pass

        assert _resolve_base_marshmallow_type(LeafField) == "Integer"

    def test_standard_field_resolves_to_itself(self):
        assert _resolve_base_marshmallow_type(ma.fields.String) == "String"

    def test_bare_field_subclass_defaults_to_string(self):
        class RawCustom(ma.fields.Field):
            pass

        assert _resolve_base_marshmallow_type(RawCustom) == "String"


class TestDetectCustomFields:

    def test_no_custom_fields_when_standard_only(self):
        class StandardSchema(ma.Schema):
            name = ma.fields.String()
            age = ma.fields.Integer()

        routes = [
            RouteInfo(
                name="things",
                pattern="/things",
                views=[
                    ViewInfo(
                        method="POST",
                        extra={
                            "cornice_args": {"schema": StandardSchema},
                        },
                    ),
                ],
            ),
        ]
        result = _detect_custom_fields(routes)
        assert result == []

    def test_detects_custom_field_from_cornice_schema(self):
        class MoneyField(ma.fields.Integer):
            pass

        class PaymentSchema(ma.Schema):
            amount = MoneyField()
            name = ma.fields.String()

        routes = [
            RouteInfo(
                name="payments",
                pattern="/payments",
                views=[
                    ViewInfo(
                        method="POST",
                        extra={
                            "cornice_args": {"schema": PaymentSchema},
                        },
                    ),
                ],
            ),
        ]
        result = _detect_custom_fields(routes)
        assert len(result) == 1
        assert result[0].class_name == "MoneyField"
        assert result[0].base_type == "Integer"

    def test_detects_custom_field_from_pcm_request(self):
        class TagField(ma.fields.String):
            pass

        class TagSchema(ma.Schema):
            tag = TagField()

        routes = [
            RouteInfo(
                name="tags",
                pattern="/tags",
                views=[
                    ViewInfo(
                        method="POST",
                        extra={
                            "cornice_args": {
                                "pcm_request": {"body": TagSchema},
                            },
                        },
                    ),
                ],
            ),
        ]
        result = _detect_custom_fields(routes)
        assert len(result) == 1
        assert result[0].class_name == "TagField"

    def test_deduplicates_custom_fields(self):
        class SharedField(ma.fields.Float):
            pass

        class SchemaA(ma.Schema):
            val = SharedField()

        class SchemaB(ma.Schema):
            val = SharedField()

        routes = [
            RouteInfo(
                name="a",
                pattern="/a",
                views=[
                    ViewInfo(
                        method="GET",
                        extra={"cornice_args": {"schema": SchemaA}},
                    ),
                ],
            ),
            RouteInfo(
                name="b",
                pattern="/b",
                views=[
                    ViewInfo(
                        method="GET",
                        extra={"cornice_args": {"schema": SchemaB}},
                    ),
                ],
            ),
        ]
        result = _detect_custom_fields(routes)
        assert len(result) == 1

    def test_ignores_views_without_cornice_args(self):
        routes = [
            RouteInfo(
                name="plain",
                pattern="/plain",
                views=[ViewInfo(method="GET")],
            ),
        ]
        result = _detect_custom_fields(routes)
        assert result == []
