from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, Field


class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


class DateRange(BaseModel):
    start: date | None = None
    end: date | None = None


class DateTimeRange(BaseModel):
    start: datetime | None = None
    end: datetime | None = None


class AmountRange(BaseModel):
    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)
