"""Tests for pyramid_client_builder.generator.naming."""

import pytest

from pyramid_client_builder.generator.naming import (
    extract_version,
    needs_schema_rename,
    to_class_name,
    to_method_name,
    to_package_name,
    to_request_attr,
    to_schema_name,
)


class TestToClassName:

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("payments", "PaymentsClient"),
            ("legal_entity", "LegalEntityClient"),
            ("my-service", "MyServiceClient"),
            ("charge", "ChargeClient"),
        ],
    )
    def test_conversions(self, name, expected):
        assert to_class_name(name) == expected


class TestToPackageName:

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("payments", "payments_client"),
            ("legal-entity", "legal_entity_client"),
        ],
    )
    def test_conversions(self, name, expected):
        assert to_package_name(name) == expected


class TestToRequestAttr:

    @pytest.mark.parametrize(
        "name, expected",
        [
            ("payments", "payments_client"),
            ("legal-entity", "legal_entity_client"),
        ],
    )
    def test_conversions(self, name, expected):
        assert to_request_attr(name) == expected


class TestToSchemaName:
    """Derive schema names from endpoint paths + role."""

    @pytest.mark.parametrize(
        "path, role, expected",
        [
            ("/api/v1/charges", "request", "ChargesRequestSchema"),
            ("/api/v1/charges", "response", "ChargesResponseSchema"),
            ("/api/v1/charges", "querystring", "ChargesQuerySchema"),
            ("/api/v1/charges/{charge_id}", "response", "ChargesResponseSchema"),
            (
                "/api/v1/charges/{charge_id}/refund",
                "request",
                "ChargesRefundRequestSchema",
            ),
            (
                "/api/v1/financing/simulate",
                "response",
                "FinancingSimulateResponseSchema",
            ),
            (
                "/api/v1/split_accounts",
                "querystring",
                "SplitAccountsQuerySchema",
            ),
        ],
    )
    def test_schema_name_from_path(self, path, role, expected):
        assert to_schema_name(path, role) == expected

    def test_returns_none_for_root_path(self):
        assert to_schema_name("/", "request") is None

    def test_returns_none_for_unknown_role(self):
        assert to_schema_name("/api/v1/charges", "unknown") is None


class TestNeedsSchemaRename:

    @pytest.mark.parametrize(
        "name",
        [
            "ChargeSchema",
            "Charge",
            "ChargeModel",
            "ChargeData",
        ],
    )
    def test_needs_rename(self, name):
        assert needs_schema_rename(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "ChargeRequestSchema",
            "ChargesResponseSchema",
            "ChargesQuerySchema",
            "RefundBodySchema",
            "ChargePathSchema",
            "RequestErrorSchema",
        ],
    )
    def test_already_has_role_suffix(self, name):
        assert needs_schema_rename(name) is False


class TestExtractVersion:

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("/api/v1/charges", "v1"),
            ("/api/v2/invoices/{id}", "v2"),
            ("/v3/items", "v3"),
            ("/api/v10/resources", "v10"),
        ],
    )
    def test_extracts_version(self, path, expected):
        assert extract_version(path) == expected

    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/",
            "/items",
            "/api/charges",
        ],
    )
    def test_returns_none_without_version(self, path):
        assert extract_version(path) is None


class TestToMethodNameVerbDetection:
    """Paths ending with a verb should use it as the prefix."""

    @pytest.mark.parametrize(
        "route_name, method, path, expected",
        [
            (
                "charge_cancel",
                "POST",
                "/api/v1/charges/{charge_id}/cancel",
                "cancel_charge",
            ),
            (
                "charge_refund",
                "POST",
                "/api/v1/charges/{charge_id}/refund",
                "refund_charge",
            ),
            (
                "charge_capture",
                "POST",
                "/api/v1/charges/{charge_id}/capture",
                "capture_charge",
            ),
            (
                "invoice_void",
                "POST",
                "/api/v1/invoices/{invoice_id}/void",
                "void_invoice",
            ),
        ],
    )
    def test_verb_paths(self, route_name, method, path, expected):
        assert to_method_name(route_name, method, path) == expected


class TestToMethodNameCollections:
    """GET on collection paths should use list_ prefix."""

    @pytest.mark.parametrize(
        "route_name, method, path, expected",
        [
            ("charges", "GET", "/api/v1/charges", "list_charges"),
            ("invoices", "GET", "/api/v1/invoices", "list_invoices"),
        ],
    )
    def test_list_collections(self, route_name, method, path, expected):
        assert to_method_name(route_name, method, path) == expected


class TestToMethodNameDetail:
    """Detail paths (ending with {id}) should singularize the resource."""

    @pytest.mark.parametrize(
        "route_name, method, path, expected",
        [
            ("charge_detail", "GET", "/api/v1/charges/{charge_id}", "get_charge"),
            ("charge_detail", "DELETE", "/api/v1/charges/{charge_id}", "delete_charge"),
            ("charge_detail", "PUT", "/api/v1/charges/{charge_id}", "update_charge"),
            ("charge_detail", "PATCH", "/api/v1/charges/{charge_id}", "patch_charge"),
        ],
    )
    def test_detail_endpoints(self, route_name, method, path, expected):
        assert to_method_name(route_name, method, path) == expected


class TestToMethodNameCreate:
    """POST on collection paths should use create_ prefix and singularize."""

    def test_create_charge(self):
        assert to_method_name("charges", "POST", "/api/v1/charges") == "create_charge"

    def test_create_invoice(self):
        assert (
            to_method_name("invoices", "POST", "/api/v1/invoices") == "create_invoice"
        )


class TestToMethodNameRouteNameFallback:
    """Short or root paths should fall back to route name."""

    @pytest.mark.parametrize(
        "route_name, method, path, expected",
        [
            ("home", "GET", "/", "get_home"),
            ("health", "GET", "/health", "get_health"),
        ],
    )
    def test_fallback(self, route_name, method, path, expected):
        assert to_method_name(route_name, method, path) == expected

    def test_no_path(self):
        assert to_method_name("status", "GET") == "get_status"


class TestToMethodNameSingularization:
    """Verify singularization handles common patterns."""

    @pytest.mark.parametrize(
        "route_name, method, path, expected_suffix",
        [
            ("categories", "GET", "/api/v1/categories/{id}", "get_category"),
            ("addresses", "GET", "/api/v1/addresses/{id}", "get_address"),
            ("taxes", "GET", "/api/v1/taxes/{id}", "get_tax"),
        ],
    )
    def test_singularization_in_detail(self, route_name, method, path, expected_suffix):
        result = to_method_name(route_name, method, path)
        assert result == expected_suffix
