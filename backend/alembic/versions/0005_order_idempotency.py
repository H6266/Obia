"""Make purchase-request creation idempotent.

Revision ID: 0005_order_idempotency
Revises: 0004_admin_operations
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_order_idempotency"
down_revision = "0004_admin_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("request_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_orders_idempotency_key_hash",
        "orders",
        ["idempotency_key_hash"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_orders_idempotency_fields_paired",
        "orders",
        "(idempotency_key_hash IS NULL) = (request_fingerprint IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_orders_idempotency_fields_paired", "orders", type_="check"
    )
    op.drop_index("uq_orders_idempotency_key_hash", table_name="orders")
    op.drop_column("orders", "request_fingerprint")
    op.drop_column("orders", "idempotency_key_hash")
