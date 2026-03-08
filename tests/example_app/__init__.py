"""Minimal Pyramid + Cornice app that mirrors payments' patterns.

Used for real-world testing of pyramid-client-builder without needing
external infrastructure (PostgreSQL, Redis, etc.).
"""

from pyramid.config import Configurator


def main(global_config, **settings):
    with Configurator(settings=settings) as config:
        config.include("cornice")
        config.include(".routes")
        config.include(".views")
        config.scan()
    return config.make_wsgi_app()
