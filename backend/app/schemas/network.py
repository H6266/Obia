from pydantic import BaseModel, ConfigDict


class NetworkRead(BaseModel):
    id: str
    name: str
    short_name: str

    model_config = ConfigDict(from_attributes=True)
