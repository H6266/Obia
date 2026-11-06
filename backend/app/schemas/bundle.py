from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BundleRead(BaseModel):
    id: str
    network_id: str
    name: str
    size_gb: Decimal
    amount: Decimal
    currency: str
    is_sample: bool
    is_available: bool

    model_config = ConfigDict(from_attributes=True)
