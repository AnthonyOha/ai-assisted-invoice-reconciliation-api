from __future__ import annotations

from fastapi import FastAPI

from app.api.bank_transactions import router as bank_tx_router
from app.api.invoices import router as invoice_router
from app.api.reconcile import router as reconcile_router
from app.api.tenants import router as tenant_router
from app.db.init_db import init_db
from app.graphql.schema import graphql_router


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Multi-Tenant Invoice Reconciliation API")

    app.include_router(tenant_router)
    app.include_router(invoice_router)
    app.include_router(bank_tx_router)
    app.include_router(reconcile_router)

    app.include_router(graphql_router, prefix="/graphql")
    return app


app = create_app()
