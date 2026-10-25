import uuid

from pydantic import BaseModel


class HubOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    address: str
    area_name: str
    lat: float
    lng: float
