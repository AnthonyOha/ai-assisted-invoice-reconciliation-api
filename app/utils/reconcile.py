from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


def _norm(s: str | None) -> str:
    return (s or "").lower().strip()


def token_jaccard(a: str | None, b: str | None) -> float:
    ta = set(_norm(a).split())
    tb = set(_norm(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def date_distance_days(inv_date: date | None, posted_at: datetime) -> int | None:
    if inv_date is None:
        return None
    return abs((posted_at.date() - inv_date).days)


@dataclass(frozen=True)
class ScoreBreakdown:
    amount_score: float
    date_score: float
    text_score: float
    total: float


def compute_score(
    invoice_amount: float,
    invoice_date: date | None,
    invoice_desc: str | None,
    txn_amount: float,
    txn_posted_at: datetime,
    txn_desc: str | None,
    date_window_days: int = 3,
    amount_tolerance_ratio: float = 0.01,
) -> ScoreBreakdown:
    """Deterministic scoring. Total ranges 0..1.

    Weighting (simple + explainable):
    - Amount: up to 0.60
    - Date proximity: up to 0.20
    - Text similarity: up to 0.20
    """

    # Amount
    amount_score = 0.0
    if abs(float(invoice_amount) - float(txn_amount)) < 0.005:
        amount_score = 0.60
    else:
        tol = max(float(invoice_amount) * amount_tolerance_ratio, 0.01)
        if abs(float(invoice_amount) - float(txn_amount)) <= tol:
            amount_score = 0.40

    # Date
    date_score = 0.0
    dd = date_distance_days(invoice_date, txn_posted_at)
    if dd is not None and dd <= date_window_days:
        # closer = higher
        date_score = 0.20 * (1.0 - (dd / max(date_window_days, 1)))

    # Text
    sim = token_jaccard(invoice_desc, txn_desc)
    text_score = 0.20 * min(sim, 1.0)

    total = min(amount_score + date_score + text_score, 1.0)
    return ScoreBreakdown(amount_score=amount_score, date_score=date_score, text_score=text_score, total=total)
