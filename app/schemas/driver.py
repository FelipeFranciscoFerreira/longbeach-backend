import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class DriverBase(BaseModel):
    company_id: uuid.UUID
    cnh: str
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    vehicle_capacity: int | None = 15
    is_available: bool = True


class DriverCreate(DriverBase):
    user_id: uuid.UUID


class DriverUpdate(BaseModel):
    company_id: uuid.UUID | None = None
    cnh: str | None = None
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    vehicle_capacity: int | None = None
    is_available: bool | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None


class DriverLocationUpdate(BaseModel):
    latitude: float
    longitude: float


class DriverResponse(DriverBase):
    id: uuid.UUID
    user_id: uuid.UUID
    current_latitude: float | None = None
    current_longitude: float | None = None
    last_location_update: datetime | None = None
    created_at: datetime
    updated_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
