"""Add customer credentials, secure sessions, and order recipient ownership.

Revision ID: 0002_customer_accounts
Revises: 0001_initial
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_customer_accounts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("full_name", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column(
        "customers",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "customers",
        sa.Column("account_status", sa.String(length=24), nullable=False, server_default="active"),
    )
    op.add_column(
        "customers",
        sa.Column("role", sa.String(length=24), nullable=False, server_default="customer"),
    )
    op.add_column(
        "customers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_phone", sa.String(length=16), nullable=True),
    )
    op.execute(
        "UPDATE orders SET recipient_phone = "
        "(SELECT customers.phone FROM customers WHERE customers.id = orders.customer_id)"
    )
    op.alter_column("orders", "recipient_phone", nullable=False)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_customer_id", "auth_sessions", ["customer_id"])
    op.create_table(
        "auth_rate_limit_buckets",
        sa.Column("bucket_key", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("bucket_key"),
    )


def downgrade() -> None:
    op.drop_table("auth_rate_limit_buckets")
    op.drop_index("ix_auth_sessions_customer_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_column("orders", "recipient_phone")
    op.drop_column("customers", "updated_at")
    op.drop_column("customers", "role")
    op.drop_column("customers", "account_status")
    op.drop_column("customers", "phone_verified")
    op.drop_column("customers", "password_hash")
    op.drop_column("customers", "full_name")
