from __future__ import annotations

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.models.models import BankTransaction, Invoice, InvoiceStatus, Match, MatchStatus
from app.schemas.match import ReconcileRequest
from app.utils.reconcile import compute_score


class ReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def reconcile(self, *, tenant_id: int, request: ReconcileRequest | None = None) -> list[Match]:
        req = request or ReconcileRequest()

        # Keep confirmed; refresh proposed/rejected to keep behavior deterministic per run.
        self.db.execute(delete(Match).where(and_(Match.tenant_id == tenant_id, Match.status != MatchStatus.confirmed)))

        invoices = list(self.db.scalars(select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.status == InvoiceStatus.open))))
        txns = list(self.db.scalars(select(BankTransaction).where(BankTransaction.tenant_id == tenant_id)))

        created: list[Match] = []
        for inv in invoices:
            scored: list[tuple[float, int]] = []
            for tx in txns:
                sb = compute_score(
                    invoice_amount=float(inv.amount),
                    invoice_date=inv.invoice_date,
                    invoice_desc=inv.description,
                    txn_amount=float(tx.amount),
                    txn_posted_at=tx.posted_at,
                    txn_desc=tx.description,
                    date_window_days=req.date_window_days,
                )
                if sb.total <= 0.0:
                    continue
                scored.append((sb.total, tx.id))

            scored.sort(key=lambda x: x[0], reverse=True)
            for score, tx_id in scored[: req.max_candidates_per_invoice]:
                m = Match(
                    tenant_id=tenant_id,
                    invoice_id=inv.id,
                    bank_transaction_id=tx_id,
                    score=score,
                    status=MatchStatus.proposed,
                )
                self.db.add(m)
                created.append(m)

        self.db.flush()
        # Return only proposed created on this run (confirmed preserved but not returned unless they were created now)
        return created

    def list_matches(self, *, tenant_id: int, status: MatchStatus | None = None) -> list[Match]:
        stmt = select(Match).where(Match.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Match.status == status)
        stmt = stmt.order_by(Match.id)
        return list(self.db.scalars(stmt))

    def confirm_match(self, *, tenant_id: int, match_id: int) -> Match:
        match = self.db.scalar(select(Match).where(and_(Match.tenant_id == tenant_id, Match.id == match_id)))
        if not match:
            raise LookupError("Match not found")
        if match.status != MatchStatus.proposed:
            raise ValueError("Only proposed matches can be confirmed")

        # Ensure no other confirmed match exists for this invoice or this transaction.
        existing_conflict = self.db.scalar(
            select(Match).where(
                and_(
                    Match.tenant_id == tenant_id,
                    Match.status == MatchStatus.confirmed,
                    (Match.invoice_id == match.invoice_id) | (Match.bank_transaction_id == match.bank_transaction_id),
                )
            )
        )
        if existing_conflict:
            raise ValueError("Invoice or transaction already has a confirmed match")

        match.status = MatchStatus.confirmed
        invoice = self.db.scalar(select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == match.invoice_id)))
        if invoice:
            invoice.status = InvoiceStatus.matched

        # Reject other proposed matches for the same invoice or txn to reduce ambiguity.
        self.db.execute(
            delete(Match).where(
                and_(
                    Match.tenant_id == tenant_id,
                    Match.status == MatchStatus.proposed,
                    Match.id != match.id,
                    ((Match.invoice_id == match.invoice_id) | (Match.bank_transaction_id == match.bank_transaction_id)),
                )
            )
        )
        self.db.flush()
        return match
