import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_roles
from app.crud.driver import crud_driver
from app.crud.company import crud_company
from app.crud.assignment import crud_assignment
from app.crud.user import crud_user
from app.crud.client import crud_client
from app.crud.trip import crud_trip
from app.models.user import User
from app.models.enums import UserRole, DayOfWeek, Shift
from app.schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverLocationUpdate,
    DriverResponse,
)
from app.schemas.client import ClientResponse, ClientCreate
from app.schemas.user import UserCreate
from app.schemas.trip import DriverRegisterClientRequest

router = APIRouter()


@router.post(
    "/register-client",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Driver registers a new client and assigns them to recurring trips",
)
async def driver_register_client(
    reg_in: DriverRegisterClientRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    """
    Allows a driver to directly register a client and assign them to 1 or more trips
    with specific days of the week.
    """
    driver = await crud_driver.get_by_user_id(db, current_user.id)
    if not driver and current_user.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver profile not found",
        )

    company_id = driver.company_id if driver else uuid.uuid4()

    # Check if email is already registered
    existing_user = await crud_user.get_by_email(db, reg_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
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

    # 2. Create Client Profile
    client_in = ClientCreate(
        user_id=user.id,
        company_id=company_id,
        pickup_address=reg_in.pickup_address,
        pickup_latitude=reg_in.pickup_latitude,
        pickup_longitude=reg_in.pickup_longitude,
        destination_address=reg_in.destination_address,
        destination_latitude=reg_in.destination_latitude,
        destination_longitude=reg_in.destination_longitude,
        notes=reg_in.notes,
        is_active=True,
    )
    client = await crud_client.create(db, client_in)

    # 3. Attach to requested trips
    for assignment_input in reg_in.trip_assignments:
        trip = await crud_trip.get_by_id(db, assignment_input.trip_id)
        if trip:
            await crud_trip.add_client_to_trip(
                db=db,
                trip_id=trip.id,
                client_id=client.id,
                days_of_week=assignment_input.days_of_week,
                destination_id=assignment_input.destination_id,
            )

    return client



@router.get("", response_model=List[DriverResponse], summary="List drivers")
async def list_drivers(
    company_id: Optional[uuid.UUID] = None,
    is_available: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    return await crud_driver.get_multi(
        db, company_id=company_id, is_available=is_available, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create driver",
)
async def create_driver(
    driver_in: DriverCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    company = await crud_company.get_by_id(db, driver_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    existing = await crud_driver.get_by_user_id(db, driver_in.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a linked Driver profile",
        )
    return await crud_driver.create(db, driver_in)


@router.get("/{driver_id}", response_model=DriverResponse, summary="Get driver by ID")
async def get_driver(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    driver = await crud_driver.get_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    return driver


@router.put("/{driver_id}", response_model=DriverResponse, summary="Update driver")
async def update_driver(
    driver_id: uuid.UUID,
    driver_in: DriverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> Any:
    driver = await crud_driver.get_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    if current_user.role != UserRole.ADMIN and driver.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this driver",
        )
    return await crud_driver.update(db, driver, driver_in)


@router.patch(
    "/{driver_id}/location",
    response_model=DriverResponse,
    summary="Update driver real-time GPS coordinates",
)
async def update_driver_location(
    driver_id: uuid.UUID,
    loc_in: DriverLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> Any:
    driver = await crud_driver.get_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    if current_user.role != UserRole.ADMIN and driver.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this driver's location",
        )
    return await crud_driver.update_location(db, driver_id, loc_in)


@router.get(
    "/{driver_id}/clients",
    response_model=List[ClientResponse],
    summary="Get clients assigned to this driver by day of week & shift",
)
async def get_driver_clients(
    driver_id: uuid.UUID,
    day_of_week: Optional[DayOfWeek] = None,
    shift: Optional[Shift] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    driver = await crud_driver.get_by_id(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    assignments = await crud_assignment.get_multi(
        db,
        driver_id=driver_id,
        day_of_week=day_of_week,
        shift=shift,
        is_active=True,
    )
    return [a.client for a in assignments if a.client is not None]


@router.delete("/{driver_id}", response_model=DriverResponse, summary="Delete driver")
async def delete_driver(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    driver = await crud_driver.delete(db, driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )
    return driver
