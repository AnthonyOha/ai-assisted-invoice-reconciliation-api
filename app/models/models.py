from __future__ import annotations

import enum
from datetime import datetime, date

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceStatus(str, enum.Enum):
    open = "open"
    matched = "matched"
    paid = "paid"


class MatchStatus(str, enum.Enum):
    proposed = "proposed"
    confirmed = "confirmed"
    rejected = "rejected"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    vendors: Mapped[list[Vendor]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]
    invoices: Mapped[list[Invoice]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]
    bank_transactions: Mapped[list[BankTransaction]] = relationship(back_populates="tenant", cascade="all, delete-orphan")  # type: ignore[name-defined]


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="vendors")

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_vendor_tenant_name"),)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)

    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.open, server_default=InvoiceStatus.open.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="invoices")

    __table_args__ = (
        Index("ix_invoices_tenant_status", "tenant_id", "status"),
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="bank_transactions")

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_id", name="uq_tx_tenant_external_id"),
        Index("ix_tx_tenant_posted", "tenant_id", "posted_at"),
    )


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_transaction_id: Mapped[int] = mapped_column(ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False, index=True)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus), nullable=False, default=MatchStatus.proposed, server_default=MatchStatus.proposed.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_match_tenant_status", "tenant_id", "status"),
        UniqueConstraint("tenant_id", "invoice_id", "bank_transaction_id", name="uq_match_triplet"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_idemp_tenant_key"),
    )
