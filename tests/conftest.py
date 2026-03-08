"""Shared fixtures for pyramid-client-builder tests."""

import pytest
from pyramid import testing
from pyramid.config import Configurator


@pytest.fixture()
def example_registry():
    """Boot the example app and return its registry."""
    with Configurator(settings={}) as config:
        config.include("cornice")
        config.include("tests.example_app.routes")
        config.include("tests.example_app.views")
        config.scan("tests.example_app.views")
        config.commit()
        yield config.registry


@pytest.fixture()
def plain_registry():
    """A Pyramid registry with plain routes only (no Cornice)."""
    with Configurator(settings={}) as config:
        config.add_route("home", "/")
        config.add_route("health", "/health")
        config.add_route("items", "/api/v1/items")
        config.add_route("item_detail", "/api/v1/items/{item_id}")
        config.add_view(
            lambda r: {"ok": True},
            route_name="home",
            renderer="json",
        )
        config.add_view(
            lambda r: {"status": "ok"},
            route_name="health",
            renderer="json",
        )
        config.add_view(
            lambda r: {"items": []},
            route_name="items",
            renderer="json",
            request_method="GET",
        )
        config.add_view(
            lambda r: {"id": "new"},
            route_name="items",
            renderer="json",
            request_method="POST",
        )
        config.add_view(
            lambda r: {"id": r.matchdict["item_id"]},
            route_name="item_detail",
            renderer="json",
            request_method="GET",
        )
        config.commit()
        yield config.registry
