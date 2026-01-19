from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Tenant
from app.schemas.tenant import TenantCreate


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_tenant(self, data: TenantCreate) -> Tenant:
        tenant = Tenant(name=data.name)
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def list_tenants(self) -> list[Tenant]:
        return list(self.db.scalars(select(Tenant).order_by(Tenant.id)))

    def get_tenant(self, tenant_id: int) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)
