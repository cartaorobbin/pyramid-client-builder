"""Tests for pyramid_client_builder.cli."""

import ast

from click.testing import CliRunner

from pyramid_client_builder.cli import pclient_build


class TestPclientBuild:

    def test_generates_all_variants(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "python_requests").is_dir()
        assert (tmp_path / "python_httpx").is_dir()
        assert (tmp_path / "go").is_dir()

    def test_python_requests_variant(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        pkg = tmp_path / "python_requests" / "example_client"
        assert pkg.exists()
        assert (pkg / "client.py").exists()
        assert (pkg / "ext.py").exists()
        assert (pkg / "__init__.py").exists()

    def test_python_httpx_variant(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        pkg = tmp_path / "python_httpx" / "example_client"
        assert pkg.exists()
        assert (pkg / "client.py").exists()
        source = (pkg / "client.py").read_text()
        assert "import httpx" in source

    def test_go_variant(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        go_dir = tmp_path / "go"
        assert (go_dir / "go.mod").exists()
        assert (go_dir / "client.go").exists()

    def test_python_requests_uses_requests(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        source = (
            tmp_path / "python_requests" / "example_client" / "client.py"
        ).read_text()
        assert "import requests" in source
        assert "import httpx" not in source

    def test_generated_python_is_valid(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        for variant in ("python_requests", "python_httpx"):
            pkg = tmp_path / variant / "example_client"
            for py_file in pkg.rglob("*.py"):
                source = py_file.read_text()
                ast.parse(source, filename=str(py_file))

    def test_debug_flag_shows_endpoints(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
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
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0

    def test_missing_output_fails(self):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
            ],
        )
        assert result.exit_code != 0

    def test_nonexistent_ini_fails(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "nonexistent.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0

    def test_include_filter(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "filtered",
                "--output",
                str(tmp_path),
                "--include",
                "/api/v1/charges*",
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
                "--name",
                "filtered",
                "--output",
                str(tmp_path),
                "--exclude",
                "/api/v1/invoices",
                "--debug",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "/api/v1/invoices" not in result.output

    def test_go_module_option(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
                "--go-module",
                "github.com/myorg/example-client",
            ],
        )
        assert result.exit_code == 0, result.output
        content = (tmp_path / "go" / "go.mod").read_text()
        assert "module github.com/myorg/example-client" in content

    def test_output_summary_mentions_variants(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            pclient_build,
            [
                "tests/example_app/example.ini",
                "--name",
                "example",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        assert "python_requests" in result.output
        assert "python_httpx" in result.output
        assert "go" in result.output
