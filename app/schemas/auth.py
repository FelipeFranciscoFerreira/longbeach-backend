import uuid
from pydantic import BaseModel, EmailStr
from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    company_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None


class TokenData(BaseModel):
    user_id: uuid.UUID | None = None
    role: UserRole | None = None


class RegisterDriverRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    company_id: uuid.UUID
    cnh: str
    vehicle_model: str | None = None
    vehicle_plate: str | None = None
    vehicle_capacity: int | None = 15


class RegisterClientRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    company_id: uuid.UUID
    pickup_address: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    destination_address: str | None = None
    destination_latitude: float | None = None
    destination_longitude: float | None = None
    notes: str | None = None
