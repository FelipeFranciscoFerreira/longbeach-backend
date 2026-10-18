import uuid
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.enums import Shift, DayOfWeek
from app.models.trip import AttendanceStatus
from app.schemas.client import ClientResponse


class TripDestinationBase(BaseModel):
    destination_name: str
    address: str
    latitude: float
    longitude: float
    drop_order: int = 1


class TripDestinationCreate(TripDestinationBase):
    pass


class TripDestinationResponse(TripDestinationBase):
    id: uuid.UUID
    trip_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripClientBase(BaseModel):
    client_id: uuid.UUID
    destination_id: Optional[uuid.UUID] = None
    days_of_week: List[DayOfWeek] = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ]
    is_active: bool = True


class TripClientCreate(TripClientBase):
    pass


class TripClientResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    client_id: uuid.UUID
    destination_id: Optional[uuid.UUID] = None
    days_of_week: str
    is_active: bool
    created_at: datetime
    client: Optional[ClientResponse] = None
    destination: Optional[TripDestinationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TripBase(BaseModel):
    name: str
    shift: Shift = Shift.MORNING
    origin_address: Optional[str] = None
    origin_latitude: Optional[float] = None
    origin_longitude: Optional[float] = None
    is_active: bool = True


class TripCreate(TripBase):
    destinations: List[TripDestinationCreate] = []


class TripUpdate(BaseModel):
    name: Optional[str] = None
    shift: Optional[Shift] = None
    origin_address: Optional[str] = None
    origin_latitude: Optional[float] = None
    origin_longitude: Optional[float] = None
    is_active: Optional[bool] = None


class TripResponse(TripBase):
    id: uuid.UUID
    company_id: uuid.UUID
    driver_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    destinations: List[TripDestinationResponse] = []
    trip_clients: List[TripClientResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Daily Attendance Check-in
class DailyAttendanceUpdate(BaseModel):
    status: AttendanceStatus
    notes: Optional[str] = None


class DailyAttendanceResponse(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    client_id: uuid.UUID
    trip_date: date
    status: AttendanceStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientResponse] = None

    model_config = ConfigDict(from_attributes=True)


# Driver registers a new client and links to trip(s)
class ClientTripAssignmentInput(BaseModel):
    trip_id: uuid.UUID
    destination_id: Optional[uuid.UUID] = None
    days_of_week: List[DayOfWeek] = [
        DayOfWeek.MONDAY,
        DayOfWeek.TUESDAY,
        DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY,
        DayOfWeek.FRIDAY,
    ]


class DriverRegisterClientRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    pickup_address: str
    pickup_latitude: float
    pickup_longitude: float
    destination_address: Optional[str] = None
    destination_latitude: Optional[float] = None
    destination_longitude: Optional[float] = None
    notes: Optional[str] = None
    trip_assignments: List[ClientTripAssignmentInput] = []


# Route Calculation Schema
class CalculatedStop(BaseModel):
    stop_order: int
    stop_type: str  # "ORIGIN", "PICKUP", "DESTINATION"
    name: str
    address: str
    latitude: float
    longitude: float
    client_id: Optional[uuid.UUID] = None
    client_phone: Optional[str] = None
    estimated_arrival_minutes: Optional[int] = None


class RouteCalculationResponse(BaseModel):
    trip_id: uuid.UUID
    trip_name: str
    trip_date: date
    provider: str
    total_stops: int
    confirmed_passengers_count: int
    total_distance_km: float
    total_duration_minutes: float
    stops: List[CalculatedStop]
    polyline: Optional[str] = None
    cached: bool = False
