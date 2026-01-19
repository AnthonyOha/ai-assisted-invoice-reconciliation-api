from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.models import BankTransaction, Invoice
from app.schemas.match import AIExplainOut
from app.services.ai import AIClient, build_ai_client
from app.utils.reconcile import compute_score


class ExplanationService:
    def __init__(self, db: Session, ai_client: AIClient | None = None) -> None:
        self.db = db
        self.ai = ai_client or build_ai_client()

    def _fallback(self, *, invoice: Invoice, txn: BankTransaction, score: float) -> AIExplainOut:
        confidence = "low"
        if score >= 0.75:
            confidence = "high"
        elif score >= 0.45:
            confidence = "medium"

        parts: list[str] = []
        if abs(float(invoice.amount) - float(txn.amount)) < 0.005:
            parts.append("The amounts match exactly")
        else:
            parts.append("The amounts are close")
        if invoice.invoice_date is not None:
            days = abs((txn.posted_at.date() - invoice.invoice_date).days)
            parts.append(f"the dates are {days} days apart")
        if invoice.description and txn.description:
            parts.append("the descriptions share similar terms")
        text = ", ".join(parts) + f". Overall score {score:.2f} suggests {confidence} confidence."
        return AIExplainOut(explanation=text, confidence=confidence, used_ai=False)

    async def explain(self, *, tenant_id: int, invoice_id: int, txn_id: int) -> AIExplainOut:
        invoice = self.db.scalar(select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)))
        txn = self.db.scalar(select(BankTransaction).where(and_(BankTransaction.tenant_id == tenant_id, BankTransaction.id == txn_id)))
        if not invoice or not txn:
            raise LookupError("Invoice or transaction not found")

        sb = compute_score(
            invoice_amount=float(invoice.amount),
            invoice_date=invoice.invoice_date,
            invoice_desc=invoice.description,
            txn_amount=float(txn.amount),
            txn_posted_at=txn.posted_at,
            txn_desc=txn.description,
        )
        score = sb.total

        prompt = (
            "Explain why this invoice and bank transaction are likely a match. "
            "Use only the provided facts.\n\n"
            f"Invoice: amount={float(invoice.amount):.2f} {invoice.currency}, date={invoice.invoice_date}, description={invoice.description}\n"
            f"Transaction: amount={float(txn.amount):.2f} {txn.currency}, posted_at={txn.posted_at.date()}, description={txn.description}\n"
            f"Heuristic score={score:.2f} (amount={sb.amount_score:.2f}, date={sb.date_score:.2f}, text={sb.text_score:.2f})\n"
            "Return 2-6 sentences and include a confidence label."
        )

        try:
            res = await self.ai.explain_match(prompt=prompt)
            return AIExplainOut(explanation=res.explanation, confidence=res.confidence, used_ai=True)
        except Exception:
            return self._fallback(invoice=invoice, txn=txn, score=score)
