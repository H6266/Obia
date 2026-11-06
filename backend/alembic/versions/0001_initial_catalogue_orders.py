"""Create catalogue, customers, and orders with demo-only offers.

Revision ID: 0001_initial
Revises:
"""
from datetime import datetime, timezone
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

networks = sa.table(
    "networks",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("short_name", sa.String),
)
bundles = sa.table(
    "bundles",
    sa.column("id", sa.String),
    sa.column("network_id", sa.String),
    sa.column("name", sa.String),
    sa.column("size_gb", sa.Numeric),
    sa.column("amount", sa.Numeric),
    sa.column("currency", sa.String),
    sa.column("is_sample", sa.Boolean),
    sa.column("is_available", sa.Boolean),
)


def upgrade() -> None:
    op.create_table(
        "networks",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("short_name", sa.String(length=32), nullable=False),
    )
    op.create_table(
        "bundles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("network_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("size_gb", sa.Numeric(8, 2), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_sample", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["network_id"], ["networks.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_bundles_network_id", "bundles", ["network_id"])
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_table(
        "orders",
        sa.Column("reference", sa.String(length=48), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("bundle_id", sa.String(length=64), nullable=False),
        sa.Column("network_id", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["network_id"], ["networks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("reference"),
    )
    op.create_index("ix_orders_bundle_id", "orders", ["bundle_id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_network_id", "orders", ["network_id"])

    op.bulk_insert(
        networks,
        [
            {"id": "mtn", "name": "MTN", "short_name": "MTN"},
            {"id": "telecel", "name": "Telecel", "short_name": "Telecel"},
            {"id": "at", "name": "AirtelTigo", "short_name": "AT"},
        ],
    )
    sample_amount = Decimal("1.00")
    op.bulk_insert(
        bundles,
        [
            {
                "id": f"{network_id}-sample-1gb",
                "network_id": network_id,
                "name": "1 GB sample bundle",
                "size_gb": Decimal("1.00"),
                "amount": sample_amount,
                "currency": "GHS",
                "is_sample": True,
                "is_available": True,
            }
            for network_id in ("mtn", "telecel", "at")
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_network_id", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_index("ix_orders_bundle_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_bundles_network_id", table_name="bundles")
    op.drop_table("bundles")
    op.drop_table("networks")
