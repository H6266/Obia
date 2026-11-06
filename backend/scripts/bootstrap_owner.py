import getpass
import re
import sys
import uuid
from urllib.parse import quote

from argon2 import PasswordHasher
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import AdminAuditLog, StaffUser
from app.services.admin_security import (
    encrypt_totp_secret,
    new_totp_code,
    new_totp_secret,
    totp_step,
)


def main() -> int:
    settings = get_settings()
    if not settings.staff_mfa_encryption_key:
        print("Set STAFF_MFA_ENCRYPTION_KEY before bootstrapping the owner.", file=sys.stderr)
        return 2
    try:
        encrypt_totp_secret("configuration-check")
    except ValueError as error:
        print(f"STAFF_MFA_ENCRYPTION_KEY is invalid: {error}", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        if db.scalar(select(StaffUser.id).where(StaffUser.role == "owner")):
            print("An owner account already exists; refusing to create another.", file=sys.stderr)
            return 2

        full_name = input("Owner full name: ").strip()
        email = input("Owner email: ").strip().lower()
        password = getpass.getpass("Owner password (minimum 14 characters): ")
        if len(full_name) < 2 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            print("A full name and valid email address are required.", file=sys.stderr)
            return 2
        if len(password) < 14 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            print("Password must be at least 14 characters and contain a letter and a number.", file=sys.stderr)
            return 2
        if db.scalar(select(StaffUser.id).where(StaffUser.email == email)):
            print("A staff account already uses this email.", file=sys.stderr)
            return 2

        secret = new_totp_secret()
        issuer = "Falaaa"
        provisioning_uri = (
            f"otpauth://totp/{quote(issuer + ':' + email)}?secret={secret}"
            f"&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
        )
        print("\nAdd this account to an authenticator app before continuing:")
        print(provisioning_uri)
        code = input("Enter the current 6-digit authenticator code: ").strip()
        step = totp_step(secret, code)
        if step is None:
            print("Authenticator code did not verify; no owner was created.", file=sys.stderr)
            return 2

        owner = StaffUser(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            password_hash=PasswordHasher().hash(password),
            role="owner",
            status="active",
            mfa_secret_encrypted=encrypt_totp_secret(secret),
            mfa_enabled=True,
            last_totp_step=step,
        )
        db.add(owner)
        db.add(
            AdminAuditLog(
                actor_id=owner.id,
                actor_email=owner.email,
                action="staff.owner.bootstrapped",
                resource_type="staff_user",
                resource_id=str(owner.id),
                new_value={"role": "owner", "mfa_enabled": True},
                request_id=f"bootstrap-{owner.id}",
            )
        )
        db.commit()
        print(f"Owner account {email} created with MFA enabled.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
