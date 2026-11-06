from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import optional_customer, require_csrf_for_session
from app.models import Customer, Order
from app.schemas.order import OrderCreate, OrderRead, serialize_order
from app.services.order_service import IdempotencyConflict, create_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf_for_session)],
)
def submit_order(
    request: OrderCreate,
    idempotency_key: str = Header(
        alias="Idempotency-Key", min_length=16, max_length=128
    ),
    db: Session = Depends(get_db),
    customer: Customer | None = Depends(optional_customer),
) -> OrderRead:
    try:
        order = create_order(db, request, idempotency_key, customer)
        return serialize_order(order)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except IdempotencyConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/{reference}", response_model=OrderRead)
def get_order(reference: str, db: Session = Depends(get_db)) -> OrderRead:
    order = db.scalar(
        select(Order).where(Order.reference == reference).limit(1)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return serialize_order(order)
