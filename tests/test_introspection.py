"""Tests for pyramid_client_builder.introspection."""

import pytest

from pyramid_client_builder.introspection.core import PyramidIntrospector
from pyramid_client_builder.introspection.routes import discover_routes
from pyramid_client_builder.introspection.cornice import enrich_endpoints_with_cornice


class TestDiscoverRoutes:

    def test_discovers_plain_routes(self, plain_registry):
        endpoints = discover_routes(plain_registry)
        paths = {(ep.path, ep.method) for ep in endpoints}
        assert ("/", "GET") in paths
        assert ("/health", "GET") in paths

    def test_discovers_methods(self, plain_registry):
        endpoints = discover_routes(plain_registry)
        items_endpoints = [ep for ep in endpoints if ep.path == "/api/v1/items"]
        methods = {ep.method for ep in items_endpoints}
        assert "GET" in methods
        assert "POST" in methods

    def test_extracts_path_parameters(self, plain_registry):
        endpoints = discover_routes(plain_registry)
        detail = [ep for ep in endpoints if ep.path == "/api/v1/items/{item_id}"]
        assert len(detail) >= 1
        path_params = detail[0].path_parameters
        assert len(path_params) == 1
        assert path_params[0].name == "item_id"
        assert path_params[0].location == "path"

    def test_discovers_cornice_routes(self, example_registry):
        endpoints = discover_routes(example_registry)
        paths = {ep.path for ep in endpoints}
        assert "/api/v1/charges" in paths
        assert "/api/v1/charges/{charge_id}" in paths
        assert "/api/v1/charges/{charge_id}/cancel" in paths
        assert "/api/v1/invoices" in paths

    def test_cornice_route_has_path_param(self, example_registry):
        endpoints = discover_routes(example_registry)
        detail = [ep for ep in endpoints if ep.path == "/api/v1/charges/{charge_id}"]
        assert any(
            p.name == "charge_id" and p.location == "path"
            for ep in detail
            for p in ep.parameters
        )


class TestCorniceEnrichment:

    def test_adds_body_parameters(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ]
        assert len(create_charge) == 1
        body_params = create_charge[0].body_parameters
        body_names = {p.name for p in body_params}
        assert "amount" in body_names
        assert "currency" in body_names
        assert "part_id" in body_names

    def test_body_param_types(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ][0]
        amount = next(p for p in create_charge.body_parameters if p.name == "amount")
        assert amount.type_hint == "int"
        currency = next(p for p in create_charge.body_parameters if p.name == "currency")
        assert currency.type_hint == "str"

    def test_adds_querystring_parameters(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        list_charges = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "GET"
        ]
        assert len(list_charges) >= 1
        qs_params = list_charges[0].querystring_parameters
        qs_names = {p.name for p in qs_params}
        assert "status" in qs_names
        assert "page" in qs_names
        assert "per_page" in qs_names

    def test_querystring_params_not_required(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        list_charges = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "GET"
        ][0]
        for p in list_charges.querystring_parameters:
            if p.name in ("status", "page", "per_page"):
                assert p.required is False

    def test_no_enrichment_for_plain_routes(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        home = [ep for ep in endpoints if ep.path == "/" and ep.method == "GET"]
        assert len(home) == 1
        assert home[0].body_parameters == []
        assert home[0].querystring_parameters == []

    def test_captures_request_schema(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ][0]
        assert create_charge.request_schema is not None
        assert create_charge.request_schema.name == "ChargeRequestSchema"
        field_names = {f.name for f in create_charge.request_schema.fields}
        assert "amount" in field_names
        assert "currency" in field_names
        assert "part_id" in field_names

    def test_request_schema_field_types(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ][0]
        fields_by_name = {
            f.name: f for f in create_charge.request_schema.fields
        }
        assert fields_by_name["amount"].field_type == "Integer"
        assert fields_by_name["amount"].required is True
        assert fields_by_name["currency"].field_type == "String"
        assert fields_by_name["description"].required is False

    def test_captures_querystring_schema(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        list_charges = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "GET"
        ][0]
        assert list_charges.querystring_schema is not None
        assert list_charges.querystring_schema.name == "ChargesQuerySchema"
        field_names = {f.name for f in list_charges.querystring_schema.fields}
        assert "status" in field_names
        assert "page" in field_names

    def test_captures_response_schema(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ][0]
        assert create_charge.response_schema is not None
        assert create_charge.response_schema.name == "ChargeResponseSchema"
        field_names = {f.name for f in create_charge.response_schema.fields}
        assert "id" in field_names
        assert "status" in field_names

    def test_no_response_schema_when_not_declared(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        list_charges = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "GET"
        ][0]
        assert list_charges.response_schema is None

    def test_no_schema_for_plain_routes(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        home = [ep for ep in endpoints if ep.path == "/" and ep.method == "GET"][0]
        assert home.request_schema is None
        assert home.querystring_schema is None
        assert home.response_schema is None


class TestCompositeSchemaEnrichment:
    """Tests for Cornice composite (location-aware) schemas."""

    def _get_refund_endpoint(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        matches = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges/{charge_id}/refund" and ep.method == "POST"
        ]
        assert len(matches) == 1
        return matches[0]

    def test_extracts_body_params_from_nested(self, example_registry):
        ep = self._get_refund_endpoint(example_registry)
        body_names = {p.name for p in ep.body_parameters}
        assert "amount" in body_names
        assert "reason" in body_names

    def test_body_param_types_from_nested(self, example_registry):
        ep = self._get_refund_endpoint(example_registry)
        amount = next(p for p in ep.body_parameters if p.name == "amount")
        assert amount.type_hint == "int"
        assert amount.required is True
        reason = next(p for p in ep.body_parameters if p.name == "reason")
        assert reason.type_hint == "str"
        assert reason.required is False

    def test_extracts_querystring_params_from_nested(self, example_registry):
        ep = self._get_refund_endpoint(example_registry)
        qs_names = {p.name for p in ep.querystring_parameters}
        assert "notify" in qs_names

    def test_no_location_fields_leaked_as_params(self, example_registry):
        """The wrapper field names (body, querystring) must not appear as params."""
        ep = self._get_refund_endpoint(example_registry)
        all_names = {p.name for p in ep.parameters}
        assert "body" not in all_names
        assert "querystring" not in all_names

    def test_request_schema_is_inner(self, example_registry):
        ep = self._get_refund_endpoint(example_registry)
        assert ep.request_schema is not None
        assert ep.request_schema.name == "RefundBodySchema"
        field_names = {f.name for f in ep.request_schema.fields}
        assert "amount" in field_names
        assert "reason" in field_names

    def test_querystring_schema_is_inner(self, example_registry):
        ep = self._get_refund_endpoint(example_registry)
        assert ep.querystring_schema is not None
        assert ep.querystring_schema.name == "RefundQuerySchema"
        field_names = {f.name for f in ep.querystring_schema.fields}
        assert "notify" in field_names


class TestPycornmarshEnrichment:
    """Tests for pycornmarsh-style metadata (pcm_request / pcm_responses)."""

    def _get_simulate_endpoint(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        matches = [
            ep for ep in endpoints
            if ep.path == "/api/v1/financing/simulate" and ep.method == "POST"
        ]
        assert len(matches) == 1
        return matches[0]

    def test_pcm_request_body_params(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        body_names = {p.name for p in ep.body_parameters}
        assert "amount" in body_names
        assert "term_months" in body_names
        assert "rate" in body_names

    def test_pcm_request_body_param_types(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        amount = next(p for p in ep.body_parameters if p.name == "amount")
        assert amount.type_hint == "int"
        assert amount.required is True
        rate = next(p for p in ep.body_parameters if p.name == "rate")
        assert rate.type_hint == "float"
        assert rate.required is False

    def test_pcm_request_body_schema(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        assert ep.request_schema is not None
        assert ep.request_schema.name == "SimulateBodySchema"
        field_names = {f.name for f in ep.request_schema.fields}
        assert "amount" in field_names
        assert "term_months" in field_names

    def test_pcm_request_querystring_schema(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        assert ep.querystring_schema is not None
        assert ep.querystring_schema.name == "SimulateQuerySchema"
        field_names = {f.name for f in ep.querystring_schema.fields}
        assert "currency" in field_names

    def test_pcm_request_querystring_params(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        qs_names = {p.name for p in ep.querystring_parameters}
        assert "currency" in qs_names

    def test_pcm_responses_success_schema(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        assert ep.response_schema is not None
        assert ep.response_schema.name == "SimulateResponseSchema"
        field_names = {f.name for f in ep.response_schema.fields}
        assert "monthly_payment" in field_names
        assert "total_interest" in field_names

    def test_pcm_overrides_schema_kwarg(self, example_registry):
        """pcm_request takes precedence over the schema kwarg."""
        ep = self._get_simulate_endpoint(example_registry)
        assert ep.request_schema.name == "SimulateBodySchema"
        assert ep.request_schema.name != "SimulateRequestSchema"

    def test_pcm_response_schemas_dict_populated(self, example_registry):
        ep = self._get_simulate_endpoint(example_registry)
        assert 200 in ep.response_schemas
        assert 400 in ep.response_schemas
        assert ep.response_schemas[200].name == "SimulateResponseSchema"
        assert ep.response_schemas[400].name == "RequestErrorSchema"

    def test_pcm_response_schema_is_success(self, example_registry):
        """response_schema returns the 2xx schema for backward compat."""
        ep = self._get_simulate_endpoint(example_registry)
        assert ep.response_schema is not None
        assert ep.response_schema.name == "SimulateResponseSchema"

    def test_pcm_response_schemas_empty_for_non_pcm(self, example_registry):
        endpoints = discover_routes(example_registry)
        endpoints = enrich_endpoints_with_cornice(example_registry, endpoints)
        create_charge = [
            ep for ep in endpoints
            if ep.path == "/api/v1/charges" and ep.method == "POST"
        ][0]
        assert create_charge.response_schemas == {}


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
