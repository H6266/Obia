"""Add controlled catalogue metadata and append-only revision history.

Revision ID: 0008_catalogue_controls
Revises: 0007_database_rbac
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_catalogue_controls"
down_revision = "0007_database_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "networks",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "bundles",
        sa.Column("category", sa.String(length=32), nullable=False, server_default="data"),
    )
    op.add_column(
        "bundles",
        sa.Column("validity_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "bundles",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_bundles_id_network_id", "bundles", ["id", "network_id"]
    )
    op.create_check_constraint(
        "positive_bundle_size", "bundles", "size_gb > 0"
    )
    op.create_check_constraint(
        "positive_bundle_amount", "bundles", "amount > 0"
    )
    op.create_check_constraint(
        "positive_validity_days",
        "bundles",
        "validity_days IS NULL OR validity_days > 0",
    )
    op.create_table(
        "catalogue_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bundle_id", sa.String(length=64), nullable=False),
        sa.Column("changed_by_id", sa.Uuid(), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=False),
        sa.Column("new_value", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["bundle_id"], ["bundles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["staff_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catalogue_revisions_bundle_id", "catalogue_revisions", ["bundle_id"])
    op.create_index("ix_catalogue_revisions_created_at", "catalogue_revisions", ["created_at"])
    op.execute(
        """
        CREATE TRIGGER catalogue_revisions_append_only
        BEFORE UPDATE OR DELETE ON catalogue_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_admin_audit_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER catalogue_revisions_append_only ON catalogue_revisions")
    op.drop_index("ix_catalogue_revisions_created_at", table_name="catalogue_revisions")
    op.drop_index("ix_catalogue_revisions_bundle_id", table_name="catalogue_revisions")
    op.drop_table("catalogue_revisions")
    op.drop_constraint("positive_validity_days", "bundles", type_="check")
    op.drop_constraint("positive_bundle_amount", "bundles", type_="check")
    op.drop_constraint("positive_bundle_size", "bundles", type_="check")
    op.drop_constraint("uq_bundles_id_network_id", "bundles", type_="unique")
    op.drop_column("bundles", "updated_at")
    op.drop_column("bundles", "validity_days")
    op.drop_column("bundles", "category")
    op.drop_column("networks", "is_active")
