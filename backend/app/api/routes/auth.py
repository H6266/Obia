from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    clear_session_cookies,
    create_session,
    enforce_auth_rate_limit,
    get_active_session,
    require_csrf_for_session,
    require_allowed_origin,
)
from app.models import AuthChallenge, AuthSession, Customer, User
from app.schemas.customer import (
    CustomerAccount,
    EmailVerificationRequest,
    GenericAuthResponse,
    LoginChallengeResponse,
    LoginRequest,
    LoginVerificationRequest,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    PhoneVerificationRequest,
    RegisterRequest,
    RegisterResponse,
    ResendEmailVerificationRequest,
    normalize_email,
)
from app.services import email_service
from app.services.otp_service import (
    enforce_otp_rate_limits,
    issue_challenge,
    utcnow,
    verify_challenge,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash("not-a-real-customer-password-123")
LOGIN_CHALLENGE_TTL_MINUTES = 15


def rate_limit(request: Request, db: Session) -> None:
    enforce_auth_rate_limit(request, db)


def generic_invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email/phone or password is incorrect.",
        headers={"WWW-Authenticate": "Cookie"},
    )


def generic_verification_response(email: str) -> GenericAuthResponse:
    return GenericAuthResponse(
        message="If an eligible account exists for that email address, a verification code has been sent."
    )


def generic_recovery_response() -> GenericAuthResponse:
    return GenericAuthResponse(
        message="If an eligible account exists for that email address, password recovery instructions have been sent."
    )


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "••••"
    return f"•••• {digits[-4:]}"


def find_customer_by_email(db: Session, email: str) -> Customer | None:
    return db.scalar(
        select(Customer)
        .join(User, Customer.user_id == User.id)
        .options(joinedload(Customer.user))
        .where(func.lower(User.email) == normalize_email(email))
    )


def _issue_login_challenge(
    db: Session,
    request: Request,
    *,
    user: User,
    purpose: str,
    account_label: str,
    channel: str = "email",
) -> tuple[AuthChallenge, str]:
    channels = ["email"]
    if getattr(user, "phone_verified", False) and getattr(user, "phone", None):
        channels.append("phone")
    if channel == "phone":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phone verification codes are unavailable until an SMS provider is configured. Use email verification.",
        )
    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verified email address is available for this account.",
        )
    enforce_otp_rate_limits(request, db, email=user.email, scope=f"{purpose}:{channel}")
    challenge, code = issue_challenge(
        db,
        email=user.email,
        purpose=purpose,
        user_id=user.id,
        enforce_cooldown=False,
    )
    # Reuse the auth challenge as a short-lived login token by extending metadata via
    # deterministic token derivation: we return challenge.id as the opaque token.
    try:
        email_service.send_email(
            to=user.email,
            content=email_service.login_otp_email(code=code, account_label=account_label),
        )
    except email_service.EmailDeliveryError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send the sign-in code right now. Please try again later.",
        ) from error
    db.commit()
    return challenge, str(challenge.id)


def _resolve_login_challenge(
    db: Session, *, challenge_token: str, purpose: str
) -> AuthChallenge:
    try:
        import uuid

        challenge_id = uuid.UUID(challenge_token)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The sign-in code is invalid or has expired.",
        ) from error
    challenge = db.scalar(
        select(AuthChallenge).where(
            AuthChallenge.id == challenge_id,
            AuthChallenge.purpose == purpose,
        )
    )
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The sign-in code is invalid or has expired.",
        )
    return challenge


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_allowed_origin)],
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    rate_limit(request, db)
    email = normalize_email(payload.email)
    existing_email = db.scalar(select(User.id).where(func.lower(User.email) == email))
    existing_phone = db.scalar(select(User.id).where(User.phone == payload.phone))
    if existing_email is not None or existing_phone is not None:
        # Do not leak whether an email/phone is registered. Generic response.
        return RegisterResponse(
            email=email,
            verification_required=True,
            message="If the account can be created, a verification code will be sent to the provided email address.",
        )

    customer = db.scalar(select(Customer).where(Customer.guest_phone == payload.phone))
    if customer is None:
        customer = Customer(guest_phone=payload.phone)
        db.add(customer)

    user = User(
        email=email,
        phone=payload.phone,
        full_name=payload.full_name,
        password_hash=password_hasher.hash(payload.password),
        phone_verified=False,
        email_verified=False,
        account_status="active",
    )
    customer.user = user
    customer.guest_phone = None
    db.add(user)
    try:
        db.flush()
        enforce_otp_rate_limits(request, db, email=email, scope="email_verification")
        challenge, code = issue_challenge(
            db,
            email=email,
            purpose="email_verification",
            user_id=user.id,
            enforce_cooldown=False,
        )
        settings = get_settings()
        verify_url = f"{settings.public_app_url.rstrip('/')}/verify-email?email={email}"
        try:
            email_service.send_email(to=email, content=email_service.verification_email(code=code, verify_url=verify_url))
        except email_service.EmailDeliveryError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send the verification email right now. Please try again later.",
            ) from error
        db.commit()
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        return RegisterResponse(
            email=email,
            verification_required=True,
            message="If the account can be created, a verification code will be sent to the provided email address.",
        )
    return RegisterResponse(
        email=email,
        verification_required=True,
        message="Verification is required before signing in. A verification code has been sent to your email address.",
    )


@router.post(
    "/verify-email",
    response_model=CustomerAccount,
    dependencies=[Depends(require_allowed_origin)],
)
def verify_email(
    payload: EmailVerificationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> CustomerAccount:
    rate_limit(request, db)
    enforce_otp_rate_limits(request, db, email=payload.email, scope="verify_email")
    result = verify_challenge(
        db,
        email=payload.email,
        purpose="email_verification",
        code=payload.code,
    )
    user = result.user
    if user is None or user.customer_profile is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or has expired.",
        )
    if user.account_status != "active":
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active.")
    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = utcnow()
    db.commit()
    db.refresh(user.customer_profile)
    create_session(db, user.customer_profile, response)
    return user.customer_profile


@router.post(
    "/resend-email-verification",
    response_model=GenericAuthResponse,
    dependencies=[Depends(require_allowed_origin)],
)
def resend_email_verification(
    payload: ResendEmailVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericAuthResponse:
    rate_limit(request, db)
    email = normalize_email(payload.email)
    enforce_otp_rate_limits(request, db, email=email, scope="resend_email_verification")
    user = db.scalar(
        select(User)
        .options(joinedload(User.customer_profile))
        .where(func.lower(User.email) == email)
    )
    if user is None or user.customer_profile is None or user.email_verified or user.account_status != "active":
        return generic_verification_response(email)
    try:
        challenge, code = issue_challenge(
            db,
            email=email,
            purpose="email_verification",
            user_id=user.id,
            enforce_cooldown=True,
        )
        settings = get_settings()
        verify_url = f"{settings.public_app_url.rstrip('/')}/verify-email?email={email}"
        email_service.send_email(to=email, content=email_service.verification_email(code=code, verify_url=verify_url))
        db.commit()
    except HTTPException as error:
        if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            raise
        db.rollback()
        return generic_verification_response(email)
    except email_service.EmailDeliveryError:
        db.rollback()
        return generic_verification_response(email)
    return generic_verification_response(email)


@router.post(
    "/login",
    response_model=LoginChallengeResponse,
    dependencies=[Depends(require_allowed_origin)],
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> LoginChallengeResponse:
    rate_limit(request, db)
    identifier_email = normalize_email(payload.email) if payload.email else None
    query = select(User).options(joinedload(User.customer_profile))
    if identifier_email:
        query = query.where(func.lower(User.email) == identifier_email)
    elif payload.phone:
        query = query.where(User.phone == payload.phone)
    user = db.scalar(query)
    customer = user.customer_profile if user else None
    password_hash = user.password_hash if user else dummy_password_hash
    try:
        password_matches = password_hasher.verify(password_hash, payload.password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        password_matches = False

    if not password_matches or user is None or customer is None:
        raise generic_invalid_credentials()
    if user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not available.",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before signing in.",
        )
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(payload.password)
        db.commit()

    channels = ["email"] if user.email else []
    if user.phone_verified and user.phone:
        channels.append("phone")
    if not channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No delivery channel is available for this account.",
        )
    challenge, token = _issue_login_challenge(
        db,
        request,
        user=user,
        purpose="customer_login",
        account_label="Obia account",
        channel="email",
    )
    return LoginChallengeResponse(
        login_required=True,
        challenge_token=token,
        email=user.email,
        phone_masked=mask_phone(user.phone),
        channels=channels,
        message="Credentials verified. Enter the 8-digit code sent to your selected channel to complete sign-in.",
    )


@router.post(
    "/login/verify",
    response_model=CustomerAccount,
    dependencies=[Depends(require_allowed_origin)],
)
def verify_login(
    payload: LoginVerificationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> CustomerAccount:
    rate_limit(request, db)
    pending = _resolve_login_challenge(db, challenge_token=payload.challenge_token, purpose="customer_login")
    user = db.get(User, pending.user_id) if pending.user_id else None
    if user is None or user.customer_profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The sign-in code is invalid or has expired.",
        )
    if payload.channel == "phone":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phone verification codes are unavailable until an SMS provider is configured. Use email verification.",
        )
    enforce_otp_rate_limits(request, db, email=user.email or pending.email, scope="customer_login:verify")
    verify_challenge(db, email=pending.email, purpose="customer_login", code=payload.code)
    if user.account_status != "active" or not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not available.")
    create_session(db, user.customer_profile, response)
    return user.customer_profile


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf_for_session)],
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    active = get_active_session(request, db)
    if active:
        db.delete(active[0])
        db.commit()
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=CustomerAccount)
def me(request: Request, db: Session = Depends(get_db)) -> CustomerAccount:
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return active[1]


@router.get("/csrf")
def csrf_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    token = request.cookies.get(get_settings().csrf_cookie_name, "")
    import hashlib
    import hmac
    import secrets

    if not token or not hmac.compare_digest(
        hashlib.sha256(token.encode("utf-8")).hexdigest(),
        active[0].csrf_token_hash,
    ):
        token = secrets.token_urlsafe(32)
        active[0].csrf_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        db.commit()
    settings = get_settings()
    response.set_cookie(
        settings.csrf_cookie_name,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


@router.post(
    "/forgot-password",
    response_model=GenericAuthResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_allowed_origin)],
)
def forgot_password(
    payload: PasswordRecoveryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericAuthResponse:
    rate_limit(request, db)
    email = normalize_email(payload.email)
    enforce_otp_rate_limits(request, db, email=email, scope="forgot_password")
    user = db.scalar(
        select(User)
        .options(joinedload(User.customer_profile))
        .where(func.lower(User.email) == email)
    )
    if user is not None and user.customer_profile is not None and user.account_status == "active":
        try:
            challenge, code = issue_challenge(
                db,
                email=email,
                purpose="password_reset",
                user_id=user.id,
                enforce_cooldown=True,
            )
            email_service.send_email(to=email, content=email_service.password_recovery_email(code=code))
            db.commit()
        except HTTPException as error:
            if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                raise
            db.rollback()
        except email_service.EmailDeliveryError:
            db.rollback()
    return generic_recovery_response()


@router.post(
    "/reset-password",
    response_model=GenericAuthResponse,
    dependencies=[Depends(require_allowed_origin)],
)
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GenericAuthResponse:
    rate_limit(request, db)
    enforce_otp_rate_limits(request, db, email=payload.email, scope="reset_password")
    result = verify_challenge(
        db,
        email=payload.email,
        purpose="password_reset",
        code=payload.code,
    )
    user = result.user
    if user is None or user.customer_profile is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The recovery code is invalid or has expired.",
        )
    user.password_hash = password_hasher.hash(payload.new_password)
    # Invalidate all existing sessions for the affected user/customer.
    db.query(AuthSession).filter(AuthSession.customer_id == user.customer_profile.id).delete(
        synchronize_session=False
    )
    db.commit()
    try:
        email_service.send_email(to=user.email or payload.email, content=email_service.password_changed_email())
    except email_service.EmailDeliveryError:
        # Password has already been changed and sessions invalidated; do not fail the reset.
        pass
    return GenericAuthResponse(message="Your password has been reset. Sign in with your new password.")


# Phone verification endpoints retained for compatibility; SMS provider not configured.
@router.post(
    "/verify-phone",
    dependencies=[Depends(require_csrf_for_session), Depends(require_allowed_origin)],
)
def verify_phone(
    payload: PhoneVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rate_limit(request, db)
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="This feature is unavailable until a verified SMS provider is configured.",
    )


@router.post(
    "/resend-verification",
    dependencies=[Depends(require_csrf_for_session), Depends(require_allowed_origin)],
)
def resend_verification(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rate_limit(request, db)
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if active[1].phone_verified:
        raise HTTPException(status_code=409, detail="Phone number is already verified.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="This feature is unavailable until a verified SMS provider is configured.",
    )
