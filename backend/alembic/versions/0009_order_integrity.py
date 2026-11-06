"""Enforce order amount and bundle/network consistency.

Revision ID: 0009_order_integrity
Revises: 0008_catalogue_controls
"""
from alembic import op

revision = "0009_order_integrity"
down_revision = "0008_catalogue_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_orders_bundle_network",
        "orders",
        "bundles",
        ["bundle_id", "network_id"],
        ["id", "network_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "positive_order_amount",
        "orders",
        "amount > 0",
    )


def downgrade() -> None:
    op.drop_constraint("positive_order_amount", "orders", type_="check")
    op.drop_constraint("fk_orders_bundle_network", "orders", type_="foreignkey")
