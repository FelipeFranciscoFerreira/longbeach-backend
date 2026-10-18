import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import DayOfWeek, Shift
from app.schemas.driver import DriverResponse
from app.schemas.client import ClientResponse


class AssignmentBase(BaseModel):
    company_id: uuid.UUID
    driver_id: uuid.UUID
    client_id: uuid.UUID
    day_of_week: DayOfWeek = DayOfWeek.ALL
    shift: Shift = Shift.ALL
    pickup_order: int | None = None
    estimated_pickup_time: str | None = None
    is_active: bool = True


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    driver_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    day_of_week: DayOfWeek | None = None
    shift: Shift | None = None
    pickup_order: int | None = None
    estimated_pickup_time: str | None = None
    is_active: bool | None = None


class AssignmentResponse(AssignmentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    driver: DriverResponse | None = None
    client: ClientResponse | None = None

    model_config = ConfigDict(from_attributes=True)
