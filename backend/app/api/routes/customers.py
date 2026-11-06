from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import CustomerAuth
from app.models import Order
from app.schemas.order import OrderRead, serialize_order

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/me/orders", response_model=list[OrderRead])
def customer_order_history(
    customer: CustomerAuth, db: Session = Depends(get_db)
) -> list[OrderRead]:
    orders = db.scalars(
        select(Order)
        .options(
            selectinload(Order.bundle),
            selectinload(Order.network),
            selectinload(Order.customer),
        )
        .where(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    ).all()
    return [serialize_order(order) for order in orders]
