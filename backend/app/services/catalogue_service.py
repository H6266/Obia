from fastapi import Request
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Bundle, CatalogueRevision, Network, StaffUser
from app.schemas.admin import BundleUpdateRequest
from app.services.admin_security import record_audit


def _bundle_values(bundle: Bundle) -> dict:
    return {
        "name": bundle.name,
        "size_gb": str(bundle.size_gb),
        "amount": str(bundle.amount),
        "currency": bundle.currency,
        "category": bundle.category,
        "validity_days": bundle.validity_days,
        "is_available": bundle.is_available,
    }


def update_bundle(
    db: Session,
    bundle: Bundle,
    payload: BundleUpdateRequest,
    actor: StaffUser,
    request: Request,
) -> Bundle:
    previous = _bundle_values(bundle)
    for field in payload.changed_fields():
        value = getattr(payload, field)
        if field in {"amount", "size_gb"}:
            value = Decimal(value)
        setattr(bundle, field, value)
    current = _bundle_values(bundle)
    db.add(
        CatalogueRevision(
            bundle_id=bundle.id,
            changed_by_id=actor.id,
            previous_value=previous,
            new_value=current,
            reason=payload.reason,
        )
    )
    record_audit(
        db,
        request,
        actor,
        action="catalogue.bundle.updated",
        resource_type="bundle",
        resource_id=bundle.id,
        previous_value=previous,
        new_value=current,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(bundle)
    return bundle


def set_network_active(
    db: Session,
    network: Network,
    *,
    is_active: bool,
    reason: str,
    actor: StaffUser,
    request: Request,
) -> Network:
    previous = {"is_active": network.is_active}
    network.is_active = is_active
    record_audit(
        db,
        request,
        actor,
        action="catalogue.network.status_changed",
        resource_type="network",
        resource_id=network.id,
        previous_value=previous,
        new_value={"is_active": network.is_active},
        reason=reason,
    )
    db.commit()
    db.refresh(network)
    return network
