"""Introduce a shared user identity for customer and staff profiles.

Revision ID: 0006_shared_user_identity
Revises: 0005_order_idempotency
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0006_shared_user_identity"
down_revision = "0005_order_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=16), nullable=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("account_status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL",
            name="identity_contact_required",
        ),
        sa.CheckConstraint(
            "account_status IN ('active', 'suspended', 'disabled')",
            name="valid_account_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
    )

    bind = op.get_bind()
    customer_rows = bind.execute(
        sa.text(
            """
            SELECT id, phone, full_name, password_hash, phone_verified,
                   account_status, created_at, updated_at
            FROM customers WHERE password_hash IS NOT NULL
            """
        )
    ).mappings()
    for customer in customer_rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO users
                    (id, phone, full_name, password_hash, phone_verified,
                     account_status, created_at, updated_at)
                VALUES
                    (:id, :phone, :full_name, :password_hash, :phone_verified,
                     :account_status, :created_at, :updated_at)
                """
            ),
            dict(customer),
        )

    staff_rows = bind.execute(
        sa.text(
            """
            SELECT id, email, full_name, password_hash, status, created_at, updated_at
            FROM staff_users
            """
        )
    ).mappings()
    staff_user_ids: dict[uuid.UUID, uuid.UUID] = {}
    for staff in staff_rows:
        user_id = uuid.uuid4()
        staff_user_ids[staff["id"]] = user_id
        bind.execute(
            sa.text(
                """
                INSERT INTO users
                    (id, email, full_name, password_hash, phone_verified,
                     account_status, created_at, updated_at)
                VALUES
                    (:id, :email, :full_name, :password_hash, false,
                     :account_status, :created_at, :updated_at)
                """
            ),
            {
                "id": user_id,
                "email": staff["email"],
                "full_name": staff["full_name"],
                "password_hash": staff["password_hash"],
                "account_status": "active" if staff["status"] == "active" else "disabled",
                "created_at": staff["created_at"],
                "updated_at": staff["updated_at"],
            },
        )

    op.add_column("customers", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("customers", sa.Column("guest_phone", sa.String(length=16), nullable=True))
    bind.execute(
        sa.text(
            """
            UPDATE customers
            SET user_id = id, guest_phone = NULL
            WHERE password_hash IS NOT NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE customers
            SET guest_phone = phone
            WHERE password_hash IS NULL
            """
        )
    )
    op.drop_constraint("customers_phone_key", "customers", type_="unique")
    op.drop_index("ix_customers_phone", table_name="customers")
    for column in (
        "phone",
        "full_name",
        "password_hash",
        "phone_verified",
        "account_status",
        "role",
        "updated_at",
    ):
        op.drop_column("customers", column)
    op.create_foreign_key(
        "fk_customers_user_id_users",
        "customers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_customers_user_id", "customers", ["user_id"])
    op.create_index("ix_customers_guest_phone", "customers", ["guest_phone"])

    op.add_column("staff_users", sa.Column("user_id", sa.Uuid(), nullable=True))
    for staff_id, user_id in staff_user_ids.items():
        bind.execute(
            sa.text("UPDATE staff_users SET user_id = :user_id WHERE id = :staff_id"),
            {"user_id": user_id, "staff_id": staff_id},
        )
    op.alter_column("staff_users", "user_id", nullable=False)
    op.drop_constraint("staff_users_email_key", "staff_users", type_="unique")
    op.drop_index("ix_staff_users_email", table_name="staff_users")
    for column in ("email", "full_name", "password_hash"):
        op.drop_column("staff_users", column)
    op.create_foreign_key(
        "fk_staff_users_user_id_users",
        "staff_users",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_staff_users_user_id", "staff_users", ["user_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_account_status", "users", ["account_status"])


def downgrade() -> None:
    op.add_column("customers", sa.Column("phone", sa.String(length=16), nullable=True))
    op.add_column(
        "customers",
        sa.Column("full_name", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column("customers", sa.Column("password_hash", sa.String(length=255), nullable=True))
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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        """
        UPDATE customers AS customer
        SET phone = COALESCE(users.phone, customer.guest_phone),
            full_name = COALESCE(users.full_name, ''),
            password_hash = users.password_hash,
            phone_verified = COALESCE(users.phone_verified, false),
            account_status = COALESCE(users.account_status, 'active'),
            updated_at = COALESCE(users.updated_at, customer.created_at)
        FROM users
        WHERE customer.user_id = users.id
        """
    )
    op.execute("UPDATE customers SET phone = guest_phone WHERE user_id IS NULL")
    op.alter_column("customers", "phone", nullable=False)
    op.create_unique_constraint("customers_phone_key", "customers", ["phone"])
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.add_column("staff_users", sa.Column("email", sa.String(length=254), nullable=True))
    op.add_column(
        "staff_users",
        sa.Column("full_name", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column("staff_users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE staff_users AS staff
        SET email = users.email,
            full_name = users.full_name,
            password_hash = users.password_hash
        FROM users
        WHERE staff.user_id = users.id
        """
    )
    op.alter_column("staff_users", "email", nullable=False)
    op.alter_column("staff_users", "password_hash", nullable=False)
    op.create_unique_constraint("staff_users_email_key", "staff_users", ["email"])
    op.create_index("ix_staff_users_email", "staff_users", ["email"])

    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_staff_users_user_id", "staff_users", type_="unique")
    op.drop_constraint("fk_staff_users_user_id_users", "staff_users", type_="foreignkey")
    op.drop_column("staff_users", "user_id")
    op.drop_constraint("uq_customers_user_id", "customers", type_="unique")
    op.drop_constraint("fk_customers_user_id_users", "customers", type_="foreignkey")
    op.drop_index("ix_customers_guest_phone", table_name="customers")
    op.drop_column("customers", "guest_phone")
    op.drop_column("customers", "user_id")
    op.drop_table("users")
