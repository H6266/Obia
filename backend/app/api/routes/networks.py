from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Network
from app.schemas.network import NetworkRead

router = APIRouter(prefix="/networks", tags=["networks"])


@router.get("", response_model=list[NetworkRead])
def list_networks(db: Session = Depends(get_db)) -> list[Network]:
    return list(db.scalars(select(Network).order_by(Network.id)).all())
