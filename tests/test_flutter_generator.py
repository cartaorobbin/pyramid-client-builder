"""Tests for the Flutter/Dart client generator."""

import pytest
from pyramid_introspector import ParameterInfo, SchemaFieldInfo, SchemaInfo

from pyramid_client_builder.generator.flutter_core import FlutterClientGenerator
from pyramid_client_builder.introspection import PyramidIntrospector
from pyramid_client_builder.models import ClientSpec, EndpointInfo


@pytest.fixture()
def simple_spec():
    """A minimal ClientSpec for testing Flutter generation."""
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


class TestFlutterGeneratorWithSimpleSpec:

    def test_creates_output_directory(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        result = gen.generate(tmp_path)
        assert result.exists()

    def test_generates_pubspec(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "pubspec.yaml").exists()

    def test_pubspec_contains_package_name(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        content = (tmp_path / "pubspec.yaml").read_text()
        assert "name: testapp_client" in content
        assert "http:" in content

    def test_generates_readme(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "README.md").exists()

    def test_generates_barrel_export(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "testapp_client.dart").exists()

    def test_generates_client_dart(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "src" / "client.dart").exists()

    def test_generates_v1_directory(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "src" / "v1").is_dir()
        assert (tmp_path / "lib" / "src" / "v1" / "client.dart").exists()

    def test_no_models_file_without_schemas(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "lib" / "src" / "models.dart").exists()
        assert not (tmp_path / "lib" / "src" / "v1" / "models.dart").exists()

    def test_root_client_has_class_declaration(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "class TestappClient" in source

    def test_root_client_has_v1_field(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "late final v1_api.V1Client v1" in source

    def test_root_client_has_constructor(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "TestappClient(" in source
        assert "this.baseUrl" in source

    def test_root_client_has_auth_token(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "String? authToken" in source
        assert "Authorization" in source

    def test_root_client_has_unversioned_methods(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "Future<Map<String, dynamic>> getHome()" in source

    def test_root_client_imports_version_package(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "import 'v1/client.dart' as v1_api;" in source

    def test_v1_client_has_class_declaration(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "class V1Client" in source

    def test_v1_client_has_versioned_methods(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "listItems(" in source
        assert "createItem(" in source
        assert "getItem(" in source

    def test_v1_client_has_constructor(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "this.authTokenProvider)" in source
        assert "V1Client(this.baseUrl, this._httpClient" in source

    def test_custom_flutter_package(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec, flutter_package="my_custom_client")
        gen.generate(tmp_path)
        content = (tmp_path / "pubspec.yaml").read_text()
        assert "name: my_custom_client" in content


# ======================================================================
# Flat spec (no versioned paths -> flat output)
# ======================================================================


class TestFlutterGeneratorWithFlatSpec:

    def test_flat_output_has_no_version_dirs(self, flat_spec, tmp_path):
        gen = FlutterClientGenerator(flat_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "lib" / "src" / "v1").exists()

    def test_flat_output_methods_on_root_client(self, flat_spec, tmp_path):
        gen = FlutterClientGenerator(flat_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "getHome()" in source
        assert "createItems(" in source

    def test_flat_client_has_no_version_imports(self, flat_spec, tmp_path):
        gen = FlutterClientGenerator(flat_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "v1/client.dart" not in source


# ======================================================================
# Example app (real Pyramid + Cornice -> versioned output)
# ======================================================================


class TestFlutterGeneratorWithExampleApp:

    def test_generates_from_real_app(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "src" / "client.dart").exists()
        assert (tmp_path / "lib" / "src" / "v1" / "client.dart").exists()

    def test_pubspec_exists(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "pubspec.yaml").exists()

    def test_verb_naming_in_v1_client(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "cancelCharge(" in source

    def test_list_naming_for_collections(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "listCharges(" in source
        assert "listInvoices(" in source

    def test_root_has_unversioned_endpoints(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "getHome()" in source
        assert "getHealth()" in source

    def test_root_has_v1_field(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "v1_api.V1Client v1" in source


# ======================================================================
# Schema generation (Dart model classes)
# ======================================================================


class TestFlutterSchemaGeneration:

    def test_generates_models_file_with_schemas(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "src" / "v1" / "models.dart").exists()

    def test_models_file_contains_class(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargesRequestSchema" in source

    def test_models_file_has_from_json(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "fromJson(Map<String, dynamic> json)" in source
        assert "json['item_name']" in source
        assert "json['price']" in source

    def test_models_file_has_to_json(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "Map<String, dynamic> toJson()" in source
        assert "'item_name': itemName" in source
        assert "'price': price" in source

    def test_optional_field_has_nullable_type(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "String?" in source

    def test_models_file_has_dart_types(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "int " in source
        assert "String " in source
        assert "bool " in source
        assert "double " in source

    def test_datetime_field_uses_parse(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "DateTime" in source
        assert "DateTime.parse" in source
        assert "toIso8601String()" in source

    def test_no_models_file_without_schemas(self, tmp_path):
        spec = ClientSpec(
            name="simple",
            endpoints=[
                EndpointInfo(name="home", path="/", method="GET"),
            ],
        )
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "lib" / "src" / "models.dart").exists()


# ======================================================================
# Method signatures
# ======================================================================


class TestFlutterMethodSignatures:

    def test_schema_body_uses_model_param(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "ChargesRequestSchema req" in source

    def test_no_schema_body_uses_named_params(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "required String name" in source
        assert "required int price" in source

    def test_path_params_are_positional_string(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "String itemId" in source

    def test_query_schema_uses_model_param(self, tmp_path):
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "ChargesQuerySchema? query" in source

    def test_no_schema_query_uses_nullable_params(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "String? status" in source

    def test_response_schema_returns_model(self, tmp_path):
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
                    name="charge_detail",
                    path="/api/v1/charges/{charge_id}",
                    method="GET",
                    response_schema=response_schema,
                    parameters=[
                        ParameterInfo(name="charge_id", location="path"),
                    ],
                ),
            ],
        )
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "Future<ChargeResponseSchema>" in source

    def test_no_response_schema_returns_map(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "Future<Map<String, dynamic>>" in source


# ======================================================================
# Collection response deserialization (paginated list endpoints)
# ======================================================================


class TestFlutterCollectionResponseDeserialization:
    """Verify list endpoints use List<T> return types and extract 'results'."""

    @pytest.fixture()
    def collection_spec(self):
        schema = SchemaInfo(
            name="PersonSchema",
            fields=[
                SchemaFieldInfo(name="id", field_type="String", required=True),
                SchemaFieldInfo(name="name", field_type="String", required=True),
            ],
        )
        return ClientSpec(
            name="legal_entity",
            endpoints=[
                EndpointInfo(
                    name="persons",
                    path="/api/v1/persons",
                    method="GET",
                    response_schema=schema,
                ),
                EndpointInfo(
                    name="person_detail",
                    path="/api/v1/persons/{person_id}",
                    method="GET",
                    response_schema=schema,
                    parameters=[
                        ParameterInfo(name="person_id", location="path"),
                    ],
                ),
            ],
        )

    def test_list_endpoint_returns_list_type(self, collection_spec, tmp_path):
        gen = FlutterClientGenerator(collection_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "Future<List<PersonsResponseSchema>>" in source

    def test_list_endpoint_extracts_results(self, collection_spec, tmp_path):
        gen = FlutterClientGenerator(collection_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "data['results']" in source
        assert "PersonsResponseSchema.fromJson" in source

    def test_detail_endpoint_returns_single_model(self, collection_spec, tmp_path):
        gen = FlutterClientGenerator(collection_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "Future<PersonsResponseSchema>" in source


# ======================================================================
# HTTP method handling
# ======================================================================


class TestFlutterHttpMethods:

    def test_get_method(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "_httpClient.get(" in source

    def test_post_method_with_body(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "_httpClient.post(" in source
        assert "jsonEncode" in source

    def test_error_handling(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "response.statusCode >= 400" in source
        assert "throw Exception" in source


# ======================================================================
# Import management
# ======================================================================


class TestFlutterImports:

    def test_client_imports_dart_convert(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "import 'dart:convert';" in source

    def test_client_imports_http(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "import 'package:http/http.dart' as http;" in source

    def test_v1_client_imports_dart_convert(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "import 'dart:convert';" in source

    def test_v1_client_imports_http(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "import 'package:http/http.dart' as http;" in source


# ======================================================================
# Schema renaming
# ======================================================================


class TestFlutterSchemaRenaming:

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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargesRequestSchema" in source
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
        gen = FlutterClientGenerator(spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargeRequestSchema" in source


# ======================================================================
# Method name deduplication
# ======================================================================


class TestFlutterMethodNameDeduplication:

    def test_duplicate_names_get_suffix(self):
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
            ],
        )
        gen = FlutterClientGenerator(spec)
        gen._annotate_endpoints(spec.endpoints)
        names = [ep.method_name for ep in spec.endpoints]  # type: ignore[attr-defined]
        assert names[0] == "listThings"
        assert names[1] == "listThings1"


# ======================================================================
# Example app with schemas
# ======================================================================


class TestFlutterExampleAppSchemas:

    def test_v1_models_file_exists(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert (tmp_path / "lib" / "src" / "v1" / "models.dart").exists()

    def test_v1_models_has_request_class(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargeRequestSchema" in source

    def test_v1_models_has_response_class(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargeResponseSchema" in source

    def test_v1_models_has_query_class(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "models.dart").read_text()
        assert "class ChargesQuerySchema" in source

    def test_v1_client_uses_schema_param(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "ChargeRequestSchema req" in source

    def test_v1_client_uses_query_schema_param(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "ChargesQuerySchema? query" in source

    def test_v1_client_returns_response_schema(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "ChargeResponseSchema" in source

    def test_no_root_models_file(self, example_spec, tmp_path):
        gen = FlutterClientGenerator(example_spec)
        gen.generate(tmp_path)
        assert not (tmp_path / "lib" / "src" / "models.dart").exists()


# ======================================================================
# Barrel export
# ======================================================================


class TestFlutterBarrelExport:

    def test_barrel_exports_client(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "testapp_client.dart").read_text()
        assert "export 'src/client.dart';" in source

    def test_barrel_exports_version_client(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "testapp_client.dart").read_text()
        assert "export 'src/v1/client.dart';" in source

    def test_barrel_has_library_declaration(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "testapp_client.dart").read_text()
        assert "library testapp_client;" in source


# ======================================================================
# Callable token provider
# ======================================================================


class TestFlutterCallableTokenProvider:
    """Verify generated Dart client supports authTokenProvider."""

    def test_root_client_has_auth_token_provider_field(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "String Function()? authTokenProvider" in source

    def test_root_client_has_auth_token_provider_param(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "this.authTokenProvider" in source

    def test_root_client_headers_check_provider_first(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "authTokenProvider != null ? authTokenProvider!()" in source

    def test_root_client_still_has_static_auth_token(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "String? authToken" in source

    def test_v1_client_has_auth_token_provider_field(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "String Function()? authTokenProvider" in source

    def test_v1_client_headers_check_provider_first(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "v1" / "client.dart").read_text()
        assert "authTokenProvider != null ? authTokenProvider!()" in source

    def test_root_passes_provider_to_subclient(self, simple_spec, tmp_path):
        gen = FlutterClientGenerator(simple_spec)
        gen.generate(tmp_path)
        source = (tmp_path / "lib" / "src" / "client.dart").read_text()
        assert "authTokenProvider)" in source
