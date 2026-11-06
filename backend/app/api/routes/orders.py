from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Order
from app.schemas.order import OrderCreate, OrderRead, serialize_order
from app.services.order_service import create_order

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def submit_order(request: OrderCreate, db: Session = Depends(get_db)) -> OrderRead:
    try:
        return serialize_order(create_order(db, request))
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{reference}", response_model=OrderRead)
def get_order(reference: str, db: Session = Depends(get_db)) -> OrderRead:
    order = db.scalar(
        select(Order).where(Order.reference == reference).limit(1)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return serialize_order(order)
