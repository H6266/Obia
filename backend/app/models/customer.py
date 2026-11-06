import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("user_id", name="uq_customers_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    guest_phone: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user: Mapped["User | None"] = relationship(back_populates="customer_profile")
    orders: Mapped[list["Order"]] = relationship(
        back_populates="customer", foreign_keys="Order.customer_id"
    )
    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    @property
    def phone(self) -> str:
        return self.user.phone if self.user and self.user.phone else self.guest_phone or ""

    @phone.setter
    def phone(self, value: str) -> None:
        self.guest_phone = value

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""

    @property
    def phone_verified(self) -> bool:
        return self.user.phone_verified if self.user else False

    @property
    def account_status(self) -> str:
        return self.user.account_status if self.user else "guest"

    @property
    def role(self) -> str:
        return "customer"

    @property
    def identity_id(self) -> uuid.UUID | None:
        return self.user_id
