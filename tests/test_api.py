from __future__ import annotations

from datetime import datetime, timedelta, date

import pytest

from app.config import settings


def create_tenant(client, name="Acme"):
    r = client.post("/tenants", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_list_delete_invoice(client):
    tenant_id = create_tenant(client, "T1")

    r = client.post(f"/tenants/{tenant_id}/invoices", json={"amount": 100.0, "currency": "USD", "invoice_date": "2026-01-10", "description": "Widget"})
    assert r.status_code == 201
    inv_id = r.json()["id"]

    # list with a filter
    r = client.get(f"/tenants/{tenant_id}/invoices", params={"status": "open"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["id"] == inv_id

    # delete
    r = client.delete(f"/tenants/{tenant_id}/invoices/{inv_id}")
    assert r.status_code == 204

    r = client.get(f"/tenants/{tenant_id}/invoices")
    assert r.status_code == 200
    assert r.json() == []


def test_import_bank_transactions_idempotency(client):
    tenant_id = create_tenant(client, "T2")
    now = datetime(2026, 1, 12, 12, 0, 0)

    payload = [
        {"external_id": "tx1", "posted_at": now.isoformat(), "amount": 100.0, "currency": "USD", "description": "Payment widget"},
        {"external_id": "tx2", "posted_at": (now + timedelta(days=1)).isoformat(), "amount": 50.0, "currency": "USD", "description": "Other"},
    ]

    headers = {"Idempotency-Key": "k1"}
    r1 = client.post(f"/tenants/{tenant_id}/bank-transactions/import", json=payload, headers=headers)
    assert r1.status_code == 200
    out1 = r1.json()
    assert out1["inserted"] == 2

    # same key + same payload => same response
    r2 = client.post(f"/tenants/{tenant_id}/bank-transactions/import", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json() == out1

    # same key + different payload => conflict
    payload2 = payload + [{"external_id": "tx3", "posted_at": now.isoformat(), "amount": 10.0, "currency": "USD"}]
    r3 = client.post(f"/tenants/{tenant_id}/bank-transactions/import", json=payload2, headers=headers)
    assert r3.status_code == 409


def test_reconcile_ranking_confirm_and_ai_explain(client):
    tenant_id = create_tenant(client, "T3")

    # invoices
    inv1 = client.post(
        f"/tenants/{tenant_id}/invoices",
        json={"amount": 100.0, "currency": "USD", "invoice_date": "2026-01-10", "description": "acme widget"},
    ).json()["id"]

    # transactions
    t0 = datetime(2026, 1, 10, 10, 0, 0)
    tx_payload = [
        {"external_id": "a", "posted_at": t0.isoformat(), "amount": 100.0, "currency": "USD", "description": "acme widget payment"},
        {"external_id": "b", "posted_at": (t0 + timedelta(days=2)).isoformat(), "amount": 100.0, "currency": "USD", "description": "unrelated"},
        {"external_id": "c", "posted_at": t0.isoformat(), "amount": 99.0, "currency": "USD", "description": "acme widget"},
    ]
    client.post(f"/tenants/{tenant_id}/bank-transactions/import", json=tx_payload, headers={"Idempotency-Key": "k2"})

    # reconcile
    r = client.post(f"/tenants/{tenant_id}/reconcile", json={"max_candidates_per_invoice": 3, "date_window_days": 3})
    assert r.status_code == 200
    candidates = r.json()
    assert len(candidates) >= 2

    # find candidates for invoice
    inv_candidates = [c for c in candidates if c["invoice_id"] == inv1]
    assert inv_candidates
    inv_candidates.sort(key=lambda c: c["score"], reverse=True)
    best = inv_candidates[0]
    assert best["score"] >= inv_candidates[-1]["score"]

    # confirm best
    match_id = best["id"]
    r = client.post(f"/tenants/{tenant_id}/matches/{match_id}/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    # invoice status should be matched
    r = client.get(f"/tenants/{tenant_id}/invoices", params={"status": "matched"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == inv1

    # AI explain with mocked AI
    settings.ai_provider = "mock"
    # need transaction id; pick from confirmed match
    txn_id = best["bank_transaction_id"]
    r = client.get(f"/tenants/{tenant_id}/reconcile/explain", params={"invoice_id": inv1, "transaction_id": txn_id})
    assert r.status_code == 200
    assert r.json()["used_ai"] is True
    assert "amount" in r.json()["explanation"].lower()

    # fallback path
    settings.ai_provider = "disabled"
    r = client.get(f"/tenants/{tenant_id}/reconcile/explain", params={"invoice_id": inv1, "transaction_id": txn_id})
    assert r.status_code == 200
    assert r.json()["used_ai"] is False
