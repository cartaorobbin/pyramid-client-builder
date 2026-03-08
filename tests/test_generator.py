"""Tests for pyramid_client_builder.generator."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from pyramid_client_builder.generator.core import ClientGenerator
from pyramid_client_builder.introspection.core import PyramidIntrospector
from pyramid_client_builder.models import (
    ClientSpec,
    EndpointInfo,
    ParameterInfo,
)


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
def example_spec(example_registry):
    """ClientSpec built from the real example app."""
    introspector = PyramidIntrospector(example_registry)
    return introspector.build_client_spec("example")


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

    def test_no_schemas_file_without_schemas(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert not (package_dir / "schemas.py").exists()

    def test_generated_client_is_valid_python(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.glob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_client_class_is_importable(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        spec = importlib.util.spec_from_file_location(
            "testapp_client.client",
            package_dir / "client.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "TestappClient")

    def test_generated_methods_exist(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        spec = importlib.util.spec_from_file_location(
            "testapp_client.client",
            package_dir / "client.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        client_cls = module.TestappClient
        method_names = [m for m in dir(client_cls) if not m.startswith("_")]
        assert "get_home" in method_names
        assert "list_items" in method_names
        assert "create_item" in method_names
        assert "get_item" in method_names

    def test_class_name_and_package_name(self, simple_spec):
        gen = ClientGenerator(simple_spec)
        assert gen.class_name == "TestappClient"
        assert gen.package_name == "testapp_client"
        assert gen.request_attr == "testapp_client"


class TestClientGeneratorWithExampleApp:

    def test_generates_from_real_app(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "client.py").exists()

    def test_all_generated_files_are_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.glob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_verb_naming_in_generated_client(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "def cancel_charge(" in client_source

    def test_list_naming_for_collections(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "def list_charges(" in client_source
        assert "def list_invoices(" in client_source

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

    def test_generates_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "schemas.py").exists()

    def test_schemas_file_is_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        ast.parse(source, filename="schemas.py")

    def test_schemas_file_contains_request_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class ChargeRequestSchema(ma.Schema):" in source
        assert "ma.fields.Integer" in source
        assert "ma.fields.String" in source

    def test_schemas_file_contains_querystring_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class ChargesQuerySchema(ma.Schema):" in source

    def test_schemas_file_contains_response_schema(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class ChargeResponseSchema(ma.Schema):" in source

    def test_client_imports_schemas(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "from example_client.schemas import" in client_source
        assert "ChargeRequestSchema" in client_source

    def test_client_uses_dump_for_body(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "ChargeRequestSchema().dump(" in client_source

    def test_client_uses_dump_for_querystring(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "ChargesQuerySchema().dump(" in client_source

    def test_client_uses_load_for_response(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "ChargeResponseSchema().load(response.json())" in client_source

    def test_client_falls_back_to_raw_json_without_response_schema(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "return response.json()" in client_source

    def test_body_params_generate_json_body(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "json=body" in client_source

    def test_init_exports_schemas(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        init_source = (package_dir / "__init__.py").read_text()
        assert "schemas" in init_source

    def test_composite_schema_generates_inner_schemas(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class RefundBodySchema(ma.Schema):" in source
        assert "class RefundQuerySchema(ma.Schema):" in source
        assert "RefundRequestSchema" not in source

    def test_composite_schema_refund_has_individual_params(
        self, example_spec, tmp_path
    ):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        for line in client_source.splitlines():
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
        client_source = (package_dir / "client.py").read_text()
        assert "RefundBodySchema().dump(" in client_source
        assert "RefundQuerySchema().dump(" in client_source


class TestPycornmarshGeneration:
    """Verify pycornmarsh-style endpoints generate correct client code."""

    def test_pcm_schemas_in_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class SimulateBodySchema(ma.Schema):" in source
        assert "class SimulateQuerySchema(ma.Schema):" in source
        assert "class SimulateResponseSchema(ma.Schema):" in source

    def test_pcm_client_uses_body_schema_dump(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "SimulateBodySchema().dump(" in client_source

    def test_pcm_client_uses_querystring_schema_dump(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "SimulateQuerySchema().dump(" in client_source

    def test_pcm_client_uses_response_schema_load(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "SimulateResponseSchema().load(response.json())" in client_source

    def test_pcm_endpoint_has_individual_params(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        for line in client_source.splitlines():
            if "def simulate_financing(" in line:
                assert "amount: int" in line
                assert "term_months: int" in line
                break
        else:
            raise AssertionError("simulate_financing not found")

    def test_pcm_error_schema_in_schemas_file(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        source = (package_dir / "schemas.py").read_text()
        assert "class RequestErrorSchema(ma.Schema):" in source

    def test_pcm_generated_code_is_valid_python(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        for py_file in package_dir.glob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))


class TestMethodSignatures:
    """Verify generated methods use individual parameters, not body: dict."""

    def test_body_params_are_individual_arguments(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "body: dict" not in client_source

    def test_create_charge_has_individual_params(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "def create_charge(self, amount: int" in client_source
        assert "currency: str" in client_source
        assert "part_id: str" in client_source
        assert "description: str | None = None" in client_source

    def test_required_params_before_optional(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        for line in client_source.splitlines():
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
        client_source = (package_dir / "client.py").read_text()
        assert '"amount": amount' in client_source
        assert '"currency": currency' in client_source

    def test_simple_spec_body_uses_individual_params(
        self, simple_spec, tmp_path
    ):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "body: dict" not in client_source
        assert "def create_item(self, name: str, price: int)" in client_source

    def test_simple_spec_body_built_from_params(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert '"name": name' in client_source
        assert '"price": price' in client_source


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
        gen._annotate_endpoints()
        names = [ep.method_name for ep in spec.endpoints]  # type: ignore[attr-defined]
        assert names[0] == "list_things"
        assert names[1] == "list_things_1"
