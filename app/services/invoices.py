from __future__ import annotations

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.models.models import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceFilters


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_invoice(self, *, tenant_id: int, data: InvoiceCreate) -> Invoice:
        invoice = Invoice(
            tenant_id=tenant_id,
            vendor_id=data.vendor_id,
            invoice_number=data.invoice_number,
            amount=data.amount,
            currency=data.currency,
            invoice_date=data.invoice_date,
            description=data.description,
        )
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def list_invoices(self, *, tenant_id: int, filters: InvoiceFilters | None = None) -> list[Invoice]:
        stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
        if filters:
            if filters.status:
                stmt = stmt.where(Invoice.status == filters.status)
            if filters.vendor_id:
                stmt = stmt.where(Invoice.vendor_id == filters.vendor_id)
            if filters.invoice_date:
                if filters.invoice_date.start:
                    stmt = stmt.where(Invoice.invoice_date >= filters.invoice_date.start)
                if filters.invoice_date.end:
                    stmt = stmt.where(Invoice.invoice_date <= filters.invoice_date.end)
            if filters.amount:
                if filters.amount.min is not None:
                    stmt = stmt.where(Invoice.amount >= filters.amount.min)
                if filters.amount.max is not None:
                    stmt = stmt.where(Invoice.amount <= filters.amount.max)
        stmt = stmt.order_by(Invoice.id)
        return list(self.db.scalars(stmt))

    def get_invoice(self, *, tenant_id: int, invoice_id: int) -> Invoice | None:
        stmt = select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id))
        return self.db.scalar(stmt)

    def delete_invoice(self, *, tenant_id: int, invoice_id: int) -> bool:
        stmt = delete(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id))
        res = self.db.execute(stmt)
        return res.rowcount > 0
