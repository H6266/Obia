from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Bundle
from app.schemas.bundle import BundleRead

router = APIRouter(tags=["bundles"])


@router.get("/networks/{network_id}/bundles", response_model=list[BundleRead])
def list_bundles(network_id: str, db: Session = Depends(get_db)) -> list[Bundle]:
    return list(
        db.scalars(
            select(Bundle)
            .where(Bundle.network_id == network_id, Bundle.is_available.is_(True))
            .order_by(Bundle.size_gb)
        ).all()
    )


@router.get("/bundles/{bundle_id}", response_model=BundleRead)
def get_bundle(bundle_id: str, db: Session = Depends(get_db)) -> Bundle:
    bundle = db.get(Bundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bundle not found.")
    return bundle
