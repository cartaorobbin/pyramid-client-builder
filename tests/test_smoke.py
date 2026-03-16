"""Smoke tests that verify generated code actually works."""

import os
import subprocess
import sys

from click.testing import CliRunner

from pyramid_client_builder.cli import pclient_build


class TestSmokeGenerated:

    def _generate(self, tmp_path):
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

    def test_python_requests_import_and_instantiate(self, tmp_path):
        self._generate(tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from example_client import ExampleClient; "
                "c = ExampleClient('http://localhost'); "
                "assert hasattr(c, 'v1')",
            ],
            env={**os.environ, "PYTHONPATH": str(tmp_path / "python_requests")},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_python_httpx_import_and_instantiate(self, tmp_path):
        self._generate(tmp_path)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from example_client import ExampleClient; "
                "c = ExampleClient('http://localhost'); "
                "assert hasattr(c, 'v1')",
            ],
            env={**os.environ, "PYTHONPATH": str(tmp_path / "python_httpx")},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_go_compiles(self, tmp_path):
        self._generate(tmp_path)
        result = subprocess.run(
            ["go", "build", "./..."],
            cwd=str(tmp_path / "go"),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_flutter_dart_analyzes(self, tmp_path):
        self._generate(tmp_path)
        dart_dir = tmp_path / "flutter"
        subprocess.run(
            ["dart", "pub", "get"],
            cwd=str(dart_dir),
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["dart", "analyze", "--fatal-infos"],
            cwd=str(dart_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
