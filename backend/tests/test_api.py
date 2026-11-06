from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.main import app


def order_payload(**overrides: str) -> dict[str, str]:
    return {
        "phone": "+233 24 123 4567",
        "network_id": "mtn",
        "bundle_id": "mtn-sample-1gb",
        **overrides,
    }


def test_health_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_health_hides_database_errors_and_returns_service_unavailable(
    client: TestClient,
) -> None:
    def unavailable_db():
        class UnavailableSession:
            def execute(self, _statement):
                raise SQLAlchemyError("private database detail")

        yield UnavailableSession()

    app.dependency_overrides[get_db] = unavailable_db
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unreachable"}
    assert "private database detail" not in response.text


def test_catalogue_lists_supported_networks_and_demo_bundles(client: TestClient) -> None:
    networks = client.get("/api/v1/networks")
    bundles = client.get("/api/v1/networks/mtn/bundles")
    assert [network["id"] for network in networks.json()] == ["at", "mtn", "telecel"]
    assert bundles.status_code == 200
    assert bundles.json()[0]["is_sample"] is True


def test_unknown_bundle_returns_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/bundles/not-a-bundle").status_code == 404


def test_valid_order_is_persisted_pending_payment(client: TestClient) -> None:
    response = client.post("/api/v1/orders", json=order_payload())
    assert response.status_code == 201
    order = response.json()
    assert order["reference"].startswith("FLA-")
    assert float(order["amount"]) == 1
    assert order["network"] == "MTN"
    assert order["bundle"] == "1 GB sample bundle"
    assert order["status"] == "pending_payment"
    assert order["is_sample"] is True
    assert order["customer_phone"].endswith("567")
    assert client.get(f"/api/v1/orders/{order['reference']}").json() == order


def test_order_references_are_unique(client: TestClient) -> None:
    first = client.post("/api/v1/orders", json=order_payload()).json()["reference"]
    second = client.post(
        "/api/v1/orders",
        json=order_payload(phone="+233 20 123 4567"),
    ).json()["reference"]
    assert first != second


def test_invalid_phone_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/orders", json=order_payload(phone="0301234567"))
    assert response.status_code == 422


def test_unknown_network_and_bundle_are_rejected(client: TestClient) -> None:
    unknown_network = client.post(
        "/api/v1/orders",
        json=order_payload(network_id="unknown"),
    )
    unknown_bundle = client.post(
        "/api/v1/orders",
        json=order_payload(bundle_id="telecel-sample-1gb"),
    )
    assert unknown_network.status_code == 404
    assert unknown_bundle.status_code == 404


def test_unknown_order_reference_returns_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/orders/FLA-unknown").status_code == 404


def test_customer_history_requires_real_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/customers/me/orders")
    assert response.status_code == 401
    assert "authentication" in response.json()["detail"].lower()


def test_customer_history_cannot_be_queried_by_phone(client: TestClient) -> None:
    response = client.get("/api/v1/customers/0241234567/orders")
    assert response.status_code == 404


def test_public_users_cannot_mutate_order_status(client: TestClient) -> None:
    order = client.post("/api/v1/orders", json=order_payload()).json()
    response = client.patch(
        f"/api/v1/orders/{order['reference']}",
        json={"status": "completed"},
    )
    assert response.status_code == 405
