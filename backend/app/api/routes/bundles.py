from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Bundle, Network
from app.schemas.bundle import BundleRead

router = APIRouter(tags=["bundles"])


@router.get("/networks/{network_id}/bundles", response_model=list[BundleRead])
def list_bundles(network_id: str, db: Session = Depends(get_db)) -> list[Bundle]:
    network = db.get(Network, network_id)
    if network is None or not network.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Network not found.")
    return list(
        db.scalars(
            select(Bundle)
            .options(joinedload(Bundle.network))
            .where(Bundle.network_id == network_id, Bundle.is_available.is_(True))
            .order_by(Bundle.size_gb)
        ).all()
    )


@router.get("/bundles/{bundle_id}", response_model=BundleRead)
def get_bundle(bundle_id: str, db: Session = Depends(get_db)) -> Bundle:
    bundle = db.scalar(
        select(Bundle)
        .options(joinedload(Bundle.network))
        .where(
            Bundle.id == bundle_id,
            Bundle.is_available.is_(True),
            Network.is_active.is_(True),
        )
        .join(Network)
    )
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found.")
    return bundle
