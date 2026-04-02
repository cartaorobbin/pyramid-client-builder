"""Tests for pyramid_client_builder.generator."""

import ast

import pytest
from pyramid_introspector import ParameterInfo, SchemaFieldInfo, SchemaInfo

from pyramid_client_builder.generator.core import ClientGenerator
from pyramid_client_builder.introspection import PyramidIntrospector
from pyramid_client_builder.models import ClientSpec, EndpointInfo


@pytest.fixture()
def simple_spec():
    """A minimal ClientSpec for testing generation."""
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
# Simple spec (has versioned /api/v1/ endpoints → versioned output)
# ======================================================================


class TestClientGeneratorWithSimpleSpec:

    def test_creates_package_directory(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert package_dir.exists()
        assert package_dir.name == "testapp_client"

    def test_generates_base_files(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "__init__.py").exists()
        assert (package_dir / "client.py").exists()
        assert (package_dir / "ext.py").exists()

    def test_generates_v1_directory(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "v1").is_dir()
        assert (package_dir / "v1" / "__init__.py").exists()
        assert (package_dir / "v1" / "client.py").exists()

    def test_no_schemas_file_without_schemas(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert not (package_dir / "schemas.py").exists()
        assert not (package_dir / "v1" / "schemas.py").exists()

    def test_generated_files_are_valid_python(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_root_client_has_version_property(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "self.v1 = V1Client(" in client_source

    def test_root_client_has_unversioned_methods(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "def get_home(self):" in client_source

    def test_v1_client_has_versioned_methods(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def list_items(" in v1_source
        assert "def create_item(" in v1_source
        assert "def get_item(" in v1_source

    def test_class_name_and_package_name(self, simple_spec):
        gen = ClientGenerator(simple_spec)
        assert gen.class_name == "TestappClient"
        assert gen.package_name == "testapp_client"
        assert gen.request_attr == "testapp_client"


# ======================================================================
# Flat spec (no versioned paths → flat output, backward compatible)
# ======================================================================


class TestClientGeneratorWithFlatSpec:

    def test_flat_output_has_no_version_dirs(self, flat_spec, tmp_path):
        gen = ClientGenerator(flat_spec)
        package_dir = gen.generate(tmp_path)
        assert not (package_dir / "v1").exists()

    def test_flat_output_methods_on_root_client(self, flat_spec, tmp_path):
        gen = ClientGenerator(flat_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "def get_home(self):" in client_source
        assert "def create_items(" in client_source

    def test_flat_output_is_valid_python(self, flat_spec, tmp_path):
        gen = ClientGenerator(flat_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.glob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Example app (real Pyramid + Cornice → versioned output)
# ======================================================================


class TestClientGeneratorWithExampleApp:

    def test_generates_from_real_app(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "client.py").exists()
        assert (package_dir / "v1" / "client.py").exists()

    def test_all_generated_files_are_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_verb_naming_in_v1_client(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def cancel_charge(" in v1_source

    def test_list_naming_for_collections(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def list_charges(" in v1_source
        assert "def list_invoices(" in v1_source

    def test_root_has_unversioned_endpoints(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "def get_home(self):" in root_source
        assert "def get_health(self):" in root_source

    def test_root_has_v1_property(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "self.v1 = V1Client(" in root_source

    def test_ext_contains_includeme(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        ext_source = (package_dir / "ext.py").read_text()
        assert "def includeme(config):" in ext_source
        assert "example_client" in ext_source

    def test_init_exports_class(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        init_source = (package_dir / "__init__.py").read_text()
        assert "ExampleClient" in init_source

    def test_init_exports_v1_module(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        init_source = (package_dir / "__init__.py").read_text()
        assert '"v1"' in init_source

    def test_generates_v1_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "v1" / "schemas.py").exists()

    def test_v1_schemas_file_is_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        ast.parse(source, filename="schemas.py")

    def test_v1_schemas_contains_request_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargeRequestSchema(ma.Schema):" in source
        assert "ma.fields.Integer" in source
        assert "ma.fields.String" in source

    def test_v1_schemas_contains_querystring_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargesQuerySchema(ma.Schema):" in source

    def test_v1_schemas_contains_response_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargeResponseSchema(ma.Schema):" in source

    def test_v1_client_imports_schemas(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "from example_client.v1.schemas import" in v1_source
        assert "ChargeRequestSchema" in v1_source

    def test_v1_client_uses_dump_for_body(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "ChargeRequestSchema().dump(" in v1_source

    def test_v1_client_uses_dump_for_querystring(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "ChargesQuerySchema().dump(" in v1_source

    def test_v1_client_uses_load_for_response(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "ChargeResponseSchema().load(response.json())" in v1_source

    def test_client_falls_back_to_raw_json_without_response_schema(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "return response.json()" in v1_source

    def test_body_params_generate_json_body(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "json=body" in v1_source

    def test_no_root_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        assert not (package_dir / "schemas.py").exists()

    def test_empty_schema_generates_pass(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class DocumentConciliateRequestSchema(ma.Schema):" in source
        assert "    pass" in source

    def test_composite_schema_generates_inner_schemas(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class RefundBodySchema(ma.Schema):" in source
        assert "class RefundQuerySchema(ma.Schema):" in source
        assert "RefundRequestSchema" not in source

    def test_composite_schema_refund_has_individual_params(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        for line in v1_source.splitlines():
            if "def refund_charge(" in line:
                assert "amount: int" in line
                assert "reason: str" in line
                assert "notify: bool" in line
                assert "body" not in line
                assert "querystring" not in line
                break
        else:
            raise AssertionError("refund_charge not found")

    def test_composite_schema_refund_uses_inner_schema_dump(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "RefundBodySchema().dump(" in v1_source
        assert "RefundQuerySchema().dump(" in v1_source


class TestPycornmarshGeneration:
    """Verify pycornmarsh-style endpoints generate correct client code."""

    def test_pcm_schemas_in_v1_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class SimulateBodySchema(ma.Schema):" in source
        assert "class SimulateQuerySchema(ma.Schema):" in source
        assert "class SimulateResponseSchema(ma.Schema):" in source

    def test_pcm_client_uses_body_schema_dump(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "SimulateBodySchema().dump(" in v1_source

    def test_pcm_client_uses_querystring_schema_dump(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "SimulateQuerySchema().dump(" in v1_source

    def test_pcm_client_uses_response_schema_load(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "SimulateResponseSchema().load(response.json())" in v1_source

    def test_pcm_endpoint_has_individual_params(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        for line in v1_source.splitlines():
            if "def simulate_financing(" in line:
                assert "amount: int" in line
                assert "term_months: int" in line
                break
        else:
            raise AssertionError("simulate_financing not found")

    def test_pcm_error_schema_in_v1_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class RequestErrorSchema(ma.Schema):" in source

    def test_pcm_generated_code_is_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Collection response deserialization (paginated list endpoints)
# ======================================================================


class TestCollectionResponseDeserialization:
    """Verify list endpoints use many=True and extract 'results' from response."""

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

    def test_list_endpoint_uses_many_true(self, collection_spec, tmp_path):
        gen = ClientGenerator(collection_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert (
            'PersonsResponseSchema(many=True).load(response.json()["results"])'
            in v1_source
        )

    def test_detail_endpoint_uses_single_load(self, collection_spec, tmp_path):
        gen = ClientGenerator(collection_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "PersonsResponseSchema().load(response.json())" in v1_source

    def test_collection_generated_code_is_valid_python(self, collection_spec, tmp_path):
        gen = ClientGenerator(collection_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_httpx_list_endpoint_uses_many_true(self, collection_spec, tmp_path):
        gen = ClientGenerator(collection_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert (
            'PersonsResponseSchema(many=True).load(response.json()["results"])'
            in v1_source
        )

    def test_list_without_response_schema_returns_raw_json(self, tmp_path):
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="GET",
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "return response.json()" in v1_source


# ======================================================================
# Method signatures
# ======================================================================


class TestMethodSignatures:
    """Verify generated methods use individual parameters, not body: dict."""

    def test_body_params_are_individual_arguments(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "body: dict" not in v1_source

    def test_create_charge_has_individual_params(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def create_charge(self, amount: int" in v1_source
        assert "currency: str" in v1_source
        assert "part_id: str" in v1_source
        assert "description: str | None = None" in v1_source

    def test_required_params_before_optional(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        for line in v1_source.splitlines():
            if "def create_charge(" in line:
                amount_pos = line.index("amount: int")
                description_pos = line.index("description: str | None")
                assert amount_pos < description_pos
                break
        else:
            raise AssertionError("create_charge not found")

    def test_dump_references_individual_params(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert '"amount": amount' in v1_source
        assert '"currency": currency' in v1_source

    def test_simple_spec_body_uses_individual_params(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "body: dict" not in v1_source
        assert "def create_item(self, name: str, price: int)" in v1_source

    def test_simple_spec_body_built_from_params(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert '"name": name' in v1_source
        assert '"price": price' in v1_source


# ======================================================================
# Method name deduplication
# ======================================================================


class TestMethodNameDeduplication:

    def test_duplicate_names_get_suffix(self):
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
                EndpointInfo(name="things", path="/api/v1/things", method="GET"),
            ],
        )
        gen = ClientGenerator(spec)
        gen._annotate_endpoints(spec.endpoints)
        names = [ep.method_name for ep in spec.endpoints]  # type: ignore[attr-defined]
        assert names[0] == "list_things"
        assert names[1] == "list_things_1"


# ======================================================================
# Schema renaming
# ======================================================================


class TestSchemaRenaming:
    """Verify schemas without role suffixes get renamed from endpoint paths."""

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
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargesRequestSchema(ma.Schema):" in v1_schemas
        assert "ChargeSchema" not in v1_schemas

    def test_generic_schema_renamed_for_response(self, tmp_path):
        schema = SchemaInfo(
            name="ChargeSchema",
            fields=[
                SchemaFieldInfo(name="id", field_type="String"),
            ],
        )
        spec = ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="GET",
                    response_schema=schema,
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargesResponseSchema(ma.Schema):" in v1_schemas

    def test_generic_schema_renamed_for_querystring(self, tmp_path):
        schema = SchemaInfo(
            name="ChargesFilter",
            fields=[
                SchemaFieldInfo(name="status", field_type="String"),
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
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargesQuerySchema(ma.Schema):" in v1_schemas
        assert "ChargesFilter" not in v1_schemas

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
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "class ChargeRequestSchema(ma.Schema):" in v1_schemas

    def test_v1_client_uses_renamed_schema(self, tmp_path):
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
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_client = (package_dir / "v1" / "client.py").read_text()
        assert "ChargesRequestSchema().dump(" in v1_client
        assert "ChargeSchema" not in v1_client

    def test_rename_conflict_keeps_original(self, tmp_path):
        """When the same schema would get different names, keep the original."""
        schema = SchemaInfo(
            name="GenericSchema",
            fields=[SchemaFieldInfo(name="data", field_type="String")],
        )
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(
                    name="charges",
                    path="/api/v1/charges",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="data", location="body", type_hint="str"),
                    ],
                ),
                EndpointInfo(
                    name="invoices",
                    path="/api/v1/invoices",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="data", location="body", type_hint="str"),
                    ],
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "class GenericSchema(ma.Schema):" in v1_schemas


# ======================================================================
# Empty schemas (no fields → must emit ``pass``)
# ======================================================================


class TestEmptySchemaGeneratesPass:
    """A schema with no fields must produce ``pass`` so the class body is valid."""

    def test_empty_schema_contains_pass(self, tmp_path):
        schema = SchemaInfo(name="EmptyRequestSchema")
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(
                    name="things",
                    path="/api/v1/things",
                    method="POST",
                    request_schema=schema,
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class EmptyRequestSchema(ma.Schema):" in source
        assert "    pass" in source

    def test_empty_schema_is_valid_python(self, tmp_path):
        schema = SchemaInfo(name="EmptyRequestSchema")
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(
                    name="things",
                    path="/api/v1/things",
                    method="POST",
                    request_schema=schema,
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_mixed_empty_and_populated_schemas(self, tmp_path):
        empty_schema = SchemaInfo(name="EmptyRequestSchema")
        populated_schema = SchemaInfo(
            name="ThingsResponseSchema",
            fields=[SchemaFieldInfo(name="id", field_type="String")],
        )
        spec = ClientSpec(
            name="test",
            endpoints=[
                EndpointInfo(
                    name="things",
                    path="/api/v1/things",
                    method="POST",
                    request_schema=empty_schema,
                    response_schema=populated_schema,
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "class EmptyRequestSchema(ma.Schema):" in source
        assert "    pass" in source
        assert "class ThingsResponseSchema(ma.Schema):" in source
        assert "id = ma.fields.String()" in source
        ast.parse(source, filename="schemas.py")


# ======================================================================
# Version directory structure
# ======================================================================


class TestVersionedStructure:

    def test_v1_init_exports_client(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_init = (package_dir / "v1" / "__init__.py").read_text()
        assert "V1Client" in v1_init

    def test_v1_client_class_name(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "class V1Client:" in v1_source

    def test_v1_client_constructor_takes_session_and_auth(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert (
            "def __init__(self, base_url, session, timeout, auth_token=None):"
            in v1_source
        )

    def test_root_client_creates_session(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "self.session = requests.Session()" in root_source
        assert "auth_token" in root_source


# ======================================================================
# Project packaging (pyproject.toml + README.md)
# ======================================================================


class TestProjectPackaging:
    """Verify the generated output is an installable Python package."""

    def test_generates_pyproject_toml(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir.parent / "pyproject.toml").exists()

    def test_generates_readme(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir.parent / "README.md").exists()

    def test_pyproject_contains_project_name(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'name = "testapp-client-requests"' in content

    def test_pyproject_contains_default_version(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'version = "0.1.0"' in content

    def test_pyproject_custom_version(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, version="2.3.1")
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'version = "2.3.1"' in content

    def test_pyproject_depends_on_requests(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "requests>=" in content

    def test_pyproject_no_marshmallow_without_schemas(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "marshmallow" not in content

    def test_pyproject_includes_marshmallow_with_schemas(self, tmp_path):
        schema = SchemaInfo(
            name="ItemSchema",
            fields=[SchemaFieldInfo(name="name", field_type="String")],
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
                        ParameterInfo(name="name", location="body", type_hint="str"),
                    ],
                ),
            ],
        )
        gen = ClientGenerator(spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "marshmallow>=" in content

    def test_pyproject_has_pyramid_optional_dep(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "[project.optional-dependencies]" in content
        assert "pyramid" in content

    def test_pyproject_has_hatchling_build_backend(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'build-backend = "hatchling.build"' in content

    def test_pyproject_has_correct_package_ref(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'packages = ["testapp_client"]' in content

    def test_readme_contains_package_name(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "README.md").read_text()
        assert "testapp-client" in content
        assert "TestappClient" in content

    def test_readme_contains_pyramid_ext_usage(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "README.md").read_text()
        assert "testapp_client.ext" in content
        assert "request.testapp_client" in content


# ======================================================================
# HTTP client backend (requests vs httpx)
# ======================================================================


class TestHttpClientOption:
    """Verify the --http-client option generates correct backend code."""

    def test_default_backend_is_requests(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        assert gen.http_client == "requests"

    def test_requests_root_client_imports_requests(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="requests")
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "import requests" in source
        assert "import httpx" not in source

    def test_requests_root_client_creates_session(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="requests")
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "self.session = requests.Session()" in source
        assert "httpx.Client()" not in source

    def test_httpx_root_client_imports_httpx(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "import httpx" in source
        assert "import requests" not in source

    def test_httpx_root_client_creates_client(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "self.session = httpx.Client()" in source
        assert "requests.Session()" not in source

    def test_httpx_v1_client_imports_httpx(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "import httpx" in v1_source
        assert "import requests" not in v1_source

    def test_requests_v1_client_imports_requests(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="requests")
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "import requests" in v1_source
        assert "import httpx" not in v1_source

    def test_httpx_pyproject_depends_on_httpx(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "httpx>=" in content
        assert "requests" not in content

    def test_requests_pyproject_depends_on_requests(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="requests")
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert "requests>=" in content
        assert "httpx" not in content

    def test_httpx_pyproject_has_httpx_project_name(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'name = "testapp-client-httpx"' in content

    def test_requests_pyproject_has_requests_project_name(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="requests")
        package_dir = gen.generate(tmp_path)
        content = (package_dir.parent / "pyproject.toml").read_text()
        assert 'name = "testapp-client-requests"' in content

    def test_httpx_generated_files_are_valid_python(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_httpx_example_app_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_httpx_flat_output_valid_python(self, flat_spec, tmp_path):
        gen = ClientGenerator(flat_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_httpx_preserves_endpoint_methods(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "def get_home(self):" in root_source
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def list_items(" in v1_source
        assert "def create_item(" in v1_source

    def test_httpx_preserves_session_method_calls(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "self.session.get(" in root_source
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "self.session.get(" in v1_source
        assert "self.session.post(" in v1_source


# ======================================================================
# Static / wildcard views (should be excluded from generated client)
# ======================================================================


class TestStaticViewsExcluded:
    """Verify that Pyramid static views with wildcard paths don't break generation."""

    @pytest.fixture()
    def spec_with_static_view(self):
        return ClientSpec(
            name="myapp",
            endpoints=[
                EndpointInfo(name="home", path="/", method="GET", description="Home"),
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="GET",
                    description="List items",
                ),
                EndpointInfo(
                    name="__static/",
                    path="static/*subpath",
                    method="GET",
                    description="An instance of this class is a callable ...",
                ),
            ],
        )

    def test_static_view_method_not_in_client(self, spec_with_static_view, tmp_path):
        gen = ClientGenerator(spec_with_static_view)
        package_dir = gen.generate(tmp_path)
        all_source = ""
        for py_file in package_dir.rglob("*.py"):
            all_source += py_file.read_text()
        assert "subpath" not in all_source
        assert "static" not in all_source.replace("__static", "")

    def test_normal_endpoints_still_generated(self, spec_with_static_view, tmp_path):
        gen = ClientGenerator(spec_with_static_view)
        package_dir = gen.generate(tmp_path)
        root_source = (package_dir / "client.py").read_text()
        assert "def get_home(self):" in root_source

    def test_generated_files_are_valid_python(self, spec_with_static_view, tmp_path):
        gen = ClientGenerator(spec_with_static_view)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Callable token provider
# ======================================================================


class TestCallableTokenProvider:
    """Verify generated Python client supports callable auth_token."""

    def test_root_client_has_apply_auth(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "def _apply_auth(self):" in source

    def test_root_client_checks_callable(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "callable(self._auth_token)" in source

    def test_root_client_stores_auth_token(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "self._auth_token = auth_token" in source

    def test_root_client_does_not_set_header_eagerly(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "if auth_token:" not in source

    def test_root_methods_call_apply_auth(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "self._apply_auth()" in source

    def test_v1_client_has_apply_auth(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "def _apply_auth(self):" in v1_source

    def test_v1_client_checks_callable(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "callable(self._auth_token)" in v1_source

    def test_v1_methods_call_apply_auth(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        v1_source = (package_dir / "v1" / "client.py").read_text()
        assert "self._apply_auth()" in v1_source

    def test_root_passes_auth_token_to_subclient(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "self._auth_token)" in source

    def test_httpx_root_client_has_apply_auth(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec, http_client="httpx")
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "client.py").read_text()
        assert "def _apply_auth(self):" in source
        assert "callable(self._auth_token)" in source


# ======================================================================
# Custom Marshmallow fields
# ======================================================================


class TestCustomFieldGeneration:
    """Verify that custom Marshmallow fields are shipped with the client."""

    @pytest.fixture()
    def spec_with_custom_field(self):
        from pyramid_client_builder.models import CustomFieldInfo

        schema = SchemaInfo(
            name="PaymentRequestSchema",
            fields=[
                SchemaFieldInfo(name="amount", field_type="Integer", required=True),
                SchemaFieldInfo(
                    name="currency", field_type="CurrencyField", required=True
                ),
            ],
        )
        return ClientSpec(
            name="billing",
            endpoints=[
                EndpointInfo(
                    name="payments",
                    path="/api/v1/payments",
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
            custom_fields=[
                CustomFieldInfo(class_name="CurrencyField", base_type="String"),
            ],
        )

    @pytest.fixture()
    def spec_without_custom_field(self):
        schema = SchemaInfo(
            name="ItemRequestSchema",
            fields=[
                SchemaFieldInfo(name="name", field_type="String", required=True),
            ],
        )
        return ClientSpec(
            name="inventory",
            endpoints=[
                EndpointInfo(
                    name="items",
                    path="/api/v1/items",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(name="name", location="body", type_hint="str"),
                    ],
                ),
            ],
        )

    def test_generates_fields_module(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "fields.py").exists()

    def test_fields_module_has_custom_class(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "fields.py").read_text()
        assert "class CurrencyField(ma.fields.String):" in source

    def test_fields_module_imports_marshmallow(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "fields.py").read_text()
        assert "import marshmallow as ma" in source

    def test_fields_module_is_valid_python(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "fields.py").read_text()
        ast.parse(source, filename="fields.py")

    def test_schemas_imports_custom_field(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "from billing_client.fields import" in source
        assert "CurrencyField" in source

    def test_schemas_uses_custom_field_directly(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "currency = CurrencyField(" in source
        assert "ma.fields.CurrencyField" not in source

    def test_schemas_still_uses_ma_for_standard_fields(
        self, spec_with_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "amount = ma.fields.Integer(" in source

    def test_no_fields_module_without_custom_fields(
        self, spec_without_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_without_custom_field)
        package_dir = gen.generate(tmp_path)
        assert not (package_dir / "fields.py").exists()

    def test_no_custom_import_without_custom_fields(
        self, spec_without_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_without_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "from inventory_client.fields import" not in source

    def test_generated_files_are_valid_python(self, spec_with_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_custom_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_example_app_custom_field_roundtrip(self, example_spec, tmp_path):
        """End-to-end: example app with CurrencyField generates valid output."""
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        fields_source = (package_dir / "fields.py").read_text()
        assert "class CurrencyField(ma.fields.String):" in fields_source

        v1_schemas = (package_dir / "v1" / "schemas.py").read_text()
        assert "from example_client.fields import" in v1_schemas
        assert "CurrencyField" in v1_schemas

        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Custom field base-type edge cases (List, Nested, bare Field)
# ======================================================================


class TestCustomFieldListBaseType:
    """Custom List fields get an __init__ with a default inner type."""

    @pytest.fixture()
    def spec_with_list_custom_field(self):
        from pyramid_client_builder.models import CustomFieldInfo

        schema = SchemaInfo(
            name="FilterRequestSchema",
            fields=[
                SchemaFieldInfo(name="tags", field_type="TagListField", required=True),
            ],
        )
        return ClientSpec(
            name="search",
            endpoints=[
                EndpointInfo(
                    name="search",
                    path="/api/v1/search",
                    method="GET",
                    querystring_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="tags", location="querystring", type_hint="list"
                        ),
                    ],
                ),
            ],
            custom_fields=[
                CustomFieldInfo(class_name="TagListField", base_type="List"),
            ],
        )

    def test_list_custom_field_has_init(self, spec_with_list_custom_field, tmp_path):
        gen = ClientGenerator(spec_with_list_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "fields.py").read_text()
        assert "def __init__" in source
        assert "ma.fields.String()" in source

    def test_list_custom_field_is_valid_python(
        self, spec_with_list_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_with_list_custom_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


class TestCustomFieldNestedBaseType:
    """Custom Nested fields get an __init__ with a default schema."""

    @pytest.fixture()
    def spec_with_nested_custom_field(self):
        from pyramid_client_builder.models import CustomFieldInfo

        schema = SchemaInfo(
            name="OrderRequestSchema",
            fields=[
                SchemaFieldInfo(
                    name="details", field_type="DetailField", required=True
                ),
            ],
        )
        return ClientSpec(
            name="orders",
            endpoints=[
                EndpointInfo(
                    name="orders",
                    path="/api/v1/orders",
                    method="POST",
                    request_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="details", location="body", type_hint="dict"
                        ),
                    ],
                ),
            ],
            custom_fields=[
                CustomFieldInfo(class_name="DetailField", base_type="Nested"),
            ],
        )

    def test_nested_custom_field_has_init(
        self, spec_with_nested_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_with_nested_custom_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "fields.py").read_text()
        assert "def __init__" in source
        assert "ma.Schema" in source

    def test_nested_custom_field_is_valid_python(
        self, spec_with_nested_custom_field, tmp_path
    ):
        gen = ClientGenerator(spec_with_nested_custom_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Schema fields: Nested -> Dict fallback, List with inner type
# ======================================================================


class TestNestedFieldFallback:
    """Nested schema fields without a schema reference fall back to Dict."""

    @pytest.fixture()
    def spec_with_nested_schema_field(self):
        schema = SchemaInfo(
            name="EntityResponseSchema",
            fields=[
                SchemaFieldInfo(name="name", field_type="String", required=True),
                SchemaFieldInfo(
                    name="phones",
                    field_type="Nested",
                    metadata={"description": "Phone list"},
                ),
                SchemaFieldInfo(
                    name="documents",
                    field_type="Nested",
                    metadata={"description": "Document list"},
                ),
            ],
        )
        return ClientSpec(
            name="legal_entity",
            endpoints=[
                EndpointInfo(
                    name="entities",
                    path="/api/v1/entities",
                    method="GET",
                    response_schema=schema,
                ),
            ],
        )

    def test_nested_fields_become_dict(self, spec_with_nested_schema_field, tmp_path):
        gen = ClientGenerator(spec_with_nested_schema_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "ma.fields.Dict(" in source
        assert "ma.fields.Nested(" not in source

    def test_nested_fallback_is_valid_python(
        self, spec_with_nested_schema_field, tmp_path
    ):
        gen = ClientGenerator(spec_with_nested_schema_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


class TestListFieldInnerType:
    """List schema fields get a default inner type (String)."""

    @pytest.fixture()
    def spec_with_list_schema_field(self):
        schema = SchemaInfo(
            name="TagsQuerySchema",
            fields=[
                SchemaFieldInfo(
                    name="tags",
                    field_type="List",
                    metadata={"description": "Filter tags"},
                ),
            ],
        )
        return ClientSpec(
            name="tagging",
            endpoints=[
                EndpointInfo(
                    name="tags",
                    path="/api/v1/tags",
                    method="GET",
                    querystring_schema=schema,
                    parameters=[
                        ParameterInfo(
                            name="tags", location="querystring", type_hint="list"
                        ),
                    ],
                ),
            ],
        )

    def test_list_field_has_inner_type(self, spec_with_list_schema_field, tmp_path):
        gen = ClientGenerator(spec_with_list_schema_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "ma.fields.List(ma.fields.String()" in source

    def test_list_field_is_valid_python(self, spec_with_list_schema_field, tmp_path):
        gen = ClientGenerator(spec_with_list_schema_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


# ======================================================================
# Schema fields: Enum -> String fallback
# ======================================================================


class TestEnumFieldFallback:
    """Enum schema fields without an enum class fall back to String."""

    @pytest.fixture()
    def spec_with_enum_schema_field(self):
        schema = SchemaInfo(
            name="EntityResponseSchema",
            fields=[
                SchemaFieldInfo(name="name", field_type="String", required=True),
                SchemaFieldInfo(
                    name="origin",
                    field_type="Enum",
                    metadata={"description": "Entity origin"},
                ),
                SchemaFieldInfo(
                    name="status",
                    field_type="Enum",
                    required=True,
                ),
            ],
        )
        return ClientSpec(
            name="legal_entity",
            endpoints=[
                EndpointInfo(
                    name="entities",
                    path="/api/v1/entities",
                    method="GET",
                    response_schema=schema,
                ),
            ],
        )

    def test_enum_fields_become_string(self, spec_with_enum_schema_field, tmp_path):
        gen = ClientGenerator(spec_with_enum_schema_field)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "v1" / "schemas.py").read_text()
        assert "ma.fields.String(" in source
        assert "ma.fields.Enum(" not in source

    def test_enum_fallback_is_valid_python(self, spec_with_enum_schema_field, tmp_path):
        gen = ClientGenerator(spec_with_enum_schema_field)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.rglob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))
