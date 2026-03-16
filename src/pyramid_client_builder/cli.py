"""CLI entry point for pyramid-client-builder.

Usage:
    pclient-build development.ini --name payments --output ./generated/
"""

import logging
import sys
from pathlib import Path

import click
from pyramid.paster import bootstrap, setup_logging

from pyramid_client_builder.generator.core import ClientGenerator
from pyramid_client_builder.generator.flutter_core import FlutterClientGenerator
from pyramid_client_builder.generator.go_core import GoClientGenerator
from pyramid_client_builder.introspection import PyramidIntrospector

logger = logging.getLogger(__name__)


@click.command()
@click.version_option(package_name="pyramid-client-builder")
@click.argument("ini_file", type=click.Path(exists=True, readable=True))
@click.option(
    "--name",
    required=True,
    help="Client name (e.g. 'payments'). Used for class name, settings prefix, "
    "and request attribute.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(),
    help="Output directory for the generated client variants.",
)
@click.option(
    "--include",
    multiple=True,
    help="Glob pattern to include routes (can be specified multiple times).",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Glob pattern to exclude routes (can be specified multiple times).",
)
@click.option(
    "--client-version",
    default="0.1.0",
    show_default=True,
    help="Version for the generated client packages.",
)
@click.option(
    "--go-module",
    default="",
    help="Go module path (e.g. 'github.com/org/payments-client'). "
    "Defaults to '<name>-client'.",
)
@click.option(
    "--flutter-package",
    default="",
    help="Dart package name (e.g. 'payments_client'). " "Defaults to '<name>_client'.",
)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
def pclient_build(
    ini_file,
    name,
    output,
    include,
    exclude,
    client_version,
    go_module,
    flutter_package,
    debug,
):
    """Generate HTTP clients from a Pyramid application's routes.

    Boots the Pyramid app from INI_FILE, introspects its routes and Cornice
    services, and writes client packages for all supported variants
    (python_requests, python_httpx, go, flutter) into subdirectories of --output.

    Examples:

        pclient-build development.ini --name payments --output ./generated/

        pclient-build production.ini --name payments --output ./clients/ \\
            --include "/api/v1/*" --exclude "/api/v1/webhooks/*"
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)-8s %(message)s",
        stream=sys.stderr,
    )

    setup_logging(ini_file)

    click.echo(f"Bootstrapping Pyramid from {ini_file}", err=True)
    env = bootstrap(ini_file)

    try:
        registry = env["registry"]

        introspector = PyramidIntrospector(registry)
        spec = introspector.build_client_spec(
            name=name,
            include_patterns=list(include) if include else None,
            exclude_patterns=list(exclude) if exclude else None,
        )

        click.echo(f"Discovered {len(spec.endpoints)} endpoints", err=True)

        if not spec.endpoints:
            click.echo(
                "No endpoints found. Check your include/exclude patterns.",
                err=True,
            )
            raise SystemExit(1)

        output_path = Path(output)

        variants = [
            (
                "python_requests",
                ClientGenerator(spec, version=client_version, http_client="requests"),
            ),
            (
                "python_httpx",
                ClientGenerator(spec, version=client_version, http_client="httpx"),
            ),
            (
                "go",
                GoClientGenerator(spec, version=client_version, go_module=go_module),
            ),
            (
                "flutter",
                FlutterClientGenerator(
                    spec,
                    version=client_version,
                    flutter_package=flutter_package,
                ),
            ),
        ]

        for variant_name, generator in variants:
            variant_dir = output_path / variant_name
            generator.generate(variant_dir)
            click.echo(f"  Generated {variant_name}/ ", err=True)

        click.echo("", err=True)
        click.echo(f"Generated clients at {output_path}", err=True)
        click.echo(f"  Name:      {name}", err=True)
        click.echo("  Variants:  python_requests, python_httpx, go, flutter", err=True)
        click.echo(f"  Endpoints: {len(spec.endpoints)}", err=True)
        click.echo(f"  Settings:  {spec.settings_prefix}.base_url", err=True)

        if debug:
            for ep in spec.endpoints:
                click.echo(f"    {ep.method:6s} {ep.path}", err=True)

    finally:
        env["closer"]()
