import secrets
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bundle, Customer, Network, Order, OrderStatus
from app.schemas.customer import normalize_ghana_phone
from app.schemas.order import OrderCreate

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_PAYMENT: {
        OrderStatus.PAYMENT_PROCESSING,
        OrderStatus.CANCELLED,
        OrderStatus.FAILED,
    },
    OrderStatus.PAYMENT_PROCESSING: {
        OrderStatus.PAID,
        OrderStatus.CANCELLED,
        OrderStatus.FAILED,
    },
    OrderStatus.PAID: {
        OrderStatus.FULFILLMENT_PENDING,
        OrderStatus.REFUNDED,
        OrderStatus.FAILED,
    },
    OrderStatus.FULFILLMENT_PENDING: {
        OrderStatus.PROCESSING,
        OrderStatus.REFUNDED,
        OrderStatus.FAILED,
    },
    OrderStatus.PROCESSING: {
        OrderStatus.COMPLETED,
        OrderStatus.REFUNDED,
        OrderStatus.FAILED,
    },
    OrderStatus.COMPLETED: {OrderStatus.REFUNDED},
    OrderStatus.FAILED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


class InvalidStatusTransition(Exception):
    pass


def create_order(db: Session, request: OrderCreate) -> Order:
    network = db.get(Network, request.network_id)
    if network is None:
        raise LookupError("Unknown network.")

    bundle = db.get(Bundle, request.bundle_id)
    if bundle is None or bundle.network_id != network.id or not bundle.is_available:
        raise LookupError("Bundle is not available for the selected network.")

    phone = normalize_ghana_phone(request.phone)
    customer = db.scalar(select(Customer).where(Customer.phone == phone))
    if customer is None:
        customer = Customer(phone=phone)
        db.add(customer)
        db.flush()

    order = Order(
        reference=f"FLA-{secrets.token_urlsafe(18)}",
        customer_id=customer.id,
        bundle_id=bundle.id,
        network_id=network.id,
        amount=bundle.amount,
        currency=bundle.currency,
        status=OrderStatus.PENDING_PAYMENT,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def transition_order_status(
    db: Session, reference: str, new_status: OrderStatus
) -> Order:
    order = db.get(Order, reference)
    if order is None:
        raise LookupError("Order not found.")
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise InvalidStatusTransition(
            f"Cannot transition an order from {order.status.value} to {new_status.value}."
        )
    order.status = new_status
    db.commit()
    db.refresh(order)
    return order


class PaymentService(Protocol):
    def initiate_payment(self, order: Order) -> str:
        """Return a real provider reference after payment initiation."""


class FulfillmentService(Protocol):
    def submit_fulfillment(self, order: Order, *, idempotency_key: str) -> str:
        """Return a supplier reference after a real fulfillment submission."""
