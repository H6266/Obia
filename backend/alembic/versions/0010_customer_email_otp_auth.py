"""Add customer email verification fields and auth challenges.

Revision ID: 0010_customer_email_otp_auth
Revises: 0009_order_integrity
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_customer_email_otp_auth"
down_revision = "0009_order_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE users
        SET email_verified = false
        WHERE email_verified IS NULL
        """
    )

    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "purpose IN ('email_verification', 'password_reset')",
            name="valid_auth_challenge_purpose",
        ),
        sa.CheckConstraint("attempts >= 0", name="valid_auth_challenge_attempts"),
        sa.CheckConstraint("max_attempts > 0", name="valid_auth_challenge_max_attempts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_challenges_email", "auth_challenges", ["email"])
    op.create_index("ix_auth_challenges_user_id", "auth_challenges", ["user_id"])
    op.create_index("ix_auth_challenges_expires_at", "auth_challenges", ["expires_at"])
    op.create_index(
        "ix_auth_challenges_email_purpose_created",
        "auth_challenges",
        ["email", "purpose", "created_at"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_users_email_lower
        ON users (lower(email))
        WHERE email IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
    op.drop_index("ix_auth_challenges_email_purpose_created", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_expires_at", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_user_id", table_name="auth_challenges")
    op.drop_index("ix_auth_challenges_email", table_name="auth_challenges")
    op.drop_table("auth_challenges")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
