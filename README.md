# Multi-Tenant Invoice Reconciliation API

Small, senior-signal exercise implementing a multi-tenant invoice reconciliation system with:

- Python 3.13 (code is 3.11+ compatible)
- FastAPI (REST)
- Strawberry GraphQL
- SQLAlchemy 2.0
- pytest

## Quickstart

1. Create a venv and install deps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the API

```bash
uvicorn run:app --reload
```

- REST docs: `http://localhost:8000/docs`
- GraphQL: `http://localhost:8000/graphql`

3. Run tests

```bash
pytest -q
```

## Key design decisions

### Architecture

- **API layer** (`app/api/*`, `app/graphql/*`)  
  HTTP/GraphQL transport, request/response models, error mapping.
- **Service layer** (`app/services/*`)  
  Business logic and transaction boundaries (runs on a SQLAlchemy `Session`).
- **Persistence layer** (`app/models/*`)  
  SQLAlchemy ORM models.
- **Deterministic reconciliation** (`app/utils/reconcile.py`)  
  Pure functions: easy to test and to explain.
- **AI integration** (`app/services/ai.py`, `app/services/explain.py`)  
  Thin, mockable adapter with graceful fallback.

### Multi-tenant isolation

- Every tenant-owned table has a `tenant_id` column.
- Every service method takes `tenant_id` and **filters all reads/writes** by it.
- REST endpoints are tenant-scoped by path: `/tenants/{tenant_id}/...`.

This keeps the isolation rule explicit and reviewable.

## Reconciliation behavior

`POST /tenants/{tenant_id}/reconcile`:

- Considers **open invoices** and **all bank transactions** for the tenant.
- Computes a deterministic score for each invoice/transaction pair.
- Keeps the **top N candidates per invoice** (`max_candidates_per_invoice`, default 3).
- Persists candidates into `matches` with status `proposed`.
- On each run, we delete non-confirmed matches for the tenant so reconciliation is deterministic per run.

### Scoring (explainable heuristic)

Total score is clamped to `0..1`.

- **Amount** (up to 0.60)
  - exact amount match => +0.60
  - within ~1% tolerance => +0.40
- **Date proximity** (up to 0.20)
  - within `date_window_days` (default 3) => closer date yields higher score
- **Text similarity** (up to 0.20)
  - simple token Jaccard overlap between invoice description and bank memo

File: `app/utils/reconcile.py`.

## Match confirmation

`POST /tenants/{tenant_id}/matches/{match_id}/confirm`:

- Requires the match to be `proposed`.
- Enforces one confirmed match per invoice OR per transaction (basic safety).
- Sets the invoice status to `matched`.
- Removes other proposed candidates that involve the same invoice or same transaction.

## Idempotent import

`POST /tenants/{tenant_id}/bank-transactions/import` uses `Idempotency-Key`.

- We hash the request payload (stable JSON) and store it in `idempotency_records` per tenant.
- If the same key is reused:
  - same payload hash => return the stored response
  - different payload hash => return HTTP 409

Additionally, when `external_id` is provided, inserts are de-duplicated per `(tenant_id, external_id)`.

## AI explanations

Endpoint:

- REST: `GET /tenants/{tenant_id}/reconcile/explain?invoice_id=...&transaction_id=...`
- GraphQL: `explainReconciliation(tenantId, invoiceId, transactionId)` (uses deterministic fallback)

Implementation:

- `ExplanationService` recomputes the heuristic score and builds an AI prompt using only tenant-authorized fields.
- AI is optional:
  - `APP_AI_PROVIDER=mock` returns a deterministic "AI" response
  - `APP_AI_PROVIDER=openai` uses the OpenAI Chat Completions HTTP API (`APP_OPENAI_API_KEY` required)
  - anything else => disabled
- If AI errors/timeouts/missing key, we return a deterministic explanation (fallback).

### Environment variables

All config uses `APP_` prefix:

- `APP_DATABASE_URL` (default: sqlite file `./invoice_recon.db`)
- `APP_AI_PROVIDER` = `disabled|mock|openai`
- `APP_OPENAI_API_KEY` (only for `openai`)
- `APP_OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)
- `APP_OPENAI_MODEL` (default: `gpt-4.1-mini`)
- `APP_AI_TIMEOUT_SECONDS` (default: `4.0`)

## Notes / tradeoffs

- SQLite is used for local simplicity.
- GraphQL resolvers open a short-lived DB session per request, mirroring the REST dependency pattern.
- Reconciliation is intentionally simple and explainable; AI is only used for narrative explanation.
