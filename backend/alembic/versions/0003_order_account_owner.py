"""Track the account that owns authenticated orders.

Revision ID: 0003_order_account_owner
Revises: 0002_customer_accounts
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_order_account_owner"
down_revision = "0002_customer_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("account_owner_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_account_owner_id_customers",
        "orders",
        "customers",
        ["account_owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_account_owner_id", "orders", ["account_owner_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_account_owner_id", table_name="orders")
    op.drop_constraint(
        "fk_orders_account_owner_id_customers",
        "orders",
        type_="foreignkey",
    )
    op.drop_column("orders", "account_owner_id")
