from pydantic import BaseModel, ConfigDict


class NetworkRead(BaseModel):
    id: str
    name: str
    short_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
