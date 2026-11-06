import uuid
from datetime import datetime
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

StaffRole = Literal[
    "super_admin",
    "operations_manager",
    "finance_manager",
    "customer_support",
    "inventory_officer",
    "agent_manager",
    "auditor",
]


class StaffLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    totp_code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class StaffLoginChallenge(BaseModel):
    login_required: bool = True
    challenge_token: str
    email: str
    phone_masked: str | None = None
    channels: list[str]
    message: str


class StaffLoginVerifyRequest(BaseModel):
    challenge_token: str = Field(min_length=16, max_length=128)
    channel: Literal["email", "phone"] = "email"
    code: str = Field(pattern=r"^\d{8}$")


class StaffAccount(BaseModel):
    id: uuid.UUID
    identity_id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str
    mfa_enabled: bool
    created_at: datetime
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_staff(cls, staff, permissions: set[str]) -> "StaffAccount":
        return cls(
            id=staff.id,
            identity_id=staff.user_id,
            email=staff.email,
            full_name=staff.full_name,
            role=staff.role,
            status=staff.status,
            mfa_enabled=staff.mfa_enabled,
            created_at=staff.created_at,
            permissions=sorted(permissions),
        )


class StaffInvitationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    full_name: str = Field(min_length=2, max_length=100)
    role: StaffRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class StaffInvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StaffInvitationCreated(StaffInvitationRead):
    invitation_token: str


class AcceptStaffInvitationRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=14, max_length=128)

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain a letter and a number.")
        return value


class StaffEnrollmentRead(BaseModel):
    enrollment_token: str
    totp_secret: str
    issuer: str
    account_name: str


class ConfirmStaffMfaRequest(BaseModel):
    enrollment_token: str = Field(min_length=32, max_length=128)
    totp_code: str = Field(pattern=r"^\d{6}$")


class DashboardMetrics(BaseModel):
    start: datetime
    end: datetime
    total_orders: int
    successful_orders: int
    pending_orders: int
    failed_orders: int
    sample_orders: int
    active_customers: int
    requested_order_value: Decimal
    revenue: Decimal | None
    net_revenue: Decimal | None
    gross_profit: Decimal | None
    available_inventory_units: int | None
    reserved_inventory_units: int | None
    delivered_inventory_units: int | None
    daily_orders: list[dict]
    orders_by_network: list[dict]
    orders_by_status: list[dict]
    data_availability: dict[str, str]


class AdminOrderRead(BaseModel):
    reference: str
    customer_name: str | None
    customer_phone: str
    recipient_phone: str
    network_id: str
    network: str
    bundle_id: str
    bundle: str
    amount: Decimal
    currency: str
    order_status: str
    payment_status: str
    fulfillment_status: str
    supplier: str | None = None
    supplier_reference: str | None = None
    agent: str | None = None
    created_at: datetime
    updated_at: datetime
    is_sample: bool


class OrderNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class OrderEscalationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class OrderNoteRead(BaseModel):
    id: uuid.UUID
    order_reference: str
    author_email: str
    note: str
    created_at: datetime


class OrderEscalationRead(BaseModel):
    id: uuid.UUID
    created_by_email: str
    reason: str
    status: str
    created_at: datetime


class OrderTimelineEvent(BaseModel):
    event_type: str
    previous_status: str | None
    new_status: str | None
    actor_type: str
    actor_label: str
    reason: str | None
    details: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminOrderDetail(AdminOrderRead):
    timeline: list[OrderTimelineEvent]
    notes: list[OrderNoteRead]
    escalations: list[OrderEscalationRead]
    failure_reason: str | None = None


class AdminCustomerRead(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str | None = None
    phone: str
    phone_verified: bool
    email_verified: bool = False
    account_status: str
    created_at: datetime
    order_count: int


class AdminCustomerDetail(AdminCustomerRead):
    orders: list[AdminOrderRead]
    support_records: list[OrderNoteRead]


class CustomerStatusRequest(BaseModel):
    status: Literal["active", "suspended"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("A reason is required.")
        return normalized


class BundleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    size_gb: Decimal | None = Field(default=None, gt=0, max_digits=8, decimal_places=2)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    category: str | None = Field(default=None, min_length=2, max_length=32)
    validity_days: int | None = Field(default=None, gt=0)
    is_available: bool | None = None
    reason: str = Field(min_length=3, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "category")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("A reason is required.")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_changes(self) -> "BundleUpdateRequest":
        fields = self.model_fields_set - {"reason"}
        if not fields:
            raise ValueError("At least one catalogue field must be provided.")
        if any(
            getattr(self, field) is None
            for field in fields
            if field != "validity_days"
        ):
            raise ValueError("Catalogue fields cannot be cleared with null.")
        return self

    def changed_fields(self) -> set[str]:
        return self.model_fields_set - {"reason"}


class NetworkStatusRequest(BaseModel):
    is_active: bool
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("A reason is required.")
        return normalized


class CatalogueRevisionRead(BaseModel):
    id: uuid.UUID
    bundle_id: str
    actor_email: str
    previous_value: dict
    new_value: dict
    reason: str
    created_at: datetime


class AdminAuditRead(BaseModel):
    id: uuid.UUID
    actor_email: str
    action: str
    resource_type: str
    resource_id: str
    previous_value: dict | None
    new_value: dict | None
    reason: str | None
    request_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
