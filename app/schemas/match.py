from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.models import MatchStatus
from app.schemas.common import OrmBase


class MatchOut(OrmBase):
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: float
    status: MatchStatus
    created_at: datetime


class ReconcileRequest(BaseModel):
    max_candidates_per_invoice: int = Field(default=3, ge=1, le=10)
    date_window_days: int = Field(default=3, ge=0, le=30)


class AIExplainOut(BaseModel):
    explanation: str
    confidence: str
    used_ai: bool
