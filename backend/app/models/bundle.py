from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Bundle(Base):
    __tablename__ = "bundles"

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

    network: Mapped["Network"] = relationship(back_populates="bundles")
