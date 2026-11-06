import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import require_allowed_origin
from app.models import (
    AdminAuditLog,
    AuthSession,
    Bundle,
    CatalogueRevision,
    Customer,
    Order,
    OrderEscalation,
    OrderEvent,
    OrderStatus,
    OrderSupportNote,
    Network,
    StaffUser,
    User,
)
from app.schemas.admin import (
    AdminAuditRead,
    AdminCustomerRead,
    AdminCustomerDetail,
    BundleUpdateRequest,
    CatalogueRevisionRead,
    AdminOrderDetail,
    AdminOrderRead,
    CustomerStatusRequest,
    DashboardMetrics,
    NetworkStatusRequest,
    OrderEscalationRead,
    OrderEscalationRequest,
    OrderNoteRead,
    OrderNoteRequest,
    OrderTimelineEvent,
)
from app.services.admin_security import (
    permissions_for,
    record_audit,
    require_permission,
    require_staff_csrf,
)
from app.schemas.bundle import BundleRead
from app.schemas.network import NetworkRead
from app.services.catalogue_service import set_network_active, update_bundle

router = APIRouter(prefix="/admin", tags=["admin operations"])
PAGE_SIZE_MAX = 100


def _mask_phone(phone: str) -> str:
    return f"+233 •• ••• {phone[-3:]}" if len(phone) >= 3 else "•••"


def _order_read(order: Order, staff: StaffUser, db: Session) -> AdminOrderRead:
    reveal = "customers.read_sensitive" in permissions_for(staff.role, db)
    phone = order.customer.phone if order.customer else order.recipient_phone
    recipient_phone = order.recipient_phone
    return AdminOrderRead(
        reference=order.reference,
        customer_name=(order.customer.full_name or None) if order.customer else None,
        customer_phone=phone if reveal else _mask_phone(phone),
        recipient_phone=recipient_phone if reveal else _mask_phone(recipient_phone),
        network_id=order.network_id,
        network=order.network.name,
        bundle_id=order.bundle_id,
        bundle=order.bundle.name,
        amount=order.amount,
        currency=order.currency,
        order_status=order.status.value,
        payment_status=order.payment_status,
        fulfillment_status=order.fulfillment_status,
        supplier=None,
        supplier_reference=None,
        agent=None,
        created_at=order.created_at,
        updated_at=order.updated_at,
        is_sample=order.bundle.is_sample,
    )


def _order_query():
    return select(Order).options(
        joinedload(Order.customer).joinedload(Customer.user),
        joinedload(Order.bundle),
        joinedload(Order.network),
    )


def _date_range(
    period: str,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime]:
    today = datetime.now(timezone.utc).date()
    if period == "custom":
        if start_date is None or end_date is None or start_date > end_date:
            raise HTTPException(status_code=422, detail="A valid custom start_date and end_date are required.")
        start, end = start_date, end_date
    elif period == "today":
        start = end = today
    elif period == "yesterday":
        start = end = today - timedelta(days=1)
    elif period == "last_7_days":
        start, end = today - timedelta(days=6), today
    elif period == "last_30_days":
        start, end = today - timedelta(days=29), today
    elif period == "this_month":
        start, end = today.replace(day=1), today
    elif period == "last_month":
        last_day = today.replace(day=1) - timedelta(days=1)
        start, end = last_day.replace(day=1), last_day
    else:
        raise HTTPException(status_code=422, detail="Unsupported dashboard period.")
    return (
        datetime.combine(start, time.min, tzinfo=timezone.utc),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(
    request: Request,
    period: str = "last_30_days",
    start_date: date | None = None,
    end_date: date | None = None,
    staff: StaffUser = Depends(require_permission("dashboard.read")),
    db: Session = Depends(get_db),
) -> DashboardMetrics:
    start, end = _date_range(period, start_date, end_date)
    predicates = [Order.created_at >= start, Order.created_at < end]
    operational = select(Order).join(Bundle, Bundle.id == Order.bundle_id).where(
        *predicates, Bundle.is_sample.is_(False)
    )
    base = operational.subquery()
    total_orders = db.scalar(select(func.count()).select_from(base)) or 0
    successful = db.scalar(
        select(func.count()).select_from(base).where(base.c.status == "completed")
    ) or 0
    failed = db.scalar(
        select(func.count()).select_from(base).where(base.c.status == "failed")
    ) or 0
    pending = db.scalar(
        select(func.count()).select_from(base).where(
            base.c.status.in_(
                ["pending_payment", "payment_processing", "fulfillment_pending", "processing"]
            )
        )
    ) or 0
    sample_orders = db.scalar(
        select(func.count(Order.reference))
        .join(Bundle, Bundle.id == Order.bundle_id)
        .where(*predicates, Bundle.is_sample.is_(True))
    ) or 0
    requested_value = db.scalar(
        select(func.coalesce(func.sum(base.c.amount), 0))
    ) or Decimal("0.00")
    daily = db.execute(
        select(
            func.date(base.c.created_at).label("day"),
            func.count().label("orders"),
            func.coalesce(func.sum(base.c.amount), 0).label("requested_value"),
        )
        .group_by(func.date(base.c.created_at))
        .order_by(func.date(base.c.created_at))
    ).all()
    statuses = db.execute(
        select(base.c.status, func.count()).group_by(base.c.status).order_by(base.c.status)
    ).all()
    network_rows = db.execute(
        select(Network.name, func.count(Order.reference))
        .join(Bundle, Bundle.id == Order.bundle_id)
        .join(Network, Network.id == Order.network_id)
        .where(*predicates, Bundle.is_sample.is_(False))
        .group_by(Network.name)
        .order_by(Network.name)
    ).all()
    network_data = [{"network": name, "orders": count} for name, count in network_rows]

    metrics = DashboardMetrics(
        start=start,
        end=end,
        total_orders=total_orders,
        successful_orders=successful,
        pending_orders=pending,
        failed_orders=failed,
        sample_orders=sample_orders,
        active_customers=db.scalar(
            select(func.count(Customer.id))
            .join(User, Customer.user_id == User.id)
            .where(User.account_status == "active")
        ) or 0,
        requested_order_value=requested_value,
        revenue=None,
        net_revenue=None,
        gross_profit=None,
        available_inventory_units=None,
        reserved_inventory_units=None,
        delivered_inventory_units=None,
        daily_orders=[
            {"date": str(row.day), "orders": row.orders, "requested_value": float(row.requested_value)}
            for row in daily
        ],
        orders_by_network=network_data,
        orders_by_status=[{"status": name, "orders": count} for name, count in statuses],
        data_availability={
            "revenue": "Unavailable: no verified payment records exist.",
            "profit": "Unavailable: supplier acquisition costs are not recorded.",
            "inventory": "Unavailable: inventory management is a later implementation stage.",
            "requested_order_value": "Sum of order request amounts; not collected revenue.",
            "sample_orders": "Sample-catalogue orders are counted separately and excluded from business metrics.",
        },
    )
    record_audit(
        db, request, staff,
        action="dashboard.viewed", resource_type="dashboard", resource_id=period,
    )
    db.commit()
    return metrics


@router.get("/catalogue/networks", response_model=list[NetworkRead])
def list_catalogue_networks(
    staff: StaffUser = Depends(require_permission("catalogue.read")),
    db: Session = Depends(get_db),
) -> list[Network]:
    del staff
    return list(db.scalars(select(Network).order_by(Network.id)).all())


@router.patch(
    "/catalogue/networks/{network_id}/status",
    response_model=NetworkRead,
    dependencies=[Depends(require_staff_csrf), Depends(require_allowed_origin)],
)
def change_network_status(
    network_id: str,
    payload: NetworkStatusRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("catalogue.manage")),
    db: Session = Depends(get_db),
) -> Network:
    network = db.get(Network, network_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Network not found.")
    return set_network_active(
        db,
        network,
        is_active=payload.is_active,
        reason=payload.reason,
        actor=staff,
        request=request,
    )


@router.get("/catalogue/bundles")
def list_catalogue_bundles(
    network_id: str | None = None,
    search: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=PAGE_SIZE_MAX),
    staff: StaffUser = Depends(require_permission("catalogue.read")),
    db: Session = Depends(get_db),
) -> dict:
    del staff
    query = select(Bundle).options(joinedload(Bundle.network))
    if network_id:
        query = query.where(Bundle.network_id == network_id)
    if search.strip():
        term = search.strip()[:100]
        query = query.where(Bundle.name.ilike(f"%{term}%"))
    total = db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    bundles = db.scalars(
        query.order_by(Bundle.network_id, Bundle.size_gb)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    return {
        "items": [BundleRead.model_validate(bundle) for bundle in bundles],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.patch(
    "/catalogue/bundles/{bundle_id}",
    response_model=BundleRead,
    dependencies=[Depends(require_staff_csrf), Depends(require_allowed_origin)],
)
def change_bundle(
    bundle_id: str,
    payload: BundleUpdateRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("catalogue.manage")),
    db: Session = Depends(get_db),
) -> Bundle:
    bundle = db.get(Bundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    return update_bundle(db, bundle, payload, staff, request)


@router.get(
    "/catalogue/bundles/{bundle_id}/history",
    response_model=list[CatalogueRevisionRead],
)
def bundle_catalogue_history(
    bundle_id: str,
    staff: StaffUser = Depends(require_permission("catalogue.read")),
    db: Session = Depends(get_db),
) -> list[CatalogueRevisionRead]:
    del staff
    if db.get(Bundle, bundle_id) is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    rows = db.execute(
        select(CatalogueRevision, User.email)
        .join(StaffUser, StaffUser.id == CatalogueRevision.changed_by_id)
        .join(User, User.id == StaffUser.user_id)
        .where(CatalogueRevision.bundle_id == bundle_id)
        .order_by(CatalogueRevision.created_at.desc())
        .limit(100)
    ).all()
    return [
        CatalogueRevisionRead(
            id=revision.id,
            bundle_id=revision.bundle_id,
            actor_email=email,
            previous_value=revision.previous_value,
            new_value=revision.new_value,
            reason=revision.reason,
            created_at=revision.created_at,
        )
        for revision, email in rows
    ]


@router.get("/orders")
def list_orders(
    request: Request,
    search: str = "",
    status: str | None = None,
    network_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    sort_by: str = Query(default="created_at", pattern="^(created_at|amount|reference)$"),
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=PAGE_SIZE_MAX),
    staff: StaffUser = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> dict:
    query = _order_query()
    predicates = []
    if search.strip():
        term = search.strip()[:100]
        search_predicates = [Order.reference.ilike(f"%{term}%")]
        if term.isdigit() and "customers.read_sensitive" in permissions_for(staff.role, db):
            phone_matches = (
                select(Customer.id)
                .outerjoin(User, Customer.user_id == User.id)
                .where(
                    or_(
                        Customer.guest_phone.ilike(f"%{term}%"),
                        User.phone.ilike(f"%{term}%"),
                    )
                )
            )
            search_predicates.append(Order.customer_id.in_(phone_matches))
            search_predicates.append(Order.recipient_phone.ilike(f"%{term}%"))
        predicates.append(or_(*search_predicates))
    if status:
        allowed = {item.value for item in OrderStatus}
        if status not in allowed:
            raise HTTPException(status_code=422, detail="Unknown order status.")
        predicates.append(Order.status == status)
    if network_id:
        predicates.append(Order.network_id == network_id)
    if start_date:
        predicates.append(Order.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
    if end_date:
        predicates.append(Order.created_at < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc))
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")
    if predicates:
        query = query.where(*predicates)
    sort_column = {
        "created_at": Order.created_at,
        "amount": Order.amount,
        "reference": Order.reference,
    }[sort_by]
    query = query.order_by(sort_column.asc() if sort_direction == "asc" else sort_column.desc())
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    orders = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    record_audit(
        db, request, staff, action="orders.listed", resource_type="order_collection",
        resource_id="filtered",
    )
    db.commit()
    return {
        "items": [_order_read(order, staff, db) for order in orders],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/orders/{reference}", response_model=AdminOrderDetail)
def order_detail(
    reference: str,
    request: Request,
    staff: StaffUser = Depends(require_permission("orders.read")),
    db: Session = Depends(get_db),
) -> AdminOrderDetail:
    order = db.scalar(_order_query().where(Order.reference == reference))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    notes = db.execute(
        select(OrderSupportNote, User.email)
        .join(StaffUser, StaffUser.id == OrderSupportNote.author_id)
        .join(User, User.id == StaffUser.user_id)
        .where(OrderSupportNote.order_reference == reference)
        .order_by(OrderSupportNote.created_at.asc())
    ).all()
    escalations = db.execute(
        select(OrderEscalation, User.email)
        .join(StaffUser, StaffUser.id == OrderEscalation.created_by_id)
        .join(User, User.id == StaffUser.user_id)
        .where(OrderEscalation.order_reference == reference)
        .order_by(OrderEscalation.created_at.asc())
    ).all()
    record_audit(
        db, request, staff, action="order.viewed", resource_type="order",
        resource_id=reference,
    )
    db.commit()
    return AdminOrderDetail(
        **_order_read(order, staff, db).model_dump(),
            timeline=[
                OrderTimelineEvent.model_validate(item)
                for item in db.scalars(
                    select(OrderEvent)
                    .where(OrderEvent.order_reference == reference)
                    .order_by(OrderEvent.created_at.asc())
                ).all()
            ],
        notes=[
            OrderNoteRead(
                id=note.id, order_reference=note.order_reference, author_email=email,
                note=note.note, created_at=note.created_at
            )
            for note, email in notes
        ],
        escalations=[
            OrderEscalationRead(
                id=item.id, created_by_email=email, reason=item.reason,
                status=item.status, created_at=item.created_at,
            )
            for item, email in escalations
        ],
    )


@router.post(
    "/orders/{reference}/notes",
    response_model=OrderNoteRead,
    status_code=201,
    dependencies=[Depends(require_staff_csrf), Depends(require_allowed_origin)],
)
def add_order_note(
    reference: str,
    payload: OrderNoteRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("orders.notes")),
    db: Session = Depends(get_db),
) -> OrderNoteRead:
    if db.get(Order, reference) is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    note = OrderSupportNote(
        id=uuid.uuid4(),
        order_reference=reference, author_id=staff.id, note=payload.note.strip()
    )
    db.add(note)
    record_audit(
        db, request, staff, action="order.note.added", resource_type="order",
        resource_id=reference, new_value={"note_id": str(note.id)},
    )
    db.commit()
    db.refresh(note)
    return OrderNoteRead(
        id=note.id, order_reference=note.order_reference, author_email=staff.email,
        note=note.note, created_at=note.created_at
    )


@router.post(
    "/orders/{reference}/escalations",
    response_model=OrderEscalationRead,
    status_code=201,
    dependencies=[Depends(require_staff_csrf), Depends(require_allowed_origin)],
)
def create_escalation(
    reference: str,
    payload: OrderEscalationRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("orders.manage")),
    db: Session = Depends(get_db),
) -> OrderEscalationRead:
    if db.get(Order, reference) is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    item = OrderEscalation(
        id=uuid.uuid4(),
        order_reference=reference, created_by_id=staff.id, reason=payload.reason.strip()
    )
    db.add(item)
    record_audit(
        db, request, staff, action="order.escalated", resource_type="order",
        resource_id=reference, new_value={"escalation_id": str(item.id), "status": item.status},
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    return OrderEscalationRead(
        id=item.id, created_by_email=staff.email, reason=item.reason,
        status=item.status, created_at=item.created_at,
    )


@router.get("/customers")
def list_customers(
    request: Request,
    search: str = "",
    phone: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=PAGE_SIZE_MAX),
    staff: StaffUser = Depends(require_permission("customers.read")),
    db: Session = Depends(get_db),
) -> dict:
    sensitive = "customers.read_sensitive" in permissions_for(staff.role, db)
    if phone and not sensitive:
        raise HTTPException(status_code=403, detail="You do not have permission to search customer phone numbers.")
    query = select(
        Customer,
        func.count(Order.reference).label("order_count"),
    ).outerjoin(User, Customer.user_id == User.id).outerjoin(
        Order, Order.account_owner_id == Customer.id
    ).options(joinedload(Customer.user)).group_by(Customer.id, User.id)
    if search.strip():
        term = search.strip()[:100]
        predicates = [
            User.full_name.ilike(f"%{term}%"),
            cast(Customer.id, String).ilike(f"%{term}%"),
            Customer.guest_phone.ilike(f"%{term}%"),
        ]
        if sensitive and term.isdigit():
            predicates.append(User.phone.ilike(f"%{term}%"))
        query = query.where(or_(*predicates))
    if phone:
        query = query.where(
            or_(
                User.phone.ilike(f"%{phone.strip()[:24]}%"),
                Customer.guest_phone.ilike(f"%{phone.strip()[:24]}%"),
            )
        )
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    rows = db.execute(
        query.order_by(Customer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    record_audit(
        db, request, staff, action="customers.listed",
        resource_type="customer_collection", resource_id="filtered",
    )
    db.commit()
    return {
        "items": [
            AdminCustomerRead(
                id=customer.id,
                full_name=customer.full_name,
                email=customer.email if sensitive else None,
                phone=customer.phone if sensitive else _mask_phone(customer.phone),
                phone_verified=customer.phone_verified,
                email_verified=customer.email_verified,
                account_status=customer.account_status,
                created_at=customer.created_at,
                order_count=order_count,
            )
            for customer, order_count in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/customers/{customer_id}", response_model=AdminCustomerDetail)
def customer_detail(
    customer_id: uuid.UUID,
    request: Request,
    staff: StaffUser = Depends(require_permission("customers.read")),
    db: Session = Depends(get_db),
) -> AdminCustomerDetail:
    customer = db.scalar(
        select(Customer)
        .options(joinedload(Customer.user))
        .where(Customer.id == customer_id)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    orders = db.scalars(
        _order_query()
        .where(Order.account_owner_id == customer.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    ).unique().all()
    references = [order.reference for order in orders]
    notes: list[OrderNoteRead] = []
    if references:
        note_rows = db.execute(
            select(OrderSupportNote, User.email)
            .join(StaffUser, StaffUser.id == OrderSupportNote.author_id)
            .join(User, User.id == StaffUser.user_id)
            .where(OrderSupportNote.order_reference.in_(references))
            .order_by(OrderSupportNote.created_at.desc())
        ).all()
        notes = [
            OrderNoteRead(
                id=note.id,
                order_reference=note.order_reference,
                author_email=email,
                note=note.note,
                created_at=note.created_at,
            )
            for note, email in note_rows
        ]
    record_audit(
        db, request, staff, action="customer.viewed", resource_type="customer",
        resource_id=str(customer.id),
    )
    db.commit()
    phone = customer.phone if "customers.read_sensitive" in permissions_for(staff.role, db) else _mask_phone(customer.phone)
    return AdminCustomerDetail(
        id=customer.id,
        full_name=customer.full_name,
        email=customer.email if "customers.read_sensitive" in permissions_for(staff.role, db) else None,
        phone=phone,
        phone_verified=customer.phone_verified,
        email_verified=customer.email_verified,
        account_status=customer.account_status,
        created_at=customer.created_at,
        order_count=len(orders),
        orders=[_order_read(order, staff, db) for order in orders],
        support_records=notes,
    )


@router.post(
    "/customers/{customer_id}/status",
    response_model=AdminCustomerRead,
    dependencies=[Depends(require_staff_csrf), Depends(require_allowed_origin)],
)
def set_customer_status(
    customer_id: uuid.UUID,
    payload: CustomerStatusRequest,
    request: Request,
    staff: StaffUser = Depends(require_permission("customers.manage")),
    db: Session = Depends(get_db),
) -> AdminCustomerRead:
    customer = db.scalar(
        select(Customer)
        .options(joinedload(Customer.user))
        .where(Customer.id == customer_id)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    if customer.user is None:
        raise HTTPException(
            status_code=409,
            detail="Guest customer records do not have accounts to suspend or reactivate.",
        )
    previous = {"account_status": customer.user.account_status}
    customer.user.account_status = payload.status
    if payload.status == "suspended":
        db.query(AuthSession).filter(AuthSession.customer_id == customer.id).delete(
            synchronize_session=False
        )
    record_audit(
        db,
        request,
        staff,
        action=f"customer.{payload.status}",
        resource_type="customer",
        resource_id=str(customer.id),
        previous_value=previous,
        new_value={"account_status": customer.user.account_status},
        reason=payload.reason.strip(),
    )
    db.commit()
    db.refresh(customer)
    order_count = db.scalar(
        select(func.count(Order.reference)).where(Order.account_owner_id == customer.id)
    ) or 0
    phone = customer.phone if "customers.read_sensitive" in permissions_for(staff.role, db) else _mask_phone(customer.phone)
    return AdminCustomerRead(
        id=customer.id,
        full_name=customer.full_name,
        email=customer.email if "customers.read_sensitive" in permissions_for(staff.role, db) else None,
        phone=phone,
        phone_verified=customer.phone_verified,
        email_verified=customer.email_verified,
        account_status=customer.account_status,
        created_at=customer.created_at,
        order_count=order_count,
    )


@router.get("/audit", response_model=list[AdminAuditRead])
def list_audit_logs(
    request: Request,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=PAGE_SIZE_MAX),
    staff: StaffUser = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
) -> list[AdminAuditRead]:
    del staff
    query = select(AdminAuditLog)
    if action:
        query = query.where(AdminAuditLog.action == action)
    if resource_type:
        query = query.where(AdminAuditLog.resource_type == resource_type)
    items = db.scalars(
        query.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    record_audit(
        db, request, staff, action="audit.viewed",
        resource_type="audit_collection", resource_id="filtered",
    )
    db.commit()
    return [AdminAuditRead.model_validate(item) for item in items]
