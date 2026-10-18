import uuid
from datetime import date
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_roles
from app.crud.trip import crud_trip
from app.crud.driver import crud_driver
from app.crud.client import crud_client
from app.models.user import User
from app.models.enums import UserRole
from app.models.trip import AttendanceStatus
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripDestinationCreate,
    TripDestinationResponse,
    TripClientCreate,
    TripClientResponse,
    DailyAttendanceUpdate,
    DailyAttendanceResponse,
    RouteCalculationResponse,
)
from app.services.routing.service import routing_service

router = APIRouter()


@router.get("", response_model=List[TripResponse], summary="List trips")
async def list_trips(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    driver_id = None
    if current_user.role == UserRole.DRIVER:
        driver = await crud_driver.get_by_user_id(db, current_user.id)
        if driver:
            driver_id = driver.id

    return await crud_trip.get_multi(db, driver_id=driver_id, skip=skip, limit=limit)


@router.post(
    "",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trip with final destinations (Driver/Admin)",
)
async def create_trip(
    trip_in: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    driver = await crud_driver.get_by_user_id(db, current_user.id)
    if not driver and current_user.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver profile not found for current user",
        )

    driver_id = driver.id if driver else uuid.uuid4()
    company_id = driver.company_id if driver else uuid.uuid4()

    return await crud_trip.create(
        db, obj_in=trip_in, driver_id=driver_id, company_id=company_id
    )


@router.get("/{trip_id}", response_model=TripResponse, summary="Get trip details")
async def get_trip(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> Any:
    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return trip


@router.put("/{trip_id}", response_model=TripResponse, summary="Update trip")
async def update_trip(
    trip_id: uuid.UUID,
    trip_in: TripUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    if current_user.role == UserRole.DRIVER:
        driver = await crud_driver.get_by_user_id(db, current_user.id)
        if not driver or trip.driver_id != driver.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this trip",
            )
    return await crud_trip.update(db, trip, trip_in)


@router.delete("/{trip_id}", response_model=TripResponse, summary="Delete trip")
async def delete_trip(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return await crud_trip.delete(db, trip_id)


@router.post(
    "/{trip_id}/destinations",
    response_model=TripDestinationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a destination (e.g. college/school) to trip",
)
async def add_destination_to_trip(
    trip_id: uuid.UUID,
    dest_in: TripDestinationCreate,
    db: AsyncSession = Depends(get_db),
    _driver: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    return await crud_trip.add_destination(db, trip_id, dest_in)


@router.post(
    "/{trip_id}/clients",
    response_model=TripClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an existing client to trip with days of week",
)
async def attach_client_to_trip(
    trip_id: uuid.UUID,
    tc_in: TripClientCreate,
    db: AsyncSession = Depends(get_db),
    _driver: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    client = await crud_client.get_by_id(db, tc_in.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return await crud_trip.add_client_to_trip(
        db,
        trip_id=trip_id,
        client_id=tc_in.client_id,
        days_of_week=tc_in.days_of_week,
        destination_id=tc_in.destination_id,
    )


# -------------------------------------------------------------------------
# Daily Attendance (Client Check-in)
# -------------------------------------------------------------------------
@router.post(
    "/{trip_id}/attendance",
    response_model=DailyAttendanceResponse,
    summary="Client confirms or declines attendance for a specific date",
)
async def submit_daily_attendance(
    trip_id: uuid.UUID,
    att_in: DailyAttendanceUpdate,
    trip_date: date = Query(..., description="Date of the trip (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Client notifies if they will ride on a specific day (CONFIRMED or ABSENT).
    Drivers or Admins can also update on behalf of the client if client_id is passed.
    """
    client = await crud_client.get_by_user_id(db, current_user.id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client profile not found for current user",
        )

    trip = await crud_trip.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    attendance = await crud_trip.set_attendance(
        db=db,
        trip_id=trip_id,
        client_id=client.id,
        trip_date=trip_date,
        status=att_in.status,
        notes=att_in.notes,
    )
    return attendance


@router.get(
    "/{trip_id}/attendance",
    response_model=List[DailyAttendanceResponse],
    summary="List client attendances for a trip date",
)
async def list_trip_attendance(
    trip_id: uuid.UUID,
    trip_date: date = Query(..., description="Date of the trip (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> Any:
    return await crud_trip.list_trip_attendances(db, trip_id, trip_date)


# -------------------------------------------------------------------------
# Route Calculation (Confirmed Clients Only)
# -------------------------------------------------------------------------
@router.post(
    "/{trip_id}/calculate-route",
    response_model=RouteCalculationResponse,
    summary="Calculate optimal route for confirmed passengers on a date",
)
async def calculate_route_for_date(
    trip_id: uuid.UUID,
    trip_date: date = Query(default=None, description="Date of the trip (defaults to today)"),
    provider: Optional[str] = Query(None, description="Routing provider: 'mock', 'here', 'google'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DRIVER, UserRole.ADMIN])),
) -> Any:
    """
    Calculates the best route from origin, picking up ONLY confirmed passengers,
    and dropping them off at the final destinations (faculdades).
    """
    target_date = trip_date or date.today()
    driver_id = None
    if current_user.role == UserRole.DRIVER:
        driver = await crud_driver.get_by_user_id(db, current_user.id)
        if driver:
            driver_id = driver.id

    return await routing_service.calculate_trip_route(
        db=db,
        trip_id=trip_id,
        target_date=target_date,
        driver_id=driver_id,
        provider_name=provider,
    )
