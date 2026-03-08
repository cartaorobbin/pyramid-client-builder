"""Views for the example app, using both plain Pyramid and Cornice."""

from cornice import Service
from cornice.validators import (
    marshmallow_querystring_validator,
    marshmallow_validator,
)
from pyramid.view import view_config

from tests.example_app.schemas import (
    ChargeRequestSchema,
    ChargesQuerySchema,
    InvoiceQuerySchema,
)

# --- Plain Pyramid views ---


@view_config(route_name="home", renderer="json")
def home(request):
    """Application home."""
    return {"app": "example"}


@view_config(route_name="health", renderer="json")
def health(request):
    """Health check endpoint."""
    return {"status": "ok"}


# --- Cornice services (mirrors payments charge API) ---

charges_service = Service(
    name="charges",
    path="/api/v1/charges",
    description="Charge management service",
    cors_origins=("*",),
)


@charges_service.post(
    schema=ChargeRequestSchema,
    validators=(marshmallow_validator,),
)
def create_charge(request):
    """Create a new charge."""
    return {"id": "ch_123", "status": "created"}


@charges_service.get(
    schema=ChargesQuerySchema,
    validators=(marshmallow_querystring_validator,),
)
def list_charges(request):
    """List charges with optional filters."""
    return {"results": [], "total": 0}


charge_detail_service = Service(
    name="charge_detail",
    path="/api/v1/charges/{charge_id}",
    description="Single charge operations",
)


@charge_detail_service.get()
def get_charge(request):
    """Get a single charge by ID."""
    return {"id": request.matchdict["charge_id"], "status": "active"}


charge_cancel_service = Service(
    name="charge_cancel",
    path="/api/v1/charges/{charge_id}/cancel",
    description="Cancel a charge",
)


@charge_cancel_service.post()
def cancel_charge(request):
    """Cancel an existing charge."""
    return {"id": request.matchdict["charge_id"], "status": "cancelled"}


# --- Cornice service for invoices (mirrors DDA pattern) ---

invoices_service = Service(
    name="invoices",
    path="/api/v1/invoices",
    description="Invoice listing service",
)


@invoices_service.get(
    schema=InvoiceQuerySchema,
    validators=(marshmallow_querystring_validator,),
)
def list_invoices(request):
    """List invoices for a part."""
    return {"results": [], "total": 0}


def includeme(config):
    config.scan(".")
