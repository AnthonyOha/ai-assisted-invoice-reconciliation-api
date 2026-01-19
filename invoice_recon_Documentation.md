### 📄 d:\workspace\code\invoice_recon\app\graphql\schema.py
*Saved at: 1/19/2026, 11:12:50 AM*

**[REMOVED]**
```
(from line ~336)
    def reconcile(self, info: Info, tenant_id: int, input: ReconcileRequest | None = None) -> list[MatchType]:

```
**[ADDED]**
```
336       def reconcile(self, info: Info, tenant_id: int, input: ReconcileRequestInput | None = None) -> list[MatchType]:
```
**[REMOVED]**
```
(from line ~338)
        matches = ReconciliationService(db).reconcile(tenant_id=tenant_id, request=input)

```
**[ADDED]**
```
338   
339           from app.schemas.match import ReconcileRequest as ReconcileRequestModel
340   
341           req = None
342           if input is not None:
343               req = ReconcileRequestModel(**vars(input))
344   
345           matches = ReconciliationService(db).reconcile(tenant_id=tenant_id, request=req)
346   
```
**[REMOVED]**
```
(from line ~358)
        ]

```
**[ADDED]**
```
358       ]
```

---

### 📄 d:\workspace\code\invoice_recon\app\graphql\schema.py
*Saved at: 1/19/2026, 11:10:28 AM*

**[REMOVED]**
```
(from line ~155)


```
**[ADDED]**
```
155   @strawberry.input
156   class ReconcileRequestInput:
157       invoice_id: int | None = None
158       bank_transaction_id: int | None = None
159       confirm: bool | None = None
```

---

### 📄 d:\workspace\code\invoice_recon\app\graphql\schema.py
*Saved at: 1/19/2026, 11:08:04 AM*

**[ADDED]**
```
3     from dataclasses import dataclass
```
**[REMOVED]**
```
(from line ~6)
from functools import wraps

```
**[ADDED]**
```
9     from strawberry.types import Info
```
**[REMOVED]**
```
(from line ~11)
from contextlib import contextmanager

```
**[REMOVED]**
```
(from line ~14)
from app.models.models import InvoiceStatus, MatchStatus

```
**[ADDED]**
```
14    from app.models.models import InvoiceStatus
```
**[REMOVED]**
```
(from line ~25)
@contextmanager
def session_scope() -> Session:
    db: Session = SessionLocal()

```
**[ADDED]**
```
25    
26    # ---------------------------
27    # GraphQL context (per request)
28    # ---------------------------
29    
30    @dataclass
31    class Context:
32        db: Session
33    
34    
35    def get_context():
36        db = SessionLocal()
```
**[REMOVED]**
```
(from line ~38)
        yield db

```
**[ADDED]**
```
38            yield Context(db=db)
```
**[ADDED]**
```
46    
47    # ---------------------------
48    # GraphQL Types
49    # ---------------------------
50    
```
**[REMOVED]**
```
(from line ~156)
def _with_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        db: Session = SessionLocal()
        try:
            result = fn(db=db, *args, **kwargs)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()  

```
**[ADDED]**
```
156   # ---------------------------
157   # Query
158   # ---------------------------
```
**[REMOVED]**
```
(from line ~160)
    return wrapper



```
**[REMOVED]**
```
(from line ~163)
    def tenants(self, db: Session) -> list[TenantType]:
        with session_scope() as db:
            items = TenantService(db).list_tenants()
            return [TenantType(id=t.id, name=t.name, created_at=t.created_at) for t in items]

```
**[ADDED]**
```
163       def tenants(self, info: Info) -> list[TenantType]:
164           db = info.context.db
165           items = TenantService(db).list_tenants()
166           return [TenantType(id=t.id, name=t.name, created_at=t.created_at) for t in items]
```
**[REMOVED]**
```
(from line ~171)
        db: Session,

```
**[ADDED]**
```
171           info: Info,
```
**[REMOVED]**
```
(from line ~176)
        with session_scope() as db:
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

```
**[ADDED]**
```
176           db = info.context.db
```
**[REMOVED]**
```
(from line ~178)
                    f.invoice_date = DateRange(**f.invoice_date)
                if isinstance(f.amount, dict):
                    from app.schemas.common import AmountRange

```
**[ADDED]**
```
178           f = None
179           if filters:
180               f = InvoiceFilters(
181                   status=InvoiceStatus(filters.status.value) if filters.status else None,
182                   vendor_id=filters.vendor_id,
183                   invoice_date=(
184                       None
185                       if not (filters.date_start or filters.date_end)
186                       else {"start": filters.date_start, "end": filters.date_end}
187                   ),
188                   amount=(
189                       None
190                       if (filters.amount_min is None and filters.amount_max is None)
191                       else {"min": filters.amount_min, "max": filters.amount_max}
192                   ),
193               )
```
**[REMOVED]**
```
(from line ~195)
                    f.amount = AmountRange(**f.amount)

```
**[ADDED]**
```
195               # convert dict to pydantic submodels
196               if isinstance(f.invoice_date, dict):
197                   from app.schemas.common import DateRange
198                   f.invoice_date = DateRange(**f.invoice_date)
```
**[REMOVED]**
```
(from line ~200)
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

```
**[ADDED]**
```
200               if isinstance(f.amount, dict):
201                   from app.schemas.common import AmountRange
202                   f.amount = AmountRange(**f.amount)
```
**[REMOVED]**
```
(from line ~204)
    @strawberry.field
    def explain_reconciliation(self, db: Session, tenant_id: int, invoice_id: int, transaction_id: int) -> AIExplainType:
        with session_scope() as db:
            from sqlalchemy import and_, select
            from app.models.models import Invoice, BankTransaction
            from app.utils.reconcile import compute_score
            from app.services.ai import DisabledAIClient

```
**[ADDED]**
```
204           items = InvoiceService(db).list_invoices(tenant_id=tenant_id, filters=f)
205           if pagination:
206               items = items[pagination.offset : pagination.offset + pagination.limit]
```
**[REMOVED]**
```
(from line ~208)
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

```
**[ADDED]**
```
208           return [
209               InvoiceType(
210                   id=i.id,
211                   tenant_id=i.tenant_id,
212                   vendor_id=i.vendor_id,
213                   invoice_number=i.invoice_number,
214                   amount=float(i.amount),
215                   currency=i.currency,
216                   invoice_date=i.invoice_date,
217                   description=i.description,
218                   status=GInvoiceStatus(i.status.value),
219                   created_at=i.created_at,
```
**[REMOVED]**
```
(from line ~221)
            svc = ExplanationService(db, ai_client=DisabledAIClient())
            out = svc._fallback(invoice=invoice, txn=txn, score=sb.total)
            return AIExplainType(**out.model_dump())

```
**[ADDED]**
```
221               for i in items
222           ]
```
**[ADDED]**
```
224       @strawberry.field
225       def explain_reconciliation(
226           self,
227           info: Info,
228           tenant_id: int,
229           invoice_id: int,
230           transaction_id: int,
231       ) -> AIExplainType:
232           db = info.context.db
```
**[ADDED]**
```
234           from sqlalchemy import and_, select
235           from app.models.models import Invoice, BankTransaction
236           from app.utils.reconcile import compute_score
237           from app.services.ai import DisabledAIClient
238   
239           invoice = db.scalar(select(Invoice).where(and_(Invoice.tenant_id == tenant_id, Invoice.id == invoice_id)))
240           txn = db.scalar(select(BankTransaction).where(and_(BankTransaction.tenant_id == tenant_id, BankTransaction.id == transaction_id)))
241   
242           if not invoice or not txn:
243               raise ValueError("Invoice or transaction not found")
244   
245           sb = compute_score(
246               invoice_amount=float(invoice.amount),
247               invoice_date=invoice.invoice_date,
248               invoice_desc=invoice.description,
249               txn_amount=float(txn.amount),
250               txn_posted_at=txn.posted_at,
251               txn_desc=txn.description,
252           )
253   
254           svc = ExplanationService(db, ai_client=DisabledAIClient())
255           out = svc._fallback(invoice=invoice, txn=txn, score=sb.total)
256           return AIExplainType(**out.model_dump())
257   
258   
259   # ---------------------------
260   # Mutation
261   # ---------------------------
262   
```
**[REMOVED]**
```
(from line ~266)
    def create_tenant(self, db: Session, input: TenantInput) -> TenantType:
        with session_scope() as db:
            t = TenantService(db).create_tenant(TenantCreate(name=input.name))
            return TenantType(id=t.id, name=t.name, created_at=t.created_at)

```
**[ADDED]**
```
266       def create_tenant(self, info: Info, input: TenantInput) -> TenantType:
267           db = info.context.db
268           t = TenantService(db).create_tenant(TenantCreate(name=input.name))
269           return TenantType(id=t.id, name=t.name, created_at=t.created_at)
```
**[REMOVED]**
```
(from line ~272)
    def create_invoice(self, db: Session, tenant_id: int, input: InvoiceInput) -> InvoiceType:
        with session_scope() as db:
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

```
**[ADDED]**
```
272       def create_invoice(self, info: Info, tenant_id: int, input: InvoiceInput) -> InvoiceType:
273           db = info.context.db
274           inv = InvoiceService(db).create_invoice(
275               tenant_id=tenant_id,
276               data=InvoiceCreate(
277                   vendor_id=input.vendor_id,
278                   invoice_number=input.invoice_number,
279                   amount=input.amount,
280                   currency=input.currency,
281                   invoice_date=input.invoice_date,
282                   description=input.description,
283               ),
284           )
285           return InvoiceType(
286               id=inv.id,
287               tenant_id=inv.tenant_id,
288               vendor_id=inv.vendor_id,
289               invoice_number=inv.invoice_number,
290               amount=float(inv.amount),
291               currency=inv.currency,
292               invoice_date=inv.invoice_date,
293               description=inv.description,
294               status=GInvoiceStatus(inv.status.value),
295               created_at=inv.created_at,
296           )
```
**[REMOVED]**
```
(from line ~299)
    def delete_invoice(self, db: Session, tenant_id: int, invoice_id: int) -> bool:
        with session_scope() as db:
            return InvoiceService(db).delete_invoice(tenant_id=tenant_id, invoice_id=invoice_id)

```
**[ADDED]**
```
299       def delete_invoice(self, info: Info, tenant_id: int, invoice_id: int) -> bool:
300           db = info.context.db
301           return InvoiceService(db).delete_invoice(tenant_id=tenant_id, invoice_id=invoice_id)
```
**[REMOVED]**
```
(from line ~304)
    def import_bank_transactions(self, db: Session, tenant_id: int, input: list[BankTransactionInput], idempotency_key: str) -> str:
        with session_scope() as db:
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

```
**[ADDED]**
```
304       def import_bank_transactions(
305           self,
306           info: Info,
307           tenant_id: int,
308           input: list[BankTransactionInput],
309           idempotency_key: str,
310       ) -> str:
311           db = info.context.db
312           try:
313               BankTransactionService(db).import_transactions(
314                   tenant_id=tenant_id,
315                   transactions=[
316                       BankTransactionIn(
317                           external_id=t.external_id,
318                           posted_at=t.posted_at,
319                           amount=t.amount,
320                           currency=t.currency,
321                           description=t.description,
322                       )
323                       for t in input
324                   ],
325                   idempotency_key=idempotency_key,
326               )
327               return "ok"
328           except IdempotencyConflict as e:
329               raise ValueError(str(e))
```
**[REMOVED]**
```
(from line ~332)
    def reconcile(self, db: Session, tenant_id: int, input: ReconcileRequest | None = None) -> list[MatchType]:
        with session_scope() as db:
            matches = ReconciliationService(db).reconcile(tenant_id=tenant_id, request=input)
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
    def confirm_match(self, db: Session, tenant_id: int, match_id: int) -> MatchType:
        with session_scope() as db:
            m = ReconciliationService(db).confirm_match(tenant_id=tenant_id, match_id=match_id)
            return MatchType(

```
**[ADDED]**
```
332       def reconcile(self, info: Info, tenant_id: int, input: ReconcileRequest | None = None) -> list[MatchType]:
333           db = info.context.db
334           matches = ReconciliationService(db).reconcile(tenant_id=tenant_id, request=input)
335           return [
336               MatchType(
```
**[ADDED]**
```
345               for m in matches
346           ]
```
**[ADDED]**
```
348       @strawberry.field
349       def confirm_match(self, info: Info, tenant_id: int, match_id: int) -> MatchType:
350           db = info.context.db
351           m = ReconciliationService(db).confirm_match(tenant_id=tenant_id, match_id=match_id)
352           return MatchType(
353               id=m.id,
354               tenant_id=m.tenant_id,
355               invoice_id=m.invoice_id,
356               bank_transaction_id=m.bank_transaction_id,
357               score=m.score,
358               status=GMatchStatus(m.status.value),
359               created_at=m.created_at,
360           )
```
**[ADDED]**
```
362   
```
**[REMOVED]**
```
(from line ~364)
graphql_router = GraphQLRouter(schema)

```
**[ADDED]**
```
364   graphql_router = GraphQLRouter(schema, context_getter=get_context)
```

---

### 📄 d:\workspace\code\invoice_recon\app\graphql\__pycache__\context.py
*Saved at: 1/19/2026, 10:58:43 AM*

**[ADDED]**
```
1     # app/graphql/context.py
2     from dataclasses import dataclass
3     from sqlalchemy.orm import Session
4     
5     @dataclass
6     class Context:
7         db: Session
```

---

### 📄 d:\workspace\code\invoice_recon\requirements.txt
*Saved at: 1/19/2026, 10:47:45 AM*

**[REMOVED]**
```
(from line ~1)
fastapi>=0.115
uvicorn[standard]>=0.30
strawberry-graphql[fastapi]>=0.243
SQLAlchemy>=2.0.35
pydantic>=2.10
pydantic-settings>=2.6

```
**[ADDED]**
```
1     fastapi>=0.110
2     uvicorn[standard]>=0.27
3     strawberry-graphql[fastapi]>=0.240
4     SQLAlchemy>=2.0
5     pydantic>=2.6
6     pydantic-settings>=2.2
```
**[REMOVED]**
```
(from line ~9)
pytest>=8.3
pytest-asyncio>=0.24
```
**[ADDED]**
```
9     pytest>=8.0
10    pytest-asyncio>=0.23
```

---

