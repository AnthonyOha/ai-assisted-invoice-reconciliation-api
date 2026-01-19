from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.tenant import TenantCreate, TenantOut
from app.services.tenants import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    svc = TenantService(db)
    try:
        tenant = svc.create_tenant(payload)
        return tenant
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db)):
    return TenantService(db).list_tenants()
