from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import OrmBase


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TenantOut(OrmBase):
    id: int
    name: str
    created_at: datetime
