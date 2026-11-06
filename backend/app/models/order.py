import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_PROCESSING = "payment_processing"
    PAID = "paid"
    FULFILLMENT_PENDING = "fulfillment_pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bundle_id", "network_id"],
            ["bundles.id", "bundles.network_id"],
            name="fk_orders_bundle_network",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount > 0", name="positive_order_amount"),
        Index(
            "uq_orders_idempotency_key_hash",
            "idempotency_key_hash",
            unique=True,
        ),
    )

    reference: Mapped[str] = mapped_column(String(48), primary_key=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    account_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    recipient_phone: Mapped[str] = mapped_column(String(16), nullable=False)
    bundle_id: Mapped[str] = mapped_column(
        ForeignKey("bundles.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    network_id: Mapped[str] = mapped_column(
        ForeignKey("networks.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    idempotency_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            values_callable=lambda statuses: [status.value for status in statuses],
            native_enum=False,
            length=32,
        ),
        default=OrderStatus.PENDING_PAYMENT,
        nullable=False,
    )
    payment_status: Mapped[str] = mapped_column(
        String(24), default="unverified", nullable=False
    )
    fulfillment_status: Mapped[str] = mapped_column(
        String(24), default="not_started", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="orders", foreign_keys=[customer_id]
    )
    bundle: Mapped["Bundle"] = relationship(foreign_keys=[bundle_id])
    network: Mapped["Network"] = relationship()
