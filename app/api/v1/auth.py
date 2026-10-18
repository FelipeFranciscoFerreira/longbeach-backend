import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.api.deps import get_current_active_user
from app.crud.user import crud_user
from app.crud.company import crud_company
from app.crud.driver import crud_driver
from app.crud.client import crud_client
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import (
    LoginRequest,
    Token,
    RegisterDriverRequest,
    RegisterClientRequest,
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.driver import DriverCreate
from app.schemas.client import ClientCreate

router = APIRouter()


async def _generate_token_for_user(user: User, db: AsyncSession) -> Token:
    company_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None

    if user.role == UserRole.DRIVER:
        driver = await crud_driver.get_by_user_id(db, user.id)
        if driver:
            driver_id = driver.id
            company_id = driver.company_id
    elif user.role == UserRole.CLIENT:
        client = await crud_client.get_by_user_id(db, user.id)
        if client:
            client_id = client.id
            company_id = client.company_id

    extra_claims = {
        "email": user.email,
        "company_id": str(company_id) if company_id else None,
        "driver_id": str(driver_id) if driver_id else None,
        "client_id": str(client_id) if client_id else None,
    }

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        extra_claims=extra_claims,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        company_id=company_id,
        driver_id=driver_id,
        client_id=client_id,
    )


@router.post("/login", response_model=Token, summary="Login as Driver or Client (JSON)")
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Authenticate user (either Driver or Client) using email and password.
    Returns JWT access token with role and profile IDs.
    """
    user = await crud_user.authenticate(
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return await _generate_token_for_user(user, db)


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Password Form Login (Swagger compatible)",
)
async def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """OAuth2 compatible token login, accepts username (email) and password."""
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return await _generate_token_for_user(user, db)


@router.post(
    "/register/driver",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Driver",
)
async def register_driver(
    reg_in: RegisterDriverRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new user account with Driver profile linked to a company."""
    # Check if company exists
    company = await crud_company.get_by_id(db, reg_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id '{reg_in.company_id}' not found",
        )

    # Check if email is already taken
    existing_user = await crud_user.get_by_email(db, reg_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # 1. Create base User
    user_in = UserCreate(
        email=reg_in.email,
        password=reg_in.password,
        full_name=reg_in.full_name,
        phone=reg_in.phone,
        role=UserRole.DRIVER,
        is_active=True,
    )
    user = await crud_user.create(db, user_in)

    # 2. Create Driver entity
    driver_in = DriverCreate(
        user_id=user.id,
        company_id=reg_in.company_id,
        cnh=reg_in.cnh,
        vehicle_model=reg_in.vehicle_model,
        vehicle_plate=reg_in.vehicle_plate,
        vehicle_capacity=reg_in.vehicle_capacity,
        is_available=True,
    )
    await crud_driver.create(db, driver_in)

    return await _generate_token_for_user(user, db)


@router.post(
    "/register/client",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Client/Passenger",
)
async def register_client(
    reg_in: RegisterClientRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new user account with Client profile linked to a company."""
    # Check if company exists
    company = await crud_company.get_by_id(db, reg_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id '{reg_in.company_id}' not found",
        )

    # Check if email is already taken
    existing_user = await crud_user.get_by_email(db, reg_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # 1. Create base User
    user_in = UserCreate(
        email=reg_in.email,
        password=reg_in.password,
        full_name=reg_in.full_name,
        phone=reg_in.phone,
        role=UserRole.CLIENT,
        is_active=True,
    )
    user = await crud_user.create(db, user_in)

    # 2. Create Client entity
    client_in = ClientCreate(
        user_id=user.id,
        company_id=reg_in.company_id,
        pickup_address=reg_in.pickup_address,
        pickup_latitude=reg_in.pickup_latitude,
        pickup_longitude=reg_in.pickup_longitude,
        destination_address=reg_in.destination_address,
        destination_latitude=reg_in.destination_latitude,
        destination_longitude=reg_in.destination_longitude,
        notes=reg_in.notes,
        is_active=True,
    )
    await crud_client.create(db, client_in)

    return await _generate_token_for_user(user, db)


@router.get("/me", summary="Get current logged in user and role profile")
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return user data and linked driver/client profile."""
    profile_data: dict[str, Any] = {
        "user": UserResponse.model_validate(current_user),
        "role": current_user.role,
        "driver": None,
        "client": None,
    }

    if current_user.role == UserRole.DRIVER:
        driver = await crud_driver.get_by_user_id(db, current_user.id)
        if driver:
            profile_data["driver"] = {
                "id": driver.id,
                "company_id": driver.company_id,
                "cnh": driver.cnh,
                "vehicle_model": driver.vehicle_model,
                "vehicle_plate": driver.vehicle_plate,
                "vehicle_capacity": driver.vehicle_capacity,
                "is_available": driver.is_available,
                "current_latitude": driver.current_latitude,
                "current_longitude": driver.current_longitude,
            }
    elif current_user.role == UserRole.CLIENT:
        client = await crud_client.get_by_user_id(db, current_user.id)
        if client:
            profile_data["client"] = {
                "id": client.id,
                "company_id": client.company_id,
                "pickup_address": client.pickup_address,
                "pickup_latitude": client.pickup_latitude,
                "pickup_longitude": client.pickup_longitude,
                "destination_address": client.destination_address,
                "destination_latitude": client.destination_latitude,
                "destination_longitude": client.destination_longitude,
                "notes": client.notes,
            }

    return profile_data
