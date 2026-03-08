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
