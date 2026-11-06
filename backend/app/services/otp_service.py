import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import enforce_auth_rate_limit
from app.models import AuthChallenge, User

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_EMAIL_LIMIT = 5
OTP_IP_LIMIT = 15
OTP_WINDOW_SECONDS = 600


@dataclass
class VerificationResult:
    challenge: AuthChallenge
    user: User | None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(100_000_000):08d}"


def otp_digest(purpose: str, email: str, code: str) -> str:
    secret = get_settings().otp_hash_secret.encode("utf-8")
    message = f"{purpose}:{normalize_email(email)}:{code}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def enforce_otp_rate_limits(request: Request, db: Session, *, email: str, scope: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    enforce_auth_rate_limit(
        request,
        db,
        limit=OTP_IP_LIMIT,
        window_seconds=OTP_WINDOW_SECONDS,
        bucket_prefix=f"otp:{scope}:ip:{client_ip}",
        commit=False,
    )
    enforce_auth_rate_limit(
        request,
        db,
        limit=OTP_EMAIL_LIMIT,
        window_seconds=OTP_WINDOW_SECONDS,
        bucket_prefix=f"otp:{scope}:email:{normalize_email(email)}",
        commit=False,
    )


def latest_challenge(
    db: Session, *, email: str, purpose: str, active_only: bool = False
) -> AuthChallenge | None:
    query = select(AuthChallenge).where(
        AuthChallenge.email == normalize_email(email),
        AuthChallenge.purpose == purpose,
    )
    if active_only:
        query = query.where(AuthChallenge.consumed_at.is_(None))
    return db.scalar(query.order_by(AuthChallenge.created_at.desc()).limit(1))


def issue_challenge(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id=None,
    enforce_cooldown: bool = True,
) -> tuple[AuthChallenge, str]:
    settings = get_settings()
    if not settings.otp_hash_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email authentication is unavailable until OTP security is configured.",
        )
    now = utcnow()
    normalized = normalize_email(email)
    previous = latest_challenge(db, email=normalized, purpose=purpose, active_only=True)
    if (
        enforce_cooldown
        and previous is not None
        and previous.consumed_at is None
        and previous.created_at.replace(tzinfo=timezone.utc)
        > now - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code.",
            headers={"Retry-After": str(OTP_RESEND_COOLDOWN_SECONDS)},
        )

    if previous is not None and previous.consumed_at is None:
        previous.consumed_at = now

    code = generate_otp_code()
    challenge = AuthChallenge(
        user_id=user_id,
        email=normalized,
        purpose=purpose,
        code_hash=otp_digest(purpose, normalized, code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
    )
    db.add(challenge)
    db.flush()
    return challenge, code


def verify_challenge(
    db: Session,
    *,
    email: str,
    purpose: str,
    code: str,
) -> VerificationResult:
    normalized = normalize_email(email)
    now = utcnow()
    query = (
        select(AuthChallenge)
        .where(
            AuthChallenge.email == normalized,
            AuthChallenge.purpose == purpose,
            AuthChallenge.consumed_at.is_(None),
        )
        .order_by(AuthChallenge.created_at.desc())
        .limit(1)
    )
    bind = db.get_bind()
    if bind is not None and bind.dialect.name != "sqlite":
        query = query.with_for_update()
    challenge = db.scalar(query)
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or has expired.",
        )
    expires_at = challenge.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or has expired.",
        )
    if challenge.attempts >= challenge.max_attempts:
        challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Request a new code.",
        )

    expected = otp_digest(purpose, normalized, code.strip())
    if not hmac.compare_digest(expected, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= challenge.max_attempts:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The verification code is invalid or has expired.",
        )

    challenge.consumed_at = now
    user = db.get(User, challenge.user_id) if challenge.user_id else None
    if user is None:
        user = db.scalar(select(User).where(User.email == normalized))
    return VerificationResult(challenge=challenge, user=user)
