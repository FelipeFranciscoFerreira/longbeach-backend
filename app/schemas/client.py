import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class ClientBase(BaseModel):
    company_id: uuid.UUID
    pickup_address: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    destination_address: str | None = None
    destination_latitude: float | None = None
    destination_longitude: float | None = None
    notes: str | None = None
    is_active: bool = True


class ClientCreate(ClientBase):
    user_id: uuid.UUID


class ClientUpdate(BaseModel):
    company_id: uuid.UUID | None = None
    pickup_address: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    destination_address: str | None = None
    destination_latitude: float | None = None
    destination_longitude: float | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientResponse(ClientBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
