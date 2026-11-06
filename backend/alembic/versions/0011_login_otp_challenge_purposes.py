"""Allow login OTP challenge purposes.

Revision ID: 0011_login_otp_purposes
Revises: 0010_customer_email_otp_auth
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_login_otp_purposes"
down_revision = "0010_customer_email_otp_auth"
branch_labels = None
depends_on = None

PURPOSES = "('email_verification', 'password_reset', 'customer_login', 'staff_login')"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite cannot ALTER CHECK constraints; tests use fresh metadata/create_all.
        # Recreate table with expanded constraint.
        with op.batch_alter_table("auth_challenges", recreate="always") as batch:
            batch.drop_constraint("valid_auth_challenge_purpose", type_="check")
            batch.create_check_constraint(
                "valid_auth_challenge_purpose",
                f"purpose IN {PURPOSES}",
            )
        return
    op.drop_constraint("valid_auth_challenge_purpose", "auth_challenges", type_="check")
    op.create_check_constraint(
        "valid_auth_challenge_purpose",
        "auth_challenges",
        f"purpose IN {PURPOSES}",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("auth_challenges", recreate="always") as batch:
            batch.drop_constraint("valid_auth_challenge_purpose", type_="check")
            batch.create_check_constraint(
                "valid_auth_challenge_purpose",
                "purpose IN ('email_verification', 'password_reset')",
            )
        return
    op.drop_constraint("valid_auth_challenge_purpose", "auth_challenges", type_="check")
    op.create_check_constraint(
        "valid_auth_challenge_purpose",
        "auth_challenges",
        "purpose IN ('email_verification', 'password_reset')",
    )
