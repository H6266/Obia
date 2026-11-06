import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.core.security import token_hash
from app.models import AuthSession, Customer, User


def registration_payload(**overrides: str) -> dict[str, str]:
    return {
        "full_name": "Amina Mensah",
        "phone": "+233 24 123 4567",
        "password": "secure-customer-pass-2026",
        **overrides,
    }


def csrf_header(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_registration_creates_hashed_active_unverified_account_and_session(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    response = client.post("/api/v1/auth/register", json=registration_payload())
    assert response.status_code == 201
    account = response.json()
    assert account["full_name"] == "Amina Mensah"
    assert account["phone"] == "+233241234567"
    assert account["phone_verified"] is False
    assert account["account_status"] == "active"
    assert "falaaa_session=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]

    with db_session_factory() as db:
        customer = db.scalar(
            select(Customer).join(User).where(User.phone == account["phone"])
        )
        assert customer is not None
        assert customer.user.password_hash != registration_payload()["password"]
        assert customer.user.password_hash.startswith("$argon2id$")
        assert client.get("/api/v1/auth/me").json()["id"] == account["id"]


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/auth/register", json=registration_payload()).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=registration_payload())
    assert duplicate.status_code == 409


def test_invalid_phone_and_weak_password_are_rejected(client: TestClient) -> None:
    invalid_phone = client.post(
        "/api/v1/auth/register",
        json=registration_payload(phone="0301234567"),
    )
    weak_password = client.post(
        "/api/v1/auth/register",
        json=registration_payload(password="short"),
    )
    assert invalid_phone.status_code == 422
    assert weak_password.status_code == 422


def test_login_uses_generic_errors_and_sets_session(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    valid = client.post(
        "/api/v1/auth/login",
        json={"phone": "0241234567", "password": registration_payload()["password"]},
    )
    invalid = client.post(
        "/api/v1/auth/login",
        json={"phone": "0241234567", "password": "incorrect-customer-password"},
    )
    assert valid.status_code == 200
    assert "HttpOnly" in valid.headers["set-cookie"]
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Phone number or password is incorrect."


def test_private_profile_history_and_session_persist_across_requests(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/customers/me/orders").status_code == 401
    client.post("/api/v1/auth/register", json=registration_payload())
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/customers/me/orders").json() == []
    assert client.get("/api/v1/auth/me").status_code == 200


def test_authenticated_order_is_owned_and_csrf_protected(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    payload = {
        "phone": "0241234567",
        "network_id": "mtn",
        "bundle_id": "mtn-sample-1gb",
    }
    key = secrets.token_urlsafe(24)
    no_csrf = client.post(
        "/api/v1/orders",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert no_csrf.status_code == 403

    created = client.post(
        "/api/v1/orders",
        json=payload,
        headers={**csrf_header(client), "Idempotency-Key": key},
    )
    assert created.status_code == 201
    order = created.json()
    history = client.get("/api/v1/customers/me/orders")
    assert [item["reference"] for item in history.json()] == [order["reference"]]
    assert order["customer_phone"].endswith("567")


def test_one_customer_cannot_see_another_customers_order_history(
    client: TestClient,
) -> None:
    legacy_phone = "0241234567"
    legacy_order = client.post(
        "/api/v1/orders",
        json={
            "phone": legacy_phone,
            "network_id": "mtn",
            "bundle_id": "mtn-sample-1gb",
        },
        headers={"Idempotency-Key": secrets.token_urlsafe(24)},
    )
    assert legacy_order.status_code == 201
    client.post("/api/v1/auth/register", json=registration_payload())
    assert client.get("/api/v1/customers/me/orders").json() == []
    payload = {
        "phone": "0241234567",
        "network_id": "mtn",
        "bundle_id": "mtn-sample-1gb",
    }
    created = client.post(
        "/api/v1/orders",
        json=payload,
        headers={**csrf_header(client), "Idempotency-Key": secrets.token_urlsafe(24)},
    )
    assert created.status_code == 201
    client.post("/api/v1/auth/logout", headers=csrf_header(client))

    second_account = registration_payload(
        full_name="Kojo Owusu",
        phone="0201234567",
    )
    assert client.post("/api/v1/auth/register", json=second_account).status_code == 201
    assert client.get("/api/v1/customers/me/orders").json() == []


def test_logout_invalidates_database_session_and_clears_cookies(
    client: TestClient, db_session_factory: sessionmaker[Session]
) -> None:
    client.post("/api/v1/auth/register", json=registration_payload())
    session_cookie = client.cookies.get("falaaa_session")
    response = client.post("/api/v1/auth/logout", headers=csrf_header(client))
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    with db_session_factory() as db:
        assert session_cookie is not None
        assert db.get(AuthSession, token_hash(session_cookie)) is None


def test_password_recovery_and_phone_verification_do_not_claim_provider_success(
    client: TestClient,
) -> None:
    recovery = client.post(
        "/api/v1/auth/forgot-password",
        json={"phone": "0241234567"},
    )
    assert recovery.status_code == 503
    assert "unavailable" in recovery.json()["detail"].lower()
    client.post("/api/v1/auth/register", json=registration_payload())
    verify = client.post(
        "/api/v1/auth/resend-verification",
        headers=csrf_header(client),
    )
    assert verify.status_code == 503
    assert "unavailable" in verify.json()["detail"].lower()


def test_authentication_routes_are_rate_limited(client: TestClient) -> None:
    statuses = [
        client.post(
            "/api/v1/auth/forgot-password",
            json={"phone": "0241234567"},
        ).status_code
        for _ in range(11)
    ]
    assert statuses[:10] == [503] * 10
    assert statuses[10] == 429
