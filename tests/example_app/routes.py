"""Plain Pyramid routes (non-Cornice)."""


def includeme(config):
    config.add_route("home", "/")
    config.add_route("health", "/health")
