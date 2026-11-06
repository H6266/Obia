import pytest
from pydantic import ValidationError

from app.schemas.customer import CustomerPhone


@pytest.mark.parametrize(
    ("phone", "normalized"),
    [
        ("0241234567", "+233241234567"),
        ("541234567", "+233541234567"),
        ("+233 24 123 4567", "+233241234567"),
        ("233201234567", "+233201234567"),
    ],
)
def test_valid_ghana_mobile_numbers_are_normalized(phone: str, normalized: str) -> None:
    assert CustomerPhone(phone=phone).phone == normalized


@pytest.mark.parametrize(
    "phone",
    ["", "123", "020123456", "02412345678", "0301234567", "+1 202 555 0100"],
)
def test_invalid_ghana_mobile_numbers_are_rejected(phone: str) -> None:
    with pytest.raises(ValidationError):
        CustomerPhone(phone=phone)


def test_unknown_network_does_not_create_order(client) -> None:
    response = client.post(
        "/api/v1/orders",
        json={
            "phone": "0241234567",
            "network_id": "unknown",
            "bundle_id": "mtn-sample-1gb",
        },
    )
    assert response.status_code == 404
