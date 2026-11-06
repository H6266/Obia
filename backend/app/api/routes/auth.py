import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
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
from app.models import Customer, User
from app.schemas.customer import (
    CustomerAccount,
    LoginRequest,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    PhoneVerificationRequest,
    RegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
password_hasher = PasswordHasher()
dummy_password_hash = password_hasher.hash("not-a-real-customer-password-123")


def rate_limit(request: Request, db: Session) -> None:
    enforce_auth_rate_limit(request, db)


def unavailable_provider() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="This feature is unavailable until a verified SMS or password-recovery provider is configured.",
    )


@router.post(
    "/register",
    response_model=CustomerAccount,
    status_code=201,
    dependencies=[Depends(require_allowed_origin)],
)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Customer:
    rate_limit(request, db)
    customer = db.scalar(
        select(Customer).where(Customer.guest_phone == payload.phone)
    )
    existing_user = db.scalar(select(User).where(User.phone == payload.phone))
    if customer is not None and customer.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        )
    if customer is None:
        customer = Customer(guest_phone=payload.phone)
        db.add(customer)

    user = User(
        phone=payload.phone,
        full_name=payload.full_name,
        password_hash=password_hasher.hash(payload.password),
        phone_verified=False,
        account_status="active",
    )
    customer.user = user
    customer.guest_phone = None
    db.add(user)
    try:
        db.commit()
        db.refresh(customer)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists.",
        ) from error
    create_session(db, customer, response)
    return customer


@router.post(
    "/login",
    response_model=CustomerAccount,
    dependencies=[Depends(require_allowed_origin)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Customer:
    rate_limit(request, db)
    user = db.scalar(
        select(User)
        .options(joinedload(User.customer_profile))
        .where(User.phone == payload.phone)
    )
    customer = user.customer_profile if user else None
    password_hash = user.password_hash if user else dummy_password_hash
    try:
        password_matches = password_hasher.verify(password_hash, payload.password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        password_matches = False

    if (
        not password_matches
        or user is None
        or customer is None
        or user.account_status != "active"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phone number or password is incorrect.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(payload.password)
        db.commit()
    create_session(db, customer, response)
    return customer


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
def me(request: Request, db: Session = Depends(get_db)) -> Customer:
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
    if not token or not secrets.compare_digest(
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
    status_code=202,
    dependencies=[Depends(require_allowed_origin)],
)
def forgot_password(
    payload: PasswordRecoveryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rate_limit(request, db)
    raise unavailable_provider()


@router.post(
    "/reset-password",
    dependencies=[Depends(require_allowed_origin)],
)
def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rate_limit(request, db)
    raise unavailable_provider()


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
    raise unavailable_provider()


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
    raise unavailable_provider()
