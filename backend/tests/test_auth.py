import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import token_hash
from app.models import AuthChallenge, AuthSession, Customer, Order, RateLimitBucket, User
from app.services import email_service
from app.services.otp_service import otp_digest

password_hasher = PasswordHasher()


def registration_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "full_name": "Amina Mensah",
        "email": "amina@example.com",
        "phone": "+233 24 123 4567",
        "password": "secure-customer-pass-2026",
        **overrides,
    }


def login_payload(**overrides: Any) -> dict[str, Any]:
    return {
        "email": "amina@example.com",
        "password": "secure-customer-pass-2026",
        **overrides,
    }


def csrf_header(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


class EmailCapture:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.fail = False

    def send(self, *, to: str, content: Any) -> None:
        if self.fail:
            raise email_service.EmailDeliveryError("mock failure")
        self.messages.append({"to": to, "subject": content.subject, "text": content.text, "html": content.html})

    @property
    def last_code(self) -> str:
        text = self.messages[-1]["text"]
        for token in text.split():
            if token.isdigit() and len(token) == 8:
                return token
        raise AssertionError("No OTP code found in sent message.")

    def code_at(self, index: int) -> str:
        text = self.messages[index]["text"]
        for token in text.split():
            if token.isdigit() and len(token) == 8:
                return token
        raise AssertionError("No OTP code found in sent message.")


def configure_email_auth(monkeypatch: Any, *, capture: EmailCapture | None = None) -> EmailCapture:
    get_settings.cache_clear()
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "Obia <no-reply@obia.test>")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://obia.test")
    monkeypatch.setenv("OTP_HASH_SECRET", "test-otp-hash-secret-please-change")
    monkeypatch.setenv("AUTH_RATE_LIMIT", "1000")
    capture = capture or EmailCapture()
    monkeypatch.setattr(email_service, "send_email", capture.send)
    return capture


def register_and_get_code(client: TestClient, monkeypatch: Any, **payload_overrides: Any) -> tuple[EmailCapture, dict[str, Any]]:
    capture = configure_email_auth(monkeypatch)
    response = client.post("/api/v1/auth/register", json=registration_payload(**payload_overrides))
    assert response.status_code == 201
    return capture, response.json()


def verify_user(client: TestClient, email: str, code: str) -> dict[str, Any]:
    response = client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    assert response.status_code == 200
    return response.json()


def create_reset_challenge(
    db_session_factory: sessionmaker[Session], *, email: str, code: str, purpose: str = "password_reset", **overrides: Any
) -> None:
    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        db.add(
            AuthChallenge(
                user_id=user.id if user else None,
                email=email.lower(),
                purpose=purpose,
                code_hash=otp_digest(purpose, email, code),
                expires_at=overrides.get("expires_at", now + timedelta(minutes=10)),
                attempts=overrides.get("attempts", 0),
                max_attempts=overrides.get("max_attempts", 5),
                consumed_at=overrides.get("consumed_at"),
            )
        )
        db.commit()


def test_successful_registration_creates_unverified_account_sends_otp_and_does_not_create_session(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    capture, payload = register_and_get_code(client, monkeypatch)
    assert payload["verification_required"] is True
    assert payload["email"] == "amina@example.com"
    assert "obia_session" not in client.cookies
    assert client.get("/api/v1/auth/me").status_code == 401
    assert len(capture.messages) == 1
    assert capture.messages[0]["to"] == "amina@example.com"
    assert capture.last_code.isdigit() and len(capture.last_code) == 8
    assert capture.last_code not in payload["message"]

    with db_session_factory() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == "amina@example.com"))
        assert user is not None
        assert user.email_verified is False
        assert user.password_hash.startswith("$argon2id$")
        challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.user_id == user.id))
        assert challenge is not None
        assert challenge.purpose == "email_verification"
        assert challenge.code_hash != capture.last_code
        assert challenge.attempts == 0
        assert challenge.max_attempts == 5


def test_duplicate_email_registration_returns_generic_response_without_session_or_extra_email(
    client: TestClient, monkeypatch: Any
) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    response = client.post(
        "/api/v1/auth/register",
        json=registration_payload(phone="+233201234567"),
    )
    assert response.status_code == 201
    assert response.json()["verification_required"] is True
    assert "obia_session" not in client.cookies
    assert len(capture.messages) == 1  # no extra email sent


def test_invalid_email_and_ghana_phone_and_weak_password_are_rejected(
    client: TestClient, monkeypatch: Any
) -> None:
    configure_email_auth(monkeypatch)
    invalid_email = client.post("/api/v1/auth/register", json=registration_payload(email="not-an-email"))
    invalid_phone = client.post("/api/v1/auth/register", json=registration_payload(phone="0301234567"))
    weak_password = client.post("/api/v1/auth/register", json=registration_payload(password="short"))
    assert invalid_email.status_code == 422
    assert invalid_phone.status_code == 422
    assert weak_password.status_code == 422


def test_registration_does_not_claim_success_when_email_delivery_fails(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    capture = EmailCapture()
    capture.fail = True
    configure_email_auth(monkeypatch, capture=capture)
    response = client.post("/api/v1/auth/register", json=registration_payload())
    assert response.status_code == 503
    assert "could not send" in response.json()["detail"].lower()
    with db_session_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0
        assert db.scalar(select(func.count()).select_from(AuthChallenge)) == 0


def test_correct_otp_verification_marks_email_verified_creates_session_and_consumes_code(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    account = verify_user(client, "amina@example.com", capture.last_code)
    assert account["email_verified"] is True
    assert account["email"] == "amina@example.com"
    assert "obia_session" in client.cookies
    assert client.get("/api/v1/auth/me").json()["email"] == "amina@example.com"

    reused = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "amina@example.com", "code": capture.last_code},
    )
    assert reused.status_code == 400
    with db_session_factory() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == "amina@example.com"))
        assert user is not None and user.email_verified is True and user.email_verified_at is not None
        challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.user_id == user.id))
        assert challenge is not None and challenge.consumed_at is not None


def test_incorrect_and_expired_otp_are_rejected(client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    incorrect = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "amina@example.com", "code": "00000000"},
    )
    assert incorrect.status_code == 400

    with db_session_factory() as db:
        challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.email == "amina@example.com"))
        assert challenge is not None
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        challenge.consumed_at = None
        challenge.attempts = 0
        db.commit()

    expired = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "amina@example.com", "code": capture.last_code},
    )
    assert expired.status_code == 400


def test_otp_attempt_exhaustion_blocks_further_attempts(client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"email": "amina@example.com", "code": "00000000"},
        )
    assert response.status_code in {400, 429}
    sixth = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "amina@example.com", "code": capture.last_code},
    )
    assert sixth.status_code in {400, 429}
    with db_session_factory() as db:
        challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.email == "amina@example.com"))
        assert challenge is not None and challenge.attempts >= 5


def test_resend_invalidates_previous_otp(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    old_code = capture.last_code
    # Bypass resend cooldown to test invalidation behavior.
    with db_session_factory() as db:
        challenge = db.scalar(select(AuthChallenge).where(AuthChallenge.email == "amina@example.com"))
        assert challenge is not None
        challenge.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.commit()
    resend = client.post("/api/v1/auth/resend-email-verification", json={"email": "amina@example.com"})
    assert resend.status_code == 200
    assert len(capture.messages) == 2
    new_code = capture.last_code
    assert new_code != old_code
    assert client.post("/api/v1/auth/verify-email", json={"email": "amina@example.com", "code": old_code}).status_code == 400
    assert client.post("/api/v1/auth/verify-email", json={"email": "amina@example.com", "code": new_code}).status_code == 200


def test_unverified_customer_cannot_log_in_and_verified_customer_can(client: TestClient, monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    unverified = client.post("/api/v1/auth/login", json=login_payload())
    assert unverified.status_code == 403
    assert "verify" in unverified.json()["detail"].lower()

    verify_user(client, "amina@example.com", capture.last_code)
    client.post("/api/v1/auth/logout", headers=csrf_header(client))
    verified = client.post("/api/v1/auth/login", json=login_payload())
    assert verified.status_code == 200
    assert verified.json()["login_required"] is True
    assert verified.json()["email"] == "amina@example.com"
    assert len(capture.messages) == 2
    completed = client.post(
        "/api/v1/auth/login/verify",
        json={
            "challenge_token": verified.json()["challenge_token"],
            "channel": "email",
            "code": capture.last_code,
        },
    )
    assert completed.status_code == 200
    assert completed.json()["email_verified"] is True
    assert "obia_session" in client.cookies


def test_password_recovery_and_reset_invalidate_sessions_and_require_new_password(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    verify_user(client, "amina@example.com", capture.last_code)
    old_session_cookie = client.cookies.get("obia_session")
    with db_session_factory() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == "amina@example.com"))
        db.add(
            AuthSession(
                id="extra-session-to-invalidate",
                customer_id=user.customer_profile.id,
                csrf_token_hash=token_hash("csrf"),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        db.commit()

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"})
    assert forgot.status_code == 202
    recovery_code = capture.last_code
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "amina@example.com",
            "code": recovery_code,
            "new_password": "new-secure-customer-pass-2026",
        },
    )
    assert reset.status_code == 200

    # Old password/session no longer work; old cookie invalidated by deletion.
    assert client.post("/api/v1/auth/login", json=login_payload()).status_code == 401
    # If client still had old cookie, protected route should reject it.
    with db_session_factory() as db:
        assert db.get(AuthSession, token_hash(old_session_cookie)) is None if old_session_cookie else True
        assert db.get(AuthSession, "extra-session-to-invalidate") is None

    new_login = client.post(
        "/api/v1/auth/login",
        json=login_payload(password="new-secure-customer-pass-2026"),
    )
    assert new_login.status_code == 200


def test_old_otp_cannot_be_reused_after_password_reset(client: TestClient, monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    verify_user(client, "amina@example.com", capture.last_code)
    client.post("/api/v1/auth/logout", headers=csrf_header(client))
    assert client.post("/api/v1/auth/forgot-password", json={"email": "amina@example.com"}).status_code == 202
    code = capture.last_code
    assert client.post(
        "/api/v1/auth/reset-password",
        json={"email": "amina@example.com", "code": code, "new_password": "new-secure-customer-pass-2026"},
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/reset-password",
        json={"email": "amina@example.com", "code": code, "new_password": "another-secure-customer-pass-2026"},
    ).status_code == 400


def test_forgot_password_returns_generic_response_for_unknown_email(client: TestClient, monkeypatch: Any) -> None:
    capture = configure_email_auth(monkeypatch)
    response = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert response.status_code == 202
    assert "if an eligible account exists" in response.json()["message"].lower()
    assert capture.messages == []


def test_existing_customers_and_order_history_remain_intact(
    client: TestClient, db_session_factory: sessionmaker[Session], monkeypatch: Any
) -> None:
    configure_email_auth(monkeypatch)
    with db_session_factory() as db:
        user = User(
            phone="+233241234567",
            full_name="Legacy Customer",
            password_hash=password_hasher.hash("legacy-customer-password-2026"),
            phone_verified=True,
            email_verified=False,
            account_status="active",
        )
        customer = Customer(user=user)
        db.add(customer)
        db.flush()
        db.add(
            Order(
                reference="FLA-LEGACY001",
                customer_id=customer.id,
                account_owner_id=customer.id,
                recipient_phone="+233241234567",
                network_id="mtn",
                bundle_id="mtn-sample-1gb",
                amount=1,
                currency="GHS",
                status="pending_payment",
                idempotency_key_hash=secrets.token_hex(32),
                request_fingerprint=secrets.token_hex(32),
            )
        )
        db.commit()

    with db_session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Order).where(Order.reference == "FLA-LEGACY001")) == 1
        legacy = db.scalar(select(User).where(User.phone == "+233241234567"))
        assert legacy is not None and legacy.full_name == "Legacy Customer"


def test_authenticated_email_verified_order_is_owned_and_csrf_protected(client: TestClient, monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    verify_user(client, "amina@example.com", capture.last_code)
    payload = {
        "phone": "0241234567",
        "network_id": "mtn",
        "bundle_id": "mtn-sample-1gb",
    }
    key = secrets.token_urlsafe(24)
    no_csrf = client.post("/api/v1/orders", json=payload, headers={"Idempotency-Key": key})
    assert no_csrf.status_code == 403
    created = client.post("/api/v1/orders", json=payload, headers={**csrf_header(client), "Idempotency-Key": key})
    assert created.status_code == 201
    order = created.json()
    history = client.get("/api/v1/customers/me/orders")
    assert [item["reference"] for item in history.json()] == [order["reference"]]


def test_phone_verification_routes_remain_unavailable_without_sms_provider(client: TestClient, monkeypatch: Any) -> None:
    capture, _ = register_and_get_code(client, monkeypatch)
    verify_user(client, "amina@example.com", capture.last_code)
    verify = client.post("/api/v1/auth/resend-verification", headers=csrf_header(client))
    assert verify.status_code == 503
    assert "unavailable" in verify.json()["detail"].lower()


def test_registration_rate_limited(client: TestClient, monkeypatch: Any) -> None:
    configure_email_auth(monkeypatch)
    monkeypatch.setenv("AUTH_RATE_LIMIT", "2")
    get_settings.cache_clear()
    statuses = [
        client.post("/api/v1/auth/register", json=registration_payload(phone=f"+23324{i:07d}", email=f"user{i}@example.com")).status_code
        for i in range(3)
    ]
    assert statuses[2] == 429


def test_codespaces_frontend_origin_is_allowed_only_in_development(
    client: TestClient, monkeypatch: Any
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    codespaces_origin = "https://kind-codespace-5173.app.github.dev"
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": codespaces_origin},
        json=login_payload(email="nobody@example.com"),
    )
    assert response.status_code == 401

    rejected = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://attacker.example"},
        json=login_payload(email="nobody@example.com"),
    )
    assert rejected.status_code == 403

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    get_settings.cache_clear()
    production_rejected = client.post(
        "/api/v1/auth/login",
        headers={"Origin": codespaces_origin},
        json=login_payload(email="nobody@example.com"),
    )
    assert production_rejected.status_code == 403
