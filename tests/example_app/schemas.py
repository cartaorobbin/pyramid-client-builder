"""Marshmallow schemas for the example app (mirrors payments patterns)."""

import marshmallow as ma


class ChargeRequestSchema(ma.Schema):
    amount = ma.fields.Integer(required=True, metadata={"description": "Amount in cents"})
    currency = ma.fields.String(required=True, metadata={"description": "ISO currency code"})
    description = ma.fields.String(metadata={"description": "Charge description"})
    part_id = ma.fields.String(required=True, metadata={"description": "Part identifier"})


class ChargeResponseSchema(ma.Schema):
    id = ma.fields.String()
    amount = ma.fields.Integer()
    currency = ma.fields.String()
    status = ma.fields.String()


class ChargesQuerySchema(ma.Schema):
    part_id = ma.fields.String(metadata={"description": "Filter by part"})
    status = ma.fields.String(metadata={"description": "Filter by status"})
    page = ma.fields.Integer(metadata={"description": "Page number"})
    per_page = ma.fields.Integer(metadata={"description": "Items per page"})


class ChargePathSchema(ma.Schema):
    charge_id = ma.fields.String(required=True)


class InvoiceQuerySchema(ma.Schema):
    part_id = ma.fields.String(required=True, metadata={"description": "Part identifier"})
    status = ma.fields.String(metadata={"description": "Filter by status"})


# --- Composite schema (Cornice location-aware pattern) ---


class RefundBodySchema(ma.Schema):
    amount = ma.fields.Integer(required=True)
    reason = ma.fields.String()


class RefundQuerySchema(ma.Schema):
    notify = ma.fields.Boolean()


class RefundRequestSchema(ma.Schema):
    """Composite schema — Cornice splits body/querystring/path automatically."""

    body = ma.fields.Nested(RefundBodySchema)
    querystring = ma.fields.Nested(RefundQuerySchema)


# --- pycornmarsh-style schemas (pcm_request / pcm_responses) ---


class SimulateBodySchema(ma.Schema):
    amount = ma.fields.Integer(
        required=True, metadata={"description": "Amount in cents"}
    )
    term_months = ma.fields.Integer(
        required=True, metadata={"description": "Loan term"}
    )
    rate = ma.fields.Float(metadata={"description": "Interest rate"})


class SimulateQuerySchema(ma.Schema):
    currency = ma.fields.String(metadata={"description": "ISO currency code"})


class SimulateRequestSchema(ma.Schema):
    """Validation schema used by Cornice (may differ from the pcm_request body)."""

    amount = ma.fields.Integer(required=True)
    term_months = ma.fields.Integer(required=True)
    rate = ma.fields.Float()
    currency = ma.fields.String()


class SimulateResponseSchema(ma.Schema):
    monthly_payment = ma.fields.Float()
    total_interest = ma.fields.Float()
    total_amount = ma.fields.Float()


class RequestErrorSchema(ma.Schema):
    error = ma.fields.String()
    details = ma.fields.Dict()
