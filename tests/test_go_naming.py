"""Tests for Go naming conventions."""

from pyramid_client_builder.generator.go_naming import (
    go_type_needs_import,
    snake_to_camel,
    snake_to_pascal,
    to_go_field_name,
    to_go_method_name,
    to_go_module_name,
    to_go_package_name,
    to_go_type,
    to_go_version_field,
)


class TestSnakeToPascal:

    def test_simple(self):
        assert snake_to_pascal("list_charges") == "ListCharges"

    def test_single_word(self):
        assert snake_to_pascal("home") == "Home"

    def test_three_words(self):
        assert snake_to_pascal("get_charge_html") == "GetChargeHtml"

    def test_leading_underscore_ignored(self):
        assert snake_to_pascal("_private_name") == "PrivateName"

    def test_empty_string(self):
        assert snake_to_pascal("") == ""


class TestSnakeToCamel:

    def test_simple(self):
        assert snake_to_camel("charge_id") == "chargeId"

    def test_single_word(self):
        assert snake_to_camel("status") == "status"

    def test_multi_word(self):
        assert snake_to_camel("item_name_long") == "itemNameLong"

    def test_empty_string(self):
        assert snake_to_camel("") == ""


class TestGoPackageName:

    def test_simple(self):
        assert to_go_package_name("payments") == "paymentsclient"

    def test_hyphenated(self):
        assert to_go_package_name("legal-entity") == "legalentityclient"

    def test_underscored(self):
        assert to_go_package_name("my_service") == "myserviceclient"

    def test_mixed_separators(self):
        assert to_go_package_name("my-cool_app") == "mycoolappclient"

    def test_uppercase_lowered(self):
        assert to_go_package_name("Payments") == "paymentsclient"


class TestGoModuleName:

    def test_simple(self):
        assert to_go_module_name("payments") == "payments-client"

    def test_underscored(self):
        assert to_go_module_name("legal_entity") == "legal-entity-client"

    def test_hyphenated(self):
        assert to_go_module_name("my-service") == "my-service-client"


class TestGoMethodName:

    def test_list_collection(self):
        assert to_go_method_name("charges", "GET", "/api/v1/charges") == "ListCharges"

    def test_get_detail(self):
        assert (
            to_go_method_name("charge_detail", "GET", "/api/v1/charges/{id}")
            == "GetCharge"
        )

    def test_create(self):
        assert to_go_method_name("charges", "POST", "/api/v1/charges") == "CreateCharge"

    def test_delete(self):
        assert (
            to_go_method_name("charge_detail", "DELETE", "/api/v1/charges/{id}")
            == "DeleteCharge"
        )

    def test_verb_path(self):
        assert (
            to_go_method_name("charge_cancel", "POST", "/api/v1/charges/{id}/cancel")
            == "CancelCharge"
        )

    def test_fallback_root(self):
        assert to_go_method_name("home", "GET", "/") == "GetHome"

    def test_health(self):
        assert to_go_method_name("health", "GET", "/health") == "GetHealth"


class TestGoFieldName:

    def test_simple(self):
        assert to_go_field_name("amount") == "Amount"

    def test_snake_case(self):
        assert to_go_field_name("part_id") == "PartId"

    def test_multi_word(self):
        assert to_go_field_name("term_months") == "TermMonths"


class TestGoType:

    def test_string_required(self):
        assert to_go_type("String", required=True) == "string"

    def test_string_optional(self):
        assert to_go_type("String", required=False) == "*string"

    def test_integer_required(self):
        assert to_go_type("Integer", required=True) == "int"

    def test_integer_optional(self):
        assert to_go_type("Integer", required=False) == "*int"

    def test_float_required(self):
        assert to_go_type("Float", required=True) == "float64"

    def test_boolean_required(self):
        assert to_go_type("Boolean", required=True) == "bool"

    def test_boolean_optional(self):
        assert to_go_type("Boolean", required=False) == "*bool"

    def test_datetime(self):
        assert to_go_type("DateTime", required=True) == "time.Time"

    def test_datetime_optional(self):
        assert to_go_type("DateTime", required=False) == "*time.Time"

    def test_list_always_slice(self):
        assert to_go_type("List", required=True) == "[]interface{}"
        assert to_go_type("List", required=False) == "[]interface{}"

    def test_dict(self):
        assert to_go_type("Dict", required=True) == "map[string]interface{}"
        assert to_go_type("Dict", required=False) == "map[string]interface{}"

    def test_uuid_is_string(self):
        assert to_go_type("UUID", required=True) == "string"

    def test_email_is_string(self):
        assert to_go_type("Email", required=True) == "string"

    def test_unknown_type(self):
        assert to_go_type("Unknown", required=True) == "interface{}"

    def test_decimal_is_string(self):
        assert to_go_type("Decimal", required=True) == "string"

    def test_raw_is_json_raw_message(self):
        assert to_go_type("Raw", required=True) == "json.RawMessage"


class TestGoTypeNeedsImport:

    def test_datetime_needs_time(self):
        assert go_type_needs_import("DateTime") == "time"

    def test_date_needs_time(self):
        assert go_type_needs_import("Date") == "time"

    def test_raw_needs_encoding_json(self):
        assert go_type_needs_import("Raw") == "encoding/json"

    def test_string_no_import(self):
        assert go_type_needs_import("String") is None

    def test_integer_no_import(self):
        assert go_type_needs_import("Integer") is None

    def test_unknown_no_import(self):
        assert go_type_needs_import("Unknown") is None


class TestGoVersionField:

    def test_v1(self):
        assert to_go_version_field("v1") == "V1"

    def test_v2(self):
        assert to_go_version_field("v2") == "V2"

    def test_v10(self):
        assert to_go_version_field("v10") == "V10"
