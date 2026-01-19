from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.models import InvoiceStatus
from app.schemas.common import AmountRange, DateRange, OrmBase


class InvoiceCreate(BaseModel):
    vendor_id: int | None = None
    invoice_number: str | None = Field(default=None, max_length=64)
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    invoice_date: date | None = None
    description: str | None = None


class InvoiceOut(OrmBase):
    id: int
    tenant_id: int
    vendor_id: int | None
    invoice_number: str | None
    amount: float
    currency: str
    invoice_date: date | None
    description: str | None
    status: InvoiceStatus
    created_at: datetime


class InvoiceFilters(BaseModel):
    status: InvoiceStatus | None = None
    vendor_id: int | None = None
    invoice_date: DateRange | None = None
    amount: AmountRange | None = None
