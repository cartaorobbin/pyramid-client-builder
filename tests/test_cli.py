"""Tests for pyramid_client_builder.cli."""

import ast
from pathlib import Path

from click.testing import CliRunner

from pyramid_client_builder.cli import pclient_build


class TestPclientBuild:

    def test_generates_client_package(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "example",
                "--output", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        package_dir = tmp_path / "example_client"
        assert package_dir.exists()
        assert (package_dir / "client.py").exists()
        assert (package_dir / "ext.py").exists()
        assert (package_dir / "__init__.py").exists()

    def test_generated_code_is_valid(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "example",
                "--output", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        for py_file in (tmp_path / "example_client").glob("*.py"):
            source = py_file.read_text()
            ast.parse(source, filename=str(py_file))

    def test_debug_flag_shows_endpoints(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "example",
                "--output", str(tmp_path),
                "--debug",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "GET" in result.output
        assert "/api/v1/charges" in result.output

    def test_missing_name_fails(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--output", str(tmp_path),
            ],
        )
        assert result.exit_code != 0

    def test_missing_output_fails(self):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "example",
            ],
        )
        assert result.exit_code != 0

    def test_nonexistent_ini_fails(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "nonexistent.ini",
                "--name", "example",
                "--output", str(tmp_path),
            ],
        )
        assert result.exit_code != 0

    def test_include_filter(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "filtered",
                "--output", str(tmp_path),
                "--include", "/api/v1/charges*",
                "--debug",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "/api/v1/invoices" not in result.output

    def test_exclude_filter(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name", "filtered",
                "--output", str(tmp_path),
                "--exclude", "/api/v1/invoices",
                "--debug",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "/api/v1/invoices" not in result.output
