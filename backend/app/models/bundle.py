from decimal import Decimal

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Bundle(Base):
    __tablename__ = "bundles"
    __table_args__ = (
        UniqueConstraint("id", "network_id", name="uq_bundles_id_network_id"),
        CheckConstraint("size_gb > 0", name="positive_bundle_size"),
        CheckConstraint("amount > 0", name="positive_bundle_amount"),
        CheckConstraint("validity_days IS NULL OR validity_days > 0", name="positive_validity_days"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    network_id: Mapped[str] = mapped_column(
        ForeignKey("networks.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    size_gb: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="GHS", nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="data", nullable=False)
    validity_days: Mapped[int | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    network: Mapped["Network"] = relationship(back_populates="bundles")
