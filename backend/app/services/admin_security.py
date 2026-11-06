import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import enforce_auth_rate_limit, require_allowed_origin, token_hash
from app.models import AdminAuditLog, RolePermission, StaffSession, StaffUser

STAFF_ROLES = {
    "owner",
    "super_admin",
    "operations_manager",
    "finance_manager",
    "customer_support",
    "inventory_officer",
    "agent_manager",
    "auditor",
}

ALL_PERMISSIONS = {
    "dashboard.read",
    "orders.read",
    "orders.manage",
    "orders.notes",
    "customers.read",
    "customers.read_sensitive",
    "customers.manage",
    "staff.manage",
    "audit.read",
    "inventory.read",
    "inventory.manage",
    "finance.read",
    "finance.reconcile",
    "refunds.approve",
    "agents.manage",
    "businesses.manage",
    "catalogue.read",
    "catalogue.manage",
}

DEFAULT_ROLE_PERMISSION_GRANTS = {
    "owner": ALL_PERMISSIONS,
    "super_admin": ALL_PERMISSIONS,
    "operations_manager": {
        "dashboard.read", "orders.read", "orders.manage", "orders.notes",
        "customers.read", "customers.read_sensitive", "catalogue.read",
    },
    "finance_manager": {
        "dashboard.read", "orders.read", "finance.read", "finance.reconcile",
        "refunds.approve",
    },
    "customer_support": {
        "dashboard.read", "orders.read", "orders.notes", "customers.read",
    },
    "inventory_officer": {"dashboard.read", "inventory.read", "inventory.manage"},
    "agent_manager": {"dashboard.read", "agents.manage"},
    "auditor": {
        "dashboard.read", "orders.read", "customers.read", "audit.read",
        "inventory.read", "finance.read",
    },
}


def permissions_for(role: str, db: Session) -> set[str]:
    return set(
        db.scalars(
            select(RolePermission.permission_code).where(
                RolePermission.role_name == role
            )
        ).all()
    )


def encrypt_totp_secret(secret: str) -> str:
    key = get_settings().staff_mfa_encryption_key
    if not key:
        raise RuntimeError("STAFF_MFA_ENCRYPTION_KEY must be configured before staff access is enabled.")
    return Fernet(key.encode("ascii")).encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_totp_secret(ciphertext: str) -> str:
    key = get_settings().staff_mfa_encryption_key
    if not key:
        raise RuntimeError("STAFF_MFA_ENCRYPTION_KEY must be configured before staff access is enabled.")
    return Fernet(key.encode("ascii")).decrypt(ciphertext.encode("ascii")).decode("ascii")


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_step(secret: str, code: str, now: float | None = None) -> int | None:
    if not code.isdigit() or len(code) != 6:
        return None
    normalized = secret.upper()
    padded = normalized + "=" * ((8 - len(normalized) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    current_step = int((time.time() if now is None else now) // 30)
    for step in (current_step - 1, current_step, current_step + 1):
        digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
        if hmac.compare_digest(f"{value:06d}", code):
            return step
    return None


def new_totp_code(secret: str, now: float | None = None) -> str:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded, casefold=True)
    step = int((time.time() if now is None else now) // 30)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def staff_rate_limit(request: Request, db: Session) -> None:
    settings = get_settings()
    enforce_auth_rate_limit(
        request,
        db,
        limit=settings.staff_auth_rate_limit,
        window_seconds=settings.auth_rate_window_seconds,
    )


def get_staff_session(
    request: Request, db: Session
) -> tuple[StaffSession, StaffUser] | None:
    token = request.cookies.get(get_settings().staff_session_cookie_name)
    if not token:
        return None
    session = db.get(StaffSession, token_hash(token))
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    staff = db.get(StaffUser, session.staff_user_id)
    if (
        staff is None
        or staff.status != "active"
        or not staff.mfa_enabled
        or staff.user.account_status != "active"
    ):
        return None
    return session, staff


def require_staff(request: Request, db: Session = Depends(get_db)) -> StaffUser:
    active = get_staff_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Staff authentication required.")
    return active[1]


def require_permission(permission: str):
    def dependency(
        staff: StaffUser = Depends(require_staff),
        db: Session = Depends(get_db),
    ) -> StaffUser:
        if permission not in permissions_for(staff.role, db):
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return staff
    return dependency


def require_staff_csrf(request: Request, db: Session = Depends(get_db)) -> None:
    require_allowed_origin(request)
    settings = get_settings()
    if not request.cookies.get(settings.staff_session_cookie_name):
        return
    active = get_staff_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Staff authentication required.")
    cookie_token = request.cookies.get(settings.staff_csrf_cookie_name, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not hmac.compare_digest(token_hash(cookie_token), active[0].csrf_token_hash)
    ):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


def create_staff_session(db: Session, staff: StaffUser, response: Response) -> None:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    db.add(
        StaffSession(
            id=token_hash(token),
            staff_user_id=staff.id,
            csrf_token_hash=token_hash(csrf_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.staff_session_ttl_hours),
        )
    )
    db.commit()
    options = {
        "max_age": settings.staff_session_ttl_hours * 3600,
        "secure": settings.session_cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(settings.staff_session_cookie_name, token, httponly=True, **options)
    response.set_cookie(settings.staff_csrf_cookie_name, csrf_token, httponly=False, **options)


def clear_staff_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.staff_session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        settings.staff_csrf_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )


def record_audit(
    db: Session,
    request: Request,
    actor: StaffUser | None,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    previous_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
    actor_email: str | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else (actor_email or "system"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason,
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        )
    )


StaffAuth = Annotated[StaffUser, Depends(require_staff)]
