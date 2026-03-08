"""Tests for pyramid_client_builder.introspection."""

from pyramid_introspector import ParameterInfo, RouteInfo, SchemaInfo, ViewInfo

from pyramid_client_builder.introspection import (
    PyramidIntrospector,
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
