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
