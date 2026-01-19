from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.models import InvoiceStatus
from app.schemas.common import AmountRange, DateRange
from app.schemas.invoice import InvoiceCreate, InvoiceFilters, InvoiceOut
from app.services.invoices import InvoiceService

router = APIRouter(prefix="/tenants/{tenant_id}/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(tenant_id: int, payload: InvoiceCreate, db: Session = Depends(get_db)):
    svc = InvoiceService(db)
    invoice = svc.create_invoice(tenant_id=tenant_id, data=payload)
    return invoice


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    tenant_id: int,
    db: Session = Depends(get_db),
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    vendor_id: int | None = Query(default=None),
    date_start: date | None = Query(default=None),
    date_end: date | None = Query(default=None),
    amount_min: float | None = Query(default=None, ge=0),
    amount_max: float | None = Query(default=None, ge=0),
):
    filters = InvoiceFilters(
        status=status_filter,
        vendor_id=vendor_id,
        invoice_date=DateRange(start=date_start, end=date_end) if (date_start or date_end) else None,
        amount=AmountRange(min=amount_min, max=amount_max) if (amount_min is not None or amount_max is not None) else None,
    )
    return InvoiceService(db).list_invoices(tenant_id=tenant_id, filters=filters)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(tenant_id: int, invoice_id: int, db: Session = Depends(get_db)):
    ok = InvoiceService(db).delete_invoice(tenant_id=tenant_id, invoice_id=invoice_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return None
