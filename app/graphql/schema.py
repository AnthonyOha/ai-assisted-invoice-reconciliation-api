from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.models import InvoiceStatus
from app.schemas.bank_transaction import BankTransactionIn
from app.schemas.invoice import InvoiceCreate, InvoiceFilters
from app.schemas.match import ReconcileRequest
from app.schemas.tenant import TenantCreate
from app.services.bank_transactions import BankTransactionService, IdempotencyConflict
from app.services.explain import ExplanationService
from app.services.invoices import InvoiceService
from app.services.reconciliation import ReconciliationService
from app.services.tenants import TenantService


# ---------------------------
# GraphQL context (per request)
# ---------------------------

@dataclass
class Context:
    db: Session


def get_context():
    db = SessionLocal()
    try:
        yield Context(db=db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------
# GraphQL Types
# ---------------------------

@strawberry.type
class TenantType:
    id: int
    name: str
    created_at: datetime


@strawberry.enum
class GInvoiceStatus(Enum):
    open = "open"
    matched = "matched"
    paid = "paid"


@strawberry.type
class InvoiceType:
    id: int
    tenant_id: int
    vendor_id: int | None
    invoice_number: str | None
    amount: float
    currency: str
    invoice_date: date | None
    description: str | None
    status: GInvoiceStatus
    created_at: datetime


@strawberry.input
class InvoiceInput:
    vendor_id: int | None = None
    invoice_number: str | None = None
    amount: float = 0.0
    currency: str = "USD"
    invoice_date: date | None = None
    description: str | None = None


@strawberry.type
class BankTransactionType:
    id: int
    tenant_id: int
    external_id: str | None
    posted_at: datetime
    amount: float
    currency: str
    description: str | None
    created_at: datetime


@strawberry.input
class BankTransactionInput:
    external_id: str | None = None
    posted_at: datetime
    amount: float
    currency: str = "USD"
    description: str | None = None


@strawberry.enum
class GMatchStatus(Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"


@strawberry.type
class MatchType:
    id: int
    tenant_id: int
    invoice_id: int
    bank_transaction_id: int
    score: float
    status: GMatchStatus
    created_at: datetime


@strawberry.type
class AIExplainType:
    explanation: str
    confidence: str
    used_ai: bool


@strawberry.input
class TenantInput:
    name: str


@strawberry.input
class InvoiceFilterInput:
    status: GInvoiceStatus | None = None
    vendor_id: int | None = None
    date_start: date | None = None
    date_end: date | None = None
    amount_min: float | None = None
    amount_max: float | None = None


@strawberry.input
class PaginationInput:
    limit: int = 50
    offset: int = 0

@strawberry.input
class ReconcileRequestInput:
    invoice_id: int | None = None
    bank_transaction_id: int | None = None
    confirm: bool | None = None
# ---------------------------
# Query
# ---------------------------

@strawberry.type
class Query:
    @strawberry.field
    def tenants(self, info: Info) -> list[TenantType]:
        db = info.context.db
        items = TenantService(db).list_tenants()
        return [TenantType(id=t.id, name=t.name, created_at=t.created_at) for t in items]

    @strawberry.field
    def invoices(
        self,
        info: Info,
        tenant_id: int,
        filters: InvoiceFilterInput | None = None,
        pagination: PaginationInput | None = None,
    ) -> list[InvoiceType]:
        db = info.context.db

        f = None
        if filters:
            f = InvoiceFilters(
                status=InvoiceStatus(filters.status.value) if filters.status else None,
                vendor_id=filters.vendor_id,
                invoice_date=(
                    None
                    if not (filters.date_start or filters.date_end)
                    else {"start": filters.date_start, "end": filters.date_end}
                ),
                amount=(
                    None
                    if (filters.amount_min is None and filters.amount_max is None)
                    else {"min": filters.amount_min, "max": filters.amount_max}
                ),
            )

            # convert dict to pydantic submodels
            if isinstance(f.invoice_date, dict):
                from app.schemas.common import DateRange
                f.invoice_date = DateRange(**f.invoice_date)

            if isinstance(f.amount, dict):
                from app.schemas.common import AmountRange
                f.amount = AmountRange(**f.amount)

        items = InvoiceService(db).list_invoices(tenant_id=tenant_id, filters=f)
        if pagination:
            items = items[pagination.offset : pagination.offset + pagination.limit]

        return [
            InvoiceType(
                id=i.id,
                tenant_id=i.tenant_id,
                vendor_id=i.vendor_id,
                invoice_number=i.invoice_number,
                amount=float(i.amount),
                currency=i.currency,
                invoice_date=i.invoice_date,
                description=i.description,
                status=GInvoiceStatus(i.status.value),
                created_at=i.created_at,
            )
            for i in items
        ]

    @strawberry.field
    def explain_reconciliation(
        self,
        info: Info,
        tenant_id: int,
        invoice_id: int,
        transaction_id: int,
    ) -> AIExplainType:
        db = info.context.db

        from sqlalchemy import and_, select
        from app.models.models import Invoice, BankTransaction
        from app.utils.reconcile import compute_score
        from app.services.ai import DisabledAIClient

        invoice = db.scalar(select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)))
        txn = db.scalar(select(BankTransaction).where(and_(BankTransaction.tenant_id == tenant_id, BankTransaction.id == transaction_id)))

        if not invoice or not txn:
            raise ValueError("Invoice or transaction not found")

        sb = compute_score(
            invoice_amount=float(invoice.amount),
            invoice_date=invoice.invoice_date,
            invoice_desc=invoice.description,
            txn_amount=float(txn.amount),
            txn_posted_at=txn.posted_at,
            txn_desc=txn.description,
        )

        svc = ExplanationService(db, ai_client=DisabledAIClient())
        out = svc._fallback(invoice=invoice, txn=txn, score=sb.total)
        return AIExplainType(**out.model_dump())


# ---------------------------
# Mutation
# ---------------------------

@strawberry.type
class Mutation:
    @strawberry.field
    def create_tenant(self, info: Info, input: TenantInput) -> TenantType:
        db = info.context.db
        t = TenantService(db).create_tenant(TenantCreate(name=input.name))
        return TenantType(id=t.id, name=t.name, created_at=t.created_at)

    @strawberry.field
    def create_invoice(self, info: Info, tenant_id: int, input: InvoiceInput) -> InvoiceType:
        db = info.context.db
        inv = InvoiceService(db).create_invoice(
            tenant_id=tenant_id,
            data=InvoiceCreate(
                vendor_id=input.vendor_id,
                invoice_number=input.invoice_number,
                amount=input.amount,
                currency=input.currency,
                invoice_date=input.invoice_date,
                description=input.description,
            ),
        )
        return InvoiceType(
            id=inv.id,
            tenant_id=inv.tenant_id,
            vendor_id=inv.vendor_id,
            invoice_number=inv.invoice_number,
            amount=float(inv.amount),
            currency=inv.currency,
            invoice_date=inv.invoice_date,
            description=inv.description,
            status=GInvoiceStatus(inv.status.value),
            created_at=inv.created_at,
        )

    @strawberry.field
    def delete_invoice(self, info: Info, tenant_id: int, invoice_id: int) -> bool:
        db = info.context.db
        return InvoiceService(db).delete_invoice(tenant_id=tenant_id, invoice_id=invoice_id)

    @strawberry.field
    def import_bank_transactions(
        self,
        info: Info,
        tenant_id: int,
        input: list[BankTransactionInput],
        idempotency_key: str,
    ) -> str:
        db = info.context.db
        try:
            BankTransactionService(db).import_transactions(
                tenant_id=tenant_id,
                transactions=[
                    BankTransactionIn(
                        external_id=t.external_id,
                        posted_at=t.posted_at,
                        amount=t.amount,
                        currency=t.currency,
                        description=t.description,
                    )
                    for t in input
                ],
                idempotency_key=idempotency_key,
            )
            return "ok"
        except IdempotencyConflict as e:
            raise ValueError(str(e))

    @strawberry.field
    def reconcile(self, info: Info, tenant_id: int, input: ReconcileRequestInput | None = None) -> list[MatchType]:
        db = info.context.db

        from app.schemas.match import ReconcileRequest as ReconcileRequestModel

        req = None
        if input is not None:
            req = ReconcileRequestModel(**vars(input))

        matches = ReconciliationService(db).reconcile(tenant_id=tenant_id, request=req)

        return [
            MatchType(
                id=m.id,
                tenant_id=m.tenant_id,
                invoice_id=m.invoice_id,
                bank_transaction_id=m.bank_transaction_id,
                score=m.score,
                status=GMatchStatus(m.status.value),
                created_at=m.created_at,
            )
            for m in matches
    ]

    @strawberry.field
    def confirm_match(self, info: Info, tenant_id: int, match_id: int) -> MatchType:
        db = info.context.db
        m = ReconciliationService(db).confirm_match(tenant_id=tenant_id, match_id=match_id)
        return MatchType(
            id=m.id,
            tenant_id=m.tenant_id,
            invoice_id=m.invoice_id,
            bank_transaction_id=m.bank_transaction_id,
            score=m.score,
            status=GMatchStatus(m.status.value),
            created_at=m.created_at,
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_context)
