import hashlib
import json
import secrets
from typing import Protocol

from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Bundle, Customer, Network, Order, OrderEvent, OrderStatus, User
from app.core.security import token_hash
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


class IdempotencyConflict(Exception):
    pass


def _existing_idempotent_order(
    db: Session, key_hash: str, fingerprint: str
) -> Order | None:
    existing = db.scalar(
        select(Order).where(Order.idempotency_key_hash == key_hash)
    )
    if existing is not None and existing.request_fingerprint != fingerprint:
        raise IdempotencyConflict("The idempotency key was already used for a different request.")
    return existing


def create_order(
    db: Session,
    request: OrderCreate,
    idempotency_key: str,
    owner: Customer | None = None,
) -> Order:
    phone = normalize_ghana_phone(request.phone)
    key_hash = token_hash(idempotency_key)
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "bundle_id": request.bundle_id,
                "network_id": request.network_id,
                "owner_id": str(owner.id) if owner else None,
                "phone": phone,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    existing = _existing_idempotent_order(db, key_hash, fingerprint)
    if existing is not None:
        return existing

    network = db.get(Network, request.network_id)
    if network is None or not network.is_active:
        raise LookupError("Unknown network.")

    bundle = db.get(Bundle, request.bundle_id)
    if bundle is None or bundle.network_id != network.id or not bundle.is_available:
        raise LookupError("Bundle is not available for the selected network.")

    customer = owner or db.scalar(
        select(Customer)
        .outerjoin(User, Customer.user_id == User.id)
        .where(or_(Customer.guest_phone == phone, User.phone == phone))
    )
    if customer is None:
        customer = Customer(guest_phone=phone)
        db.add(customer)
        db.flush()

    order = Order(
        reference=f"FLA-{secrets.token_urlsafe(18)}",
        customer_id=customer.id,
        account_owner_id=owner.id if owner else None,
        recipient_phone=phone,
        bundle_id=bundle.id,
        network_id=network.id,
        amount=bundle.amount,
        currency=bundle.currency,
        status=OrderStatus.PENDING_PAYMENT,
        idempotency_key_hash=key_hash,
        request_fingerprint=fingerprint,
    )
    db.add(order)
    db.add(
        OrderEvent(
            order_reference=order.reference,
            event_type="order.created",
            previous_status=None,
            new_status=OrderStatus.PENDING_PAYMENT.value,
            actor_type="customer" if owner else "guest",
            actor_label="authenticated customer" if owner else "guest checkout",
            details={"payment_status": "unverified", "fulfillment_status": "not_started"},
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _existing_idempotent_order(db, key_hash, fingerprint)
        if existing is None:
            raise
        return existing
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
    previous_status = order.status
    order.status = new_status
    db.add(
        OrderEvent(
            order_reference=order.reference,
            event_type="order.status_changed",
            previous_status=previous_status.value,
            new_status=new_status.value,
            actor_type="system",
            actor_label="order service",
        )
    )
    db.commit()
    db.refresh(order)
    return order


class PaymentService(Protocol):
    def initiate_payment(self, order: Order) -> str:
        """Return a real provider reference after payment initiation."""


class FulfillmentService(Protocol):
    def submit_fulfillment(self, order: Order, *, idempotency_key: str) -> str:
        """Return a supplier reference after a real fulfillment submission."""
