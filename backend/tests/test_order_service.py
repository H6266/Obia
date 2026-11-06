import pytest
from sqlalchemy.orm import Session

from app.models import Bundle, Customer, Network, Order, OrderStatus
from app.services.order_service import InvalidStatusTransition, transition_order_status


def test_invalid_status_transition_is_rejected(client) -> None:
    from app.core.database import get_db

    db: Session = next(iter(client.app.dependency_overrides[get_db]()))
    try:
        customer = Customer(phone="+233241234567")
        db.add(customer)
        db.flush()
        db.add(
            Order(
                reference="FLA-test-reference",
                customer_id=customer.id,
                recipient_phone=customer.phone,
                bundle_id="mtn-sample-1gb",
                network_id="mtn",
                amount=1,
                currency="GHS",
                status=OrderStatus.PENDING_PAYMENT,
            )
        )
        db.commit()
        with pytest.raises(InvalidStatusTransition):
            transition_order_status(db, "FLA-test-reference", OrderStatus.COMPLETED)
    finally:
        db.close()
