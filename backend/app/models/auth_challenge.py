import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('email_verification', 'password_reset', 'customer_login', 'staff_login')",
            name="valid_auth_challenge_purpose",
        ),
        CheckConstraint("attempts >= 0", name="valid_auth_challenge_attempts"),
        CheckConstraint("max_attempts > 0", name="valid_auth_challenge_max_attempts"),
        Index("ix_auth_challenges_email_purpose_created", "email", "purpose", "created_at"),
        Index("ix_auth_challenges_user_id", "user_id"),
        Index("ix_auth_challenges_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
