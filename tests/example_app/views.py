"""Views for the example app, using both plain Pyramid and Cornice."""

from cornice import Service
from cornice.validators import (
    marshmallow_querystring_validator,
    marshmallow_validator,
)
from pyramid.view import view_config

from tests.example_app.schemas import (
    ChargeRequestSchema,
    ChargeResponseSchema,
    ChargesQuerySchema,
    CompanyRelationshipPathSchema,
    CompanyRelationshipQuerySchema,
    CompanyRelationshipsResponseSchema,
    DocumentConciliateRequestSchema,
    InvoiceQuerySchema,
    RefundRequestSchema,
    RequestErrorSchema,
    SimulateBodySchema,
    SimulateQuerySchema,
    SimulateRequestSchema,
    SimulateResponseSchema,
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


create_charge.response_schema = ChargeResponseSchema


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


# --- Cornice service with composite schema (location-aware pattern) ---

refund_service = Service(
    name="refunds",
    path="/api/v1/charges/{charge_id}/refund",
    description="Refund a charge",
)


@refund_service.post(
    schema=RefundRequestSchema,
    validators=(marshmallow_validator,),
)
def create_refund(request):
    """Create a refund for a charge."""
    return {"id": "rf_123", "status": "refunded"}


# --- Cornice service with pycornmarsh-style metadata ---

simulate_service = Service(
    name="simulate",
    path="/api/v1/financing/simulate",
    description="Financing simulation",
)


@simulate_service.post(
    pcm_show="v1",
    pcm_responses={200: SimulateResponseSchema, 400: RequestErrorSchema},
    schema=SimulateRequestSchema,
    pcm_request=dict(body=SimulateBodySchema, querystring=SimulateQuerySchema),
    validators=(marshmallow_validator,),
)
def simulate_financing(request):
    """Simulate a financing plan."""
    return {"monthly_payment": 100.0, "total_interest": 200.0, "total_amount": 1200.0}


# --- Cornice service with empty request schema (no fields) ---

document_conciliate_service = Service(
    name="document_conciliate",
    path="/api/v1/documents/conciliate",
    description="Conciliate a document (empty request schema)",
)


@document_conciliate_service.post(
    schema=DocumentConciliateRequestSchema,
    validators=(marshmallow_validator,),
)
def conciliate_document(request):
    """Conciliate a document using an empty request schema."""
    return {"status": "conciliated"}


# --- Cornice service with regex path param (company relationships) ---

company_relationship_service = Service(
    name="company_relationship",
    path=r"/api/v1/companies/{uuid_or_tax_id:[^/]+}/relationships",
    description="Company relationships API",
    cors_origins=("*",),
)


@company_relationship_service.get(
    pcm_show="v1",
    pcm_request=dict(
        path=CompanyRelationshipPathSchema,
        querystring=CompanyRelationshipQuerySchema,
    ),
    pcm_responses={200: CompanyRelationshipsResponseSchema},
)
def list_company_relationships(request):
    """List relationships for a company."""
    return {"company_relationships": []}


def includeme(config):
    config.scan(".")
