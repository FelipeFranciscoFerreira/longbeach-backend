import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_roles
from app.crud.client import crud_client
from app.crud.company import crud_company
from app.crud.assignment import crud_assignment
from app.models.enums import UserRole, DayOfWeek, Shift
from app.schemas.client import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
)
from app.schemas.driver import DriverResponse

router = APIRouter()


@router.get("", response_model=List[ClientResponse], summary="List clients")
async def list_clients(
    company_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    return await crud_client.get_multi(
        db, company_id=company_id, is_active=is_active, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create client",
)
async def create_client(
    client_in: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    company = await crud_company.get_by_id(db, client_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    existing = await crud_client.get_by_user_id(db, client_in.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a linked Client profile",
        )
    return await crud_client.create(db, client_in)


@router.get("/{client_id}", response_model=ClientResponse, summary="Get client by ID")
async def get_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    client = await crud_client.get_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


@router.put("/{client_id}", response_model=ClientResponse, summary="Update client")
async def update_client(
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> Any:
    client = await crud_client.get_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    if current_user.role != UserRole.ADMIN and client.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this client",
        )
    return await crud_client.update(db, client, client_in)


@router.get(
    "/{client_id}/drivers",
    response_model=List[DriverResponse],
    summary="Get drivers assigned to this client by day of week & shift",
)
async def get_client_drivers(
    client_id: uuid.UUID,
    day_of_week: Optional[DayOfWeek] = None,
    shift: Optional[Shift] = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    client = await crud_client.get_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    assignments = await crud_assignment.get_multi(
        db,
        client_id=client_id,
        day_of_week=day_of_week,
        shift=shift,
        is_active=True,
    )
    return [a.driver for a in assignments if a.driver is not None]


@router.delete("/{client_id}", response_model=ClientResponse, summary="Delete client")
async def delete_client(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    client = await crud_client.delete(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client
