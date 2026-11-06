"""Add staff access control and stage-one admin operations.

Revision ID: 0004_admin_operations
Revises: 0003_order_account_owner
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_admin_operations"
down_revision = "0003_order_account_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.add_column(
        "orders",
        sa.Column("payment_status", sa.String(length=24), nullable=False, server_default="unverified"),
    )
    op.add_column(
        "orders",
        sa.Column("fulfillment_status", sa.String(length=24), nullable=False, server_default="not_started"),
    )
    op.add_column(
        "orders",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "staff_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending_mfa"),
        sa.Column("mfa_secret_encrypted", sa.String(length=512), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enrollment_token_hash", sa.String(length=64), nullable=True),
        sa.Column("enrollment_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_totp_step", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_staff_users_email", "staff_users", ["email"])
    op.create_index(
        "uq_staff_single_owner",
        "staff_users",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'owner'"),
    )

    op.create_table(
        "staff_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("staff_user_id", sa.Uuid(), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["staff_user_id"], ["staff_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_sessions_staff_user_id", "staff_sessions", ["staff_user_id"])
    op.create_index("ix_staff_sessions_expires_at", "staff_sessions", ["expires_at"])

    op.create_table(
        "staff_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["invited_by_id"], ["staff_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_staff_invitations_email", "staff_invitations", ["email"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=254), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_id"], ["staff_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("actor_id", "action", "resource_type", "resource_id", "request_id", "created_at"):
        op.create_index(f"ix_admin_audit_logs_{column}", "admin_audit_logs", [column])

    op.create_table(
        "order_support_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_reference", sa.String(length=48), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_reference"], ["orders.reference"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["staff_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_support_notes_order_reference", "order_support_notes", ["order_reference"])

    op.create_table(
        "order_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_reference", sa.String(length=48), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_label", sa.String(length=254), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_reference"], ["orders.reference"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_events_order_reference", "order_events", ["order_reference"])
    op.create_index("ix_order_events_created_at", "order_events", ["created_at"])

    op.create_table(
        "order_escalations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_reference", sa.String(length=48), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["order_reference"], ["orders.reference"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["staff_users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_escalations_order_reference", "order_escalations", ["order_reference"])

    op.execute(
        """
        CREATE FUNCTION reject_admin_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Administrative audit records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER admin_audit_logs_append_only
        BEFORE UPDATE OR DELETE ON admin_audit_logs
        FOR EACH ROW EXECUTE FUNCTION reject_admin_audit_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_order_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Order events are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER order_events_append_only
        BEFORE UPDATE OR DELETE ON order_events
        FOR EACH ROW EXECUTE FUNCTION reject_order_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER order_events_append_only ON order_events")
    op.execute("DROP FUNCTION reject_order_event_mutation()")
    op.execute("DROP TRIGGER admin_audit_logs_append_only ON admin_audit_logs")
    op.execute("DROP FUNCTION reject_admin_audit_mutation()")
    op.drop_index("ix_order_escalations_order_reference", table_name="order_escalations")
    op.drop_table("order_escalations")
    op.drop_index("ix_order_events_created_at", table_name="order_events")
    op.drop_index("ix_order_events_order_reference", table_name="order_events")
    op.drop_table("order_events")
    op.drop_index("ix_order_support_notes_order_reference", table_name="order_support_notes")
    op.drop_table("order_support_notes")
    for column in ("actor_id", "action", "resource_type", "resource_id", "request_id", "created_at"):
        op.drop_index(f"ix_admin_audit_logs_{column}", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("ix_staff_invitations_email", table_name="staff_invitations")
    op.drop_table("staff_invitations")
    op.drop_index("ix_staff_sessions_expires_at", table_name="staff_sessions")
    op.drop_index("ix_staff_sessions_staff_user_id", table_name="staff_sessions")
    op.drop_table("staff_sessions")
    op.drop_index("ix_staff_users_email", table_name="staff_users")
    op.drop_index("uq_staff_single_owner", table_name="staff_users")
    op.drop_table("staff_users")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_column("orders", "updated_at")
    op.drop_column("orders", "fulfillment_status")
    op.drop_column("orders", "payment_status")
