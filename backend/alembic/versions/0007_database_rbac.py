"""Move staff role permissions into relational tables.

Revision ID: 0007_database_rbac
Revises: 0006_shared_user_identity
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_database_rbac"
down_revision = "0006_shared_user_identity"
branch_labels = None
depends_on = None

ALL = (
    "dashboard.read", "orders.read", "orders.manage", "orders.notes",
    "customers.read", "customers.read_sensitive", "customers.manage",
    "staff.manage", "audit.read", "inventory.read", "inventory.manage",
    "finance.read", "finance.reconcile", "refunds.approve", "agents.manage",
    "businesses.manage", "catalogue.read", "catalogue.manage",
)
GRANTS = {
    "owner": ALL,
    "super_admin": ALL,
    "operations_manager": (
        "dashboard.read", "orders.read", "orders.manage", "orders.notes",
        "customers.read", "customers.read_sensitive", "catalogue.read",
    ),
    "finance_manager": (
        "dashboard.read", "orders.read", "finance.read", "finance.reconcile",
        "refunds.approve",
    ),
    "customer_support": (
        "dashboard.read", "orders.read", "orders.notes", "customers.read",
    ),
    "inventory_officer": ("dashboard.read", "inventory.read", "inventory.manage"),
    "agent_manager": ("dashboard.read", "agents.manage"),
    "auditor": (
        "dashboard.read", "orders.read", "customers.read", "audit.read",
        "inventory.read", "finance.read",
    ),
}


def _label(value: str) -> str:
    return value.replace(".", " ").replace("_", " ").title()


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_name", sa.String(length=32), nullable=False),
        sa.Column("permission_code", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["role_name"], ["roles.name"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_code"], ["permissions.code"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_name", "permission_code"),
    )

    roles = sa.table(
        "roles",
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
    )
    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("description", sa.String),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_name", sa.String),
        sa.column("permission_code", sa.String),
    )
    op.bulk_insert(
        roles,
        [
            {
                "name": role,
                "display_name": _label(role),
                "description": f"{_label(role)} access",
            }
            for role in GRANTS
        ],
    )
    permission_codes = sorted({code for grants in GRANTS.values() for code in grants})
    op.bulk_insert(
        permissions,
        [{"code": code, "description": _label(code)} for code in permission_codes],
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role_name": role, "permission_code": code}
            for role, grants in GRANTS.items()
            for code in grants
        ],
    )
    op.create_foreign_key(
        "fk_staff_users_role_roles",
        "staff_users",
        "roles",
        ["role"],
        ["name"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_staff_users_role_roles", "staff_users", type_="foreignkey")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
