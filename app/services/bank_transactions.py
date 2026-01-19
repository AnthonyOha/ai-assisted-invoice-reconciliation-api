from __future__ import annotations

import json
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.models import BankTransaction, IdempotencyRecord
from app.schemas.bank_transaction import BankTransactionIn, BankTransactionFilters
from app.utils.hashing import sha256_hex, stable_json_dumps


class IdempotencyConflict(Exception):
    pass


class BankTransactionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_transactions(self, *, tenant_id: int, filters: BankTransactionFilters | None = None) -> list[BankTransaction]:
        stmt = select(BankTransaction).where(BankTransaction.tenant_id == tenant_id)
        if filters:
            if filters.posted_at:
                if filters.posted_at.start:
                    stmt = stmt.where(BankTransaction.posted_at >= filters.posted_at.start)
                if filters.posted_at.end:
                    stmt = stmt.where(BankTransaction.posted_at <= filters.posted_at.end)
            if filters.amount:
                if filters.amount.min is not None:
                    stmt = stmt.where(BankTransaction.amount >= filters.amount.min)
                if filters.amount.max is not None:
                    stmt = stmt.where(BankTransaction.amount <= filters.amount.max)
            if filters.description_contains:
                like = f"%{filters.description_contains.lower()}%"
                stmt = stmt.where(BankTransaction.description.ilike(like))
        stmt = stmt.order_by(BankTransaction.id)
        return list(self.db.scalars(stmt))

    def import_transactions(
        self,
        *,
        tenant_id: int,
        transactions: list[BankTransactionIn],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")

        payload_obj = [t.model_dump(mode="json") for t in transactions]
        payload_str = stable_json_dumps(payload_obj)
        req_hash = sha256_hex(payload_str)

        existing = self.db.scalar(
            select(IdempotencyRecord).where(and_(IdempotencyRecord.tenant_id == tenant_id, IdempotencyRecord.key == idempotency_key))
        )
        if existing:
            if existing.request_hash != req_hash:
                raise IdempotencyConflict("Idempotency key reused with different payload")
            return json.loads(existing.response_json)

        # Insert transactions; ignore duplicates by (tenant_id, external_id) if external_id is present.
        created_ids: list[int] = []
        inserted = 0
        skipped = 0

        for t in transactions:
            values = {
                "tenant_id": tenant_id,
                "external_id": t.external_id,
                "posted_at": t.posted_at,
                "amount": t.amount,
                "currency": t.currency,
                "description": t.description,
            }

            if t.external_id:
                stmt = sqlite_insert(BankTransaction).values(**values).on_conflict_do_nothing(index_elements=["tenant_id", "external_id"])
            else:
                # No natural key; always insert.
                stmt = sqlite_insert(BankTransaction).values(**values)

            res = self.db.execute(stmt)
            # sqlite: rowcount == 1 means inserted, 0 means conflict/no-op
            if res.rowcount == 1:
                inserted += 1
                # Fetch id via lastrowid (dialect specific)
                last_id = res.lastrowid
                if last_id is not None:
                    created_ids.append(int(last_id))
            else:
                skipped += 1

        response = {"inserted": inserted, "skipped": skipped, "created_ids": created_ids}
        record = IdempotencyRecord(tenant_id=tenant_id, key=idempotency_key, request_hash=req_hash, response_json=stable_json_dumps(response))
        self.db.add(record)
        self.db.flush()
        return response
