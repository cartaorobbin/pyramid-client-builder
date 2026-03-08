"""Tests for pyramid_client_builder.generator."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from pyramid_client_builder.generator.core import ClientGenerator
from pyramid_client_builder.introspection.core import PyramidIntrospector
from pyramid_client_builder.models import ClientSpec, EndpointInfo, ParameterInfo


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

    def test_generates_three_files(self, simple_spec, tmp_path):
        gen = ClientGenerator(simple_spec)
        package_dir = gen.generate(tmp_path)
        assert (package_dir / "__init__.py").exists()
        assert (package_dir / "client.py").exists()
        assert (package_dir / "ext.py").exists()

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

    def test_querystring_params_generate_params_dict(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "params = {}" in client_source
        assert "params=" in client_source

    def test_body_params_generate_json_body(self, example_spec, tmp_path):
        gen = ClientGenerator(example_spec)
        package_dir = gen.generate(tmp_path)
        client_source = (package_dir / "client.py").read_text()
        assert "json=body" in client_source


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
