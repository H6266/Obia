from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import Order
from app.models.order import OrderStatus
from app.schemas.customer import CustomerPhone


class OrderCreate(CustomerPhone):
    network_id: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9-]+$")
    bundle_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")


class OrderRead(BaseModel):
    reference: str
    amount: Decimal
    currency: str
    network_id: str
    network: str
    bundle_id: str
    bundle: str
    customer_phone: str
    status: OrderStatus
    created_at: datetime
    is_sample: bool

    model_config = ConfigDict(from_attributes=True)


def serialize_order(order: Order) -> OrderRead:
    return OrderRead(
        reference=order.reference,
        amount=order.amount,
        currency=order.currency,
        network_id=order.network_id,
        network=order.network.name,
        bundle_id=order.bundle_id,
        bundle=order.bundle.name,
        customer_phone=f"••• ••• {order.recipient_phone[-3:]}",
        status=order.status,
        created_at=order.created_at,
        is_sample=order.bundle.is_sample,
    )
