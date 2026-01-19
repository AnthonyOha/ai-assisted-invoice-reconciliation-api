from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import AmountRange, DateTimeRange, OrmBase


class BankTransactionIn(BaseModel):
    external_id: str | None = Field(default=None, max_length=128)
    posted_at: datetime
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = None


class BankTransactionOut(OrmBase):
    id: int
    tenant_id: int
    external_id: str | None
    posted_at: datetime
    amount: float
    currency: str
    description: str | None
    created_at: datetime


class BankTransactionFilters(BaseModel):
    posted_at: DateTimeRange | None = None
    amount: AmountRange | None = None
    description_contains: str | None = None
