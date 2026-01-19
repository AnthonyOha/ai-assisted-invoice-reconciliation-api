from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.bank_transaction import (
    BankTransactionFilters,
    BankTransactionIn,
    BankTransactionOut,
)
from app.schemas.common import AmountRange, DateTimeRange
from app.services.bank_transactions import BankTransactionService, IdempotencyConflict

router = APIRouter(prefix="/tenants/{tenant_id}/bank-transactions", tags=["bank-transactions"])


@router.post("/import", status_code=status.HTTP_200_OK)
def import_transactions(
    tenant_id: int,
    payload: list[BankTransactionIn],
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    try:
        return BankTransactionService(db).import_transactions(
            tenant_id=tenant_id, transactions=payload, idempotency_key=idempotency_key
        )
    except IdempotencyConflict as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[BankTransactionOut])
def list_transactions(
    tenant_id: int,
    db: Session = Depends(get_db),
    posted_start: datetime | None = Query(default=None),
    posted_end: datetime | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
    description_contains: str | None = Query(default=None),
):
    filters = BankTransactionFilters(
        posted_at=DateTimeRange(start=posted_start, end=posted_end) if (posted_start or posted_end) else None,
        amount=AmountRange(min=amount_min, max=amount_max) if (amount_min is not None or amount_max is not None) else None,
        description_contains=description_contains,
    )
    return BankTransactionService(db).list_transactions(tenant_id=tenant_id, filters=filters)
