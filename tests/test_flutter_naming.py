"""Tests for Flutter/Dart naming conventions."""

from pyramid_client_builder.generator.flutter_naming import (
    snake_to_camel,
    snake_to_pascal,
    to_dart_class_name,
    to_dart_field_name,
    to_dart_method_name,
    to_dart_package_name,
    to_dart_type,
    to_dart_version_class,
    to_dart_version_field,
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


class TestDartPackageName:

    def test_simple(self):
        assert to_dart_package_name("payments") == "payments_client"

    def test_hyphenated(self):
        assert to_dart_package_name("legal-entity") == "legal_entity_client"

    def test_underscored(self):
        assert to_dart_package_name("my_service") == "my_service_client"

    def test_mixed_separators(self):
        assert to_dart_package_name("my-cool_app") == "my_cool_app_client"

    def test_uppercase_lowered(self):
        assert to_dart_package_name("Payments") == "payments_client"


class TestDartClassName:

    def test_simple(self):
        assert to_dart_class_name("payments") == "PaymentsClient"

    def test_hyphenated(self):
        assert to_dart_class_name("legal-entity") == "LegalEntityClient"

    def test_underscored(self):
        assert to_dart_class_name("my_service") == "MyServiceClient"


class TestDartMethodName:

    def test_list_collection(self):
        assert to_dart_method_name("charges", "GET", "/api/v1/charges") == "listCharges"

    def test_get_detail(self):
        assert (
            to_dart_method_name("charge_detail", "GET", "/api/v1/charges/{id}")
            == "getCharge"
        )

    def test_create(self):
        assert (
            to_dart_method_name("charges", "POST", "/api/v1/charges") == "createCharge"
        )

    def test_delete(self):
        assert (
            to_dart_method_name("charge_detail", "DELETE", "/api/v1/charges/{id}")
            == "deleteCharge"
        )

    def test_verb_path(self):
        assert (
            to_dart_method_name("charge_cancel", "POST", "/api/v1/charges/{id}/cancel")
            == "cancelCharge"
        )

    def test_fallback_root(self):
        assert to_dart_method_name("home", "GET", "/") == "getHome"

    def test_health(self):
        assert to_dart_method_name("health", "GET", "/health") == "getHealth"


class TestDartFieldName:

    def test_simple(self):
        assert to_dart_field_name("amount") == "amount"

    def test_snake_case(self):
        assert to_dart_field_name("part_id") == "partId"

    def test_multi_word(self):
        assert to_dart_field_name("term_months") == "termMonths"

    def test_created_at(self):
        assert to_dart_field_name("created_at") == "createdAt"


class TestDartType:

    def test_string_required(self):
        assert to_dart_type("String", required=True) == "String"

    def test_string_optional(self):
        assert to_dart_type("String", required=False) == "String?"

    def test_integer_required(self):
        assert to_dart_type("Integer", required=True) == "int"

    def test_integer_optional(self):
        assert to_dart_type("Integer", required=False) == "int?"

    def test_float_required(self):
        assert to_dart_type("Float", required=True) == "double"

    def test_float_optional(self):
        assert to_dart_type("Float", required=False) == "double?"

    def test_boolean_required(self):
        assert to_dart_type("Boolean", required=True) == "bool"

    def test_boolean_optional(self):
        assert to_dart_type("Boolean", required=False) == "bool?"

    def test_datetime(self):
        assert to_dart_type("DateTime", required=True) == "DateTime"

    def test_datetime_optional(self):
        assert to_dart_type("DateTime", required=False) == "DateTime?"

    def test_list(self):
        assert to_dart_type("List", required=True) == "List<dynamic>"
        assert to_dart_type("List", required=False) == "List<dynamic>?"

    def test_dict(self):
        assert to_dart_type("Dict", required=True) == "Map<String, dynamic>"
        assert to_dart_type("Dict", required=False) == "Map<String, dynamic>?"

    def test_uuid_is_string(self):
        assert to_dart_type("UUID", required=True) == "String"

    def test_email_is_string(self):
        assert to_dart_type("Email", required=True) == "String"

    def test_unknown_type(self):
        assert to_dart_type("Unknown", required=True) == "dynamic"

    def test_decimal_is_string(self):
        assert to_dart_type("Decimal", required=True) == "String"

    def test_raw_is_dynamic(self):
        assert to_dart_type("Raw", required=True) == "dynamic"


class TestDartVersionField:

    def test_v1(self):
        assert to_dart_version_field("v1") == "v1"

    def test_v2(self):
        assert to_dart_version_field("v2") == "v2"

    def test_v10(self):
        assert to_dart_version_field("v10") == "v10"


class TestDartVersionClass:

    def test_v1(self):
        assert to_dart_version_class("v1") == "V1"

    def test_v2(self):
        assert to_dart_version_class("v2") == "V2"

    def test_v10(self):
        assert to_dart_version_class("v10") == "V10"
