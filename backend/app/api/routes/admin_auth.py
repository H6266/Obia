import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_allowed_origin, token_hash
from app.models import AdminAuditLog, Role, StaffInvitation, StaffUser, User
from app.schemas.admin import (
    AcceptStaffInvitationRequest,
    ConfirmStaffMfaRequest,
    StaffAccount,
    StaffEnrollmentRead,
    StaffInvitationCreated,
    StaffInvitationRead,
    StaffInvitationRequest,
    StaffLoginRequest,
)
from app.services.admin_security import (
    create_staff_session,
    decrypt_totp_secret,
    encrypt_totp_secret,
    get_staff_session,
    new_totp_secret,
    permissions_for,
    record_audit,
    require_permission,
    require_staff,
    require_staff_csrf,
    staff_rate_limit,
    totp_step,
)

router = APIRouter(prefix="/admin", tags=["admin operations"])
auth_router = APIRouter(prefix="/auth", tags=["admin authentication"])
staff_router = APIRouter(prefix="/staff", tags=["admin staff"])
password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash("not-a-real-staff-account-password-2026")


@auth_router.post("/login", dependencies=[Depends(require_allowed_origin)])
def login(
    payload: StaffLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> StaffAccount:
    staff_rate_limit(request, db)
    staff = db.scalar(
        select(StaffUser)
        .join(User, StaffUser.user_id == User.id)
        .where(User.email == payload.email)
    )
    password_hash = staff.password_hash if staff else dummy_password_hash
    try:
        password_matches = password_hasher.verify(password_hash, payload.password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        password_matches = False

    if (
        staff is None
        or staff.status != "active"
        or staff.user.account_status != "active"
        or not staff.mfa_enabled
        or not staff.mfa_secret_encrypted
        or not password_matches
    ):
        raise HTTPException(status_code=401, detail="Email, password, or authenticator code is incorrect.")

    step = totp_step(decrypt_totp_secret(staff.mfa_secret_encrypted), payload.totp_code)
    if step is None:
        raise HTTPException(status_code=401, detail="Email, password, or authenticator code is incorrect.")

    consumed = db.execute(
        update(StaffUser)
        .where(
            StaffUser.id == staff.id,
            or_(StaffUser.last_totp_step.is_(None), StaffUser.last_totp_step < step),
        )
        .values(last_totp_step=step)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="Email, password, or authenticator code is incorrect.")
    db.commit()
    create_staff_session(db, staff, response)
    return StaffAccount.from_staff(staff, permissions_for(staff.role, db))


@auth_router.post(
    "/accept-invitation",
    response_model=StaffEnrollmentRead,
    dependencies=[Depends(require_allowed_origin)],
)
def accept_invitation(
    payload: AcceptStaffInvitationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StaffEnrollmentRead:
    staff_rate_limit(request, db)
    if not get_settings().staff_mfa_encryption_key:
        raise HTTPException(
            status_code=503,
            detail="Staff onboarding is unavailable until STAFF_MFA_ENCRYPTION_KEY is configured.",
        )
    invitation = db.scalar(
        select(StaffInvitation)
        .where(StaffInvitation.token_hash == token_hash(payload.token))
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if invitation is None or invitation.accepted_at is not None:
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired.")
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now or db.scalar(
        select(User.id).where(User.email == invitation.email)
    ):
        raise HTTPException(status_code=400, detail="This invitation is invalid or has expired.")

    secret = new_totp_secret()
    enrollment_token = secrets.token_urlsafe(32)
    user = User(
        email=invitation.email,
        full_name=invitation.full_name,
        password_hash=password_hasher.hash(payload.password),
        account_status="disabled",
    )
    staff = StaffUser(
        user=user,
        role=invitation.role,
        status="pending_mfa",
        mfa_secret_encrypted=encrypt_totp_secret(secret),
        enrollment_token_hash=token_hash(enrollment_token),
        enrollment_expires_at=now + timedelta(minutes=30),
    )
    invitation.accepted_at = now
    db.add(staff)
    db.add(
        AdminAuditLog(
            actor_id=None,
            actor_email=invitation.email,
            action="staff.invitation.accepted",
            resource_type="staff_user",
            resource_id=invitation.id.hex,
            new_value={"role": invitation.role},
            request_id=getattr(request.state, "request_id", secrets.token_hex(16)),
        )
    )
    try:
        db.commit()
        record_audit(
            db, request, staff, action="staff.login", resource_type="staff_user",
            resource_id=str(staff.id),
        )
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This invitation is invalid or has expired.") from error

    issuer = "Falaaa"
    return StaffEnrollmentRead(
        enrollment_token=enrollment_token,
        totp_secret=secret,
        issuer=issuer,
        account_name=staff.email,
    )


@auth_router.post(
    "/confirm-enrollment",
    response_model=StaffAccount,
    dependencies=[Depends(require_allowed_origin)],
)
def confirm_enrollment(
    payload: ConfirmStaffMfaRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StaffAccount:
    staff_rate_limit(request, db)
    staff = db.scalar(
        select(StaffUser).where(
            StaffUser.enrollment_token_hash == token_hash(payload.enrollment_token),
            StaffUser.status == "pending_mfa",
        )
    )
    if staff is None or not staff.mfa_secret_encrypted:
        raise HTTPException(status_code=400, detail="The enrollment session is invalid or expired.")
    if staff.enrollment_expires_at is None:
        raise HTTPException(status_code=400, detail="The enrollment session is invalid or expired.")
    enrollment_expires_at = staff.enrollment_expires_at
    if enrollment_expires_at.tzinfo is None:
        enrollment_expires_at = enrollment_expires_at.replace(tzinfo=timezone.utc)
    if enrollment_expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="The enrollment session is invalid or expired.")
    step = totp_step(decrypt_totp_secret(staff.mfa_secret_encrypted), payload.totp_code)
    if step is None:
        raise HTTPException(status_code=400, detail="The authenticator code is incorrect.")
    staff.mfa_enabled = True
    staff.status = "active"
    staff.user.account_status = "active"
    staff.enrollment_token_hash = None
    staff.enrollment_expires_at = None
    staff.last_totp_step = step
    db.add(
        AdminAuditLog(
            actor_id=staff.id,
            actor_email=staff.email,
            action="staff.mfa.enabled",
            resource_type="staff_user",
            resource_id=staff.id.hex,
            new_value={"mfa_enabled": True, "role": staff.role},
            request_id=getattr(request.state, "request_id", secrets.token_hex(16)),
        )
    )
    db.commit()
    db.refresh(staff)
    return StaffAccount.from_staff(staff, permissions_for(staff.role, db))


@auth_router.get("/me", response_model=StaffAccount)
def me(
    staff: StaffUser = Depends(require_staff),
    db: Session = Depends(get_db),
) -> StaffAccount:
    return StaffAccount.from_staff(staff, permissions_for(staff.role, db))


@auth_router.get("/csrf")
def csrf(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    active = get_staff_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Staff authentication required.")
    settings = get_settings()
    token = request.cookies.get(settings.staff_csrf_cookie_name, "")
    if not token or not secrets.compare_digest(
        hashlib.sha256(token.encode()).hexdigest(), active[0].csrf_token_hash
    ):
        token = secrets.token_urlsafe(32)
        active[0].csrf_token_hash = hashlib.sha256(token.encode()).hexdigest()
        db.commit()
    response.set_cookie(
        settings.staff_csrf_cookie_name,
        token,
        max_age=settings.staff_session_ttl_hours * 3600,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


@auth_router.post("/logout", status_code=204, dependencies=[Depends(require_staff_csrf)])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    active = get_staff_session(request, db)
    if active:
        record_audit(
            db, request, active[1], action="staff.logout", resource_type="staff_user",
            resource_id=str(active[1].id),
        )
        db.delete(active[0])
        db.commit()
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
    response.status_code = 204
    return response


@staff_router.get("/roles")
def roles(
    staff: StaffUser = Depends(require_permission("staff.manage")),
    db: Session = Depends(get_db),
) -> list[dict]:
    del staff
    available_roles = db.scalars(select(Role.name).order_by(Role.name)).all()
    return [
        {"role": role, "permissions": sorted(permissions_for(role, db))}
        for role in available_roles
    ]


@staff_router.post(
    "/invitations",
    response_model=StaffInvitationCreated,
    status_code=201,
    dependencies=[Depends(require_allowed_origin)],
)
def create_invitation(
    payload: StaffInvitationRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("staff.manage")),
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_staff_csrf),
):
    if not get_settings().staff_mfa_encryption_key:
        raise HTTPException(
            status_code=503,
            detail="Staff onboarding is unavailable until STAFF_MFA_ENCRYPTION_KEY is configured.",
        )
    if staff.role != "owner" and payload.role == "super_admin":
        raise HTTPException(status_code=403, detail="Only the owner can invite a Super Admin.")
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise HTTPException(
            status_code=409,
            detail="An account already uses this email. Existing accounts must be linked through the verified account-linking workflow.",
        )
    active_invitation = db.scalar(
        select(StaffInvitation).where(
            StaffInvitation.email == payload.email,
            StaffInvitation.accepted_at.is_(None),
            StaffInvitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if active_invitation:
        raise HTTPException(status_code=409, detail="An active invitation already exists for this email.")

    raw_token = secrets.token_urlsafe(32)
    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email=payload.email,
        full_name=payload.full_name.strip(),
        role=payload.role,
        token_hash=token_hash(raw_token),
        invited_by_id=staff.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
    )
    db.add(invitation)
    record_audit(
        db,
        request,
        staff,
        action="staff.invitation.created",
        resource_type="staff_invitation",
        resource_id=str(invitation.id),
        new_value={"email": invitation.email, "role": invitation.role},
    )
    db.commit()
    db.refresh(invitation)
    return StaffInvitationCreated(
        **StaffInvitationRead.model_validate(invitation).model_dump(),
        invitation_token=raw_token,
    )


@staff_router.get("/invitations", response_model=list[StaffInvitationRead])
def list_invitations(
    staff: StaffUser = Depends(require_permission("staff.manage")),
    db: Session = Depends(get_db),
) -> list[StaffInvitationRead]:
    del staff
    invitations = db.scalars(
        select(StaffInvitation).order_by(StaffInvitation.created_at.desc()).limit(100)
    ).all()
    return [StaffInvitationRead.model_validate(invitation) for invitation in invitations]


@staff_router.get("", response_model=list[StaffAccount])
def list_staff(
    request: Request,
    staff: StaffUser = Depends(require_permission("staff.manage")),
    db: Session = Depends(get_db),
) -> list[StaffAccount]:
    del staff
    staff_users = db.scalars(
        select(StaffUser).order_by(StaffUser.created_at.desc()).limit(200)
    ).all()
    record_audit(
        db, request, staff, action="staff.listed",
        resource_type="staff_collection", resource_id="all",
    )
    db.commit()
    return [
        StaffAccount.from_staff(item, permissions_for(item.role, db))
        for item in staff_users
    ]


router.include_router(auth_router)
router.include_router(staff_router)
