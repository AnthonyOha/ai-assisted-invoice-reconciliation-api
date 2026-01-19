from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.match import AIExplainOut, MatchOut, ReconcileRequest
from app.services.explain import ExplanationService
from app.services.reconciliation import ReconciliationService

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["reconciliation"])


@router.post("/reconcile", response_model=list[MatchOut], status_code=status.HTTP_200_OK)
def reconcile(tenant_id: int, payload: ReconcileRequest | None = None, db: Session = Depends(get_db)):
    return ReconciliationService(db).reconcile(tenant_id=tenant_id, request=payload)


@router.post("/matches/{match_id}/confirm", response_model=MatchOut, status_code=status.HTTP_200_OK)
def confirm_match(tenant_id: int, match_id: int, db: Session = Depends(get_db)):
    try:
        return ReconciliationService(db).confirm_match(tenant_id=tenant_id, match_id=match_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Match not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reconcile/explain", response_model=AIExplainOut)
async def explain(
    tenant_id: int,
    invoice_id: int = Query(...),
    transaction_id: int = Query(..., alias="transaction_id"),
    db: Session = Depends(get_db),
):
    try:
        return await ExplanationService(db).explain(tenant_id=tenant_id, invoice_id=invoice_id, txn_id=transaction_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Invoice or transaction not found")
