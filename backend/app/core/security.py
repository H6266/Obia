import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.models import AuthSession, Customer, RateLimitBucket


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_active_session(
    request: Request, db: Session
) -> tuple[AuthSession, Customer] | None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    session = db.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.customer).joinedload(Customer.user))
        .where(AuthSession.id == token_hash(token))
    )
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    if session.customer.user is None or session.customer.user.account_status != "active":
        return None
    return session, session.customer


def optional_customer(
    request: Request, db: Session = Depends(get_db)
) -> Customer | None:
    active = get_active_session(request, db)
    return active[1] if active else None


def require_allowed_origin(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin and origin not in get_settings().allowed_origins:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")


def require_customer(
    request: Request, db: Session = Depends(get_db)
) -> Customer:
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return active[1]


def require_csrf_for_session(request: Request, db: Session = Depends(get_db)) -> None:
    require_allowed_origin(request)
    settings = get_settings()
    if not request.cookies.get(settings.session_cookie_name):
        return
    active = get_active_session(request, db)
    if active is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    cookie_token = request.cookies.get(settings.csrf_cookie_name, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not hmac.compare_digest(token_hash(cookie_token), active[0].csrf_token_hash)
    ):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


def create_session(db: Session, customer: Customer, response: Response) -> None:
    settings = get_settings()
    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(
        AuthSession(
            id=token_hash(session_token),
            customer_id=customer.id,
            csrf_token_hash=token_hash(csrf_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    cookie_options = {
        "max_age": settings.session_ttl_hours * 3600,
        "secure": settings.session_cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        **cookie_options,
    )


def clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.session_cookie_secure,
            httponly=name == settings.session_cookie_name,
            samesite=settings.cookie_samesite,
        )


def enforce_auth_rate_limit(
    request: Request,
    db: Session,
    *,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> None:
    settings = get_settings()
    window_seconds = window_seconds or settings.auth_rate_window_seconds
    now = datetime.now(timezone.utc)
    window_id = int(now.timestamp()) // window_seconds
    client_ip = request.client.host if request.client else "unknown"
    bucket_key = token_hash(f"{request.url.path}:{client_ip}:{window_id}")
    statement_values = {"bucket_key": bucket_key, "attempts": 1}
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        statement = sqlite_insert(RateLimitBucket).values(**statement_values)
    else:
        statement = pg_insert(RateLimitBucket).values(**statement_values)
    statement = statement.on_conflict_do_update(
        index_elements=[RateLimitBucket.bucket_key],
        set_={"attempts": RateLimitBucket.attempts + 1},
    ).returning(RateLimitBucket.attempts)
    attempts = db.scalar(statement)
    db.execute(
        delete(RateLimitBucket).where(
            RateLimitBucket.created_at < now - timedelta(seconds=window_seconds * 2)
        )
    )
    db.commit()
    if attempts is not None and attempts > (limit or settings.auth_rate_limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(window_seconds)},
        )


CustomerAuth = Annotated[Customer, Depends(require_customer)]
