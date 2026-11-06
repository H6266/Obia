import secrets
from typing import Any

from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.models import (
    AdminAuditLog,
    Bundle,
    CatalogueRevision,
    Customer,
    OrderEvent,
    RolePermission,
    StaffUser,
    User,
)
from app.services import email_service
from app.services.admin_security import (
    encrypt_totp_secret,
    new_totp_code,
    new_totp_secret,
    permissions_for,
)


def _configure_mfa(monkeypatch) -> str:
    key = Fernet.generate_key().decode()
    settings = Settings(staff_mfa_encryption_key=key)
    monkeypatch.setattr("app.services.admin_security.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.admin_auth.get_settings", lambda: settings)
    return key


def _add_staff(
    factory: sessionmaker[Session],
    *,
    email: str = "owner@obia.test",
    role: str = "owner",
    secret: str | None = None,
) -> tuple[StaffUser, str]:
    secret = secret or new_totp_secret()
    with factory() as db:
        user = User(
            email=email,
            full_name="Test Owner",
            password_hash=PasswordHasher().hash("admin-test-password-2026"),
            account_status="active",
        )
        staff = StaffUser(
            user=user,
            role=role,
            status="active",
            mfa_enabled=True,
            mfa_secret_encrypted=encrypt_totp_secret(secret),
        )
        db.add(user)
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff, secret


def _login(client: TestClient, email: str, secret: str) -> TestClient:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": email,
            "password": "admin-test-password-2026",
            "totp_code": new_totp_code(secret),
        },
    )
    assert response.status_code == 200, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    return client


def _csrf(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/admin/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


class _EmailCapture:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send(self, *, to: str, content: Any) -> None:
        self.messages.append({"to": to, "text": content.text})

    @property
    def last_code(self) -> str:
        for token in self.messages[-1]["text"].split():
            if token.isdigit() and len(token) == 8:
                return token
        raise AssertionError("No OTP code found in sent message.")


def _configure_customer_email_auth(monkeypatch) -> _EmailCapture:
    get_settings.cache_clear()
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("EMAIL_FROM", "Obia <no-reply@obia.test>")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://obia.test")
    monkeypatch.setenv("OTP_HASH_SECRET", "test-otp-hash-secret-please-change")
    monkeypatch.setenv("AUTH_RATE_LIMIT", "1000")
    capture = _EmailCapture()
    monkeypatch.setattr(email_service, "send_email", capture.send)
    return capture


def _register_verified_customer(
    client: TestClient,
    monkeypatch,
    *,
    full_name: str = "Customer Name",
    email: str = "customer@example.com",
    phone: str = "0241234567",
    password: str = "secure-customer-pass-2026",
) -> dict[str, Any]:
    capture = _configure_customer_email_auth(monkeypatch)
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password": password,
        },
    )
    assert register.status_code == 201, register.text
    verify = client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": capture.last_code},
    )
    assert verify.status_code == 200, verify.text
    return verify.json()


def test_staff_login_requires_password_totp_and_prevents_code_replay(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _, secret = _add_staff(db_session_factory)
    assert client.get("/api/v1/admin/auth/me").status_code == 401
    _login(client, "owner@obia.test", secret)
    assert client.get("/api/v1/admin/auth/me").json()["role"] == "owner"
    replay = client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "owner@obia.test",
            "password": "admin-test-password-2026",
            "totp_code": new_totp_code(secret),
        },
    )
    assert replay.status_code == 401
    assert client.get("/api/v1/admin/auth/csrf").status_code == 200


def test_invitation_is_one_time_and_requires_mfa_before_staff_activation(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _add_staff(db_session_factory)
    with db_session_factory() as db:
        owner = db.scalar(
            select(StaffUser).join(User).where(User.email == "owner@obia.test")
        )
        from app.services.admin_security import decrypt_totp_secret
        owner_secret = decrypt_totp_secret(owner.mfa_secret_encrypted)
    _login(client, "owner@obia.test", owner_secret)

    invitation_response = client.post(
        "/api/v1/admin/staff/invitations",
        headers=_csrf(client),
        json={"email": "ops@obia.test", "full_name": "Ops Person", "role": "operations_manager"},
    )
    assert invitation_response.status_code == 201, invitation_response.text
    invitation_token = invitation_response.json()["invitation_token"]
    assert len(invitation_token) >= 32
    invitations = client.get("/api/v1/admin/staff/invitations").json()
    assert "invitation_token" not in invitations[0]

    accepted = client.post(
        "/api/v1/admin/auth/accept-invitation",
        json={"token": invitation_token, "password": "operations-password-2026"},
    )
    assert accepted.status_code == 200, accepted.text
    enrollment = accepted.json()
    with db_session_factory() as db:
        staff = db.scalar(
            select(StaffUser).join(User).where(User.email == "ops@obia.test")
        )
        assert staff is not None
        assert staff.status == "pending_mfa"
        assert staff.mfa_enabled is False
        assert staff.mfa_secret_encrypted != enrollment["totp_secret"]

    enabled = client.post(
        "/api/v1/admin/auth/confirm-enrollment",
        json={
            "enrollment_token": enrollment["enrollment_token"],
            "totp_code": new_totp_code(enrollment["totp_secret"]),
        },
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["mfa_enabled"] is True
    reused = client.post(
        "/api/v1/admin/auth/accept-invitation",
        json={"token": invitation_token, "password": "operations-password-2026"},
    )
    assert reused.status_code == 400


def test_owner_can_read_real_operations_but_revenue_is_not_fabricated(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _add_staff(db_session_factory)
    with db_session_factory() as db:
        owner = db.scalar(
            select(StaffUser).join(User).where(User.email == "owner@obia.test")
        )
        from app.services.admin_security import decrypt_totp_secret
        secret = decrypt_totp_secret(owner.mfa_secret_encrypted)
    _login(client, "owner@obia.test", secret)

    order_response = client.post(
        "/api/v1/orders",
        json={"phone": "0241234567", "network_id": "mtn", "bundle_id": "mtn-sample-1gb"},
        headers={"Idempotency-Key": secrets.token_urlsafe(24)},
    )
    assert order_response.status_code == 201
    reference = order_response.json()["reference"]
    dashboard = client.get("/api/v1/admin/dashboard?period=last_30_days")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_orders"] == 0
    assert dashboard.json()["sample_orders"] == 1
    assert dashboard.json()["requested_order_value"] == "0.00"
    assert dashboard.json()["revenue"] is None
    assert dashboard.json()["gross_profit"] is None

    order_list = client.get("/api/v1/admin/orders?page=1&page_size=1")
    assert order_list.status_code == 200, order_list.text
    assert order_list.json()["items"][0]["reference"] == reference
    order_detail = client.get(f"/api/v1/admin/orders/{reference}")
    assert order_detail.status_code == 200, order_detail.text
    assert order_detail.json()["timeline"][0]["event_type"] == "order.created"
    assert order_detail.json()["payment_status"] == "unverified"
    assert order_detail.json()["fulfillment_status"] == "not_started"
    with db_session_factory() as db:
        assert db.scalar(
            select(OrderEvent).where(OrderEvent.order_reference == reference)
        ) is not None
        audit = db.scalars(select(AdminAuditLog)).all()
        assert any(item.action == "order.viewed" for item in audit)


def test_role_permissions_and_customer_phone_masking_are_enforced(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _, secret = _add_staff(
        db_session_factory, email="support@obia.test", role="customer_support"
    )
    with db_session_factory() as db:
        assert "customers.read_sensitive" not in permissions_for("customer_support", db)
        assert "staff.manage" not in permissions_for("auditor", db)

    account = _register_verified_customer(client, monkeypatch)
    order = client.post(
        "/api/v1/orders",
        headers={
            "X-CSRF-Token": client.get("/api/v1/auth/csrf").json()["csrf_token"],
            "Idempotency-Key": secrets.token_urlsafe(24),
        },
        json={"phone": "0241234567", "network_id": "mtn", "bundle_id": "mtn-sample-1gb"},
    )
    assert order.status_code == 201

    _login(client, "support@obia.test", secret)
    assert client.get("/api/v1/admin/staff").status_code == 403
    assert client.get("/api/v1/admin/customers?phone=241234567").status_code == 403
    visible_orders = client.get("/api/v1/admin/orders").json()["items"]
    assert visible_orders
    assert "••" in visible_orders[0]["recipient_phone"]
    customers = client.get("/api/v1/admin/customers").json()["items"]
    assert customers
    assert "••" in customers[0]["phone"]


def test_customer_suspension_is_reasoned_audited_and_revokes_sessions(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _add_staff(db_session_factory)
    with db_session_factory() as db:
        owner = db.scalar(
            select(StaffUser).join(User).where(User.email == "owner@obia.test")
        )
        from app.services.admin_security import decrypt_totp_secret
        secret = decrypt_totp_secret(owner.mfa_secret_encrypted)
    _login(client, "owner@obia.test", secret)

    account = _register_verified_customer(
        client,
        monkeypatch,
        full_name="Suspended Customer",
        email="suspended@example.com",
    )
    customer_id = account["id"]
    csrf = client.get("/api/v1/admin/auth/csrf").json()["csrf_token"]
    response = client.post(
        f"/api/v1/admin/customers/{customer_id}/status",
        headers={"X-CSRF-Token": csrf},
        json={"status": "suspended", "reason": "Account review requested by support."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["account_status"] == "suspended"
    assert client.get("/api/v1/auth/me").status_code == 401
    with db_session_factory() as db:
        assert db.scalar(
            select(AdminAuditLog).where(
                AdminAuditLog.action == "customer.suspended",
                AdminAuditLog.resource_id == customer_id,
            )
        ) is not None
        customer = db.scalar(select(Customer).where(Customer.id == UUID(customer_id)))
        assert customer is not None
        assert customer.account_status == "suspended"


def test_catalogue_updates_are_permissioned_audited_and_preserve_order_price(
    client: TestClient,
    db_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    _configure_mfa(monkeypatch)
    _add_staff(db_session_factory)
    with db_session_factory() as db:
        owner = db.scalar(
            select(StaffUser).join(User).where(User.email == "owner@obia.test")
        )
        from app.services.admin_security import decrypt_totp_secret

        secret = decrypt_totp_secret(owner.mfa_secret_encrypted)
    _login(client, "owner@obia.test", secret)
    created = client.post(
        "/api/v1/orders",
        headers={"Idempotency-Key": secrets.token_urlsafe(24)},
        json={"phone": "0241234567", "network_id": "mtn", "bundle_id": "mtn-sample-1gb"},
    )
    assert created.status_code == 201
    reference = created.json()["reference"]

    updated = client.patch(
        "/api/v1/admin/catalogue/bundles/mtn-sample-1gb",
        headers=_csrf(client),
        json={"amount": "2.50", "is_available": False, "reason": "Supplier pricing changed"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == "2.50"
    assert updated.json()["is_available"] is False
    assert client.get("/api/v1/networks/mtn/bundles").json() == []
    assert client.get(f"/api/v1/orders/{reference}").json()["amount"] == "1.00"

    history = client.get("/api/v1/admin/catalogue/bundles/mtn-sample-1gb/history")
    assert history.status_code == 200, history.text
    assert history.json()[0]["previous_value"]["amount"] == "1.00"
    assert history.json()[0]["new_value"]["amount"] == "2.50"
    with db_session_factory() as db:
        assert db.scalar(
            select(CatalogueRevision).where(
                CatalogueRevision.bundle_id == "mtn-sample-1gb"
            )
        ) is not None
        bundle = db.get(Bundle, "mtn-sample-1gb")
        assert bundle.amount == 2.5


def test_permissions_are_read_from_database(client, db_session_factory, monkeypatch) -> None:
    _configure_mfa(monkeypatch)
    _, secret = _add_staff(
        db_session_factory, email="ops@obia.test", role="operations_manager"
    )
    _login(client, "ops@obia.test", secret)
    with db_session_factory() as db:
        db.query(RolePermission).filter_by(
            role_name="operations_manager", permission_code="orders.read"
        ).delete()
        db.commit()
    assert client.get("/api/v1/admin/orders").status_code == 403
