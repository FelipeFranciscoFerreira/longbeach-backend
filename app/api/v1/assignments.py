import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_roles
from app.crud.assignment import crud_assignment
from app.crud.driver import crud_driver
from app.crud.client import crud_client
from app.crud.company import crud_company
from app.models.enums import UserRole, DayOfWeek, Shift
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentResponse,
)

router = APIRouter()


@router.get("", response_model=List[AssignmentResponse], summary="List assignments")
async def list_assignments(
    company_id: Optional[uuid.UUID] = None,
    driver_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    day_of_week: Optional[DayOfWeek] = None,
    shift: Optional[Shift] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    return await crud_assignment.get_multi(
        db,
        company_id=company_id,
        driver_id=driver_id,
        client_id=client_id,
        day_of_week=day_of_week,
        shift=shift,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create driver-client schedule assignment",
)
async def create_assignment(
    assignment_in: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    # Validate company
    company = await crud_company.get_by_id(db, assignment_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    # Validate driver
    driver = await crud_driver.get_by_id(db, assignment_in.driver_id)
    if not driver or driver.company_id != assignment_in.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found in this company",
        )

    # Validate client
    client = await crud_client.get_by_id(db, assignment_in.client_id)
    if not client or client.company_id != assignment_in.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found in this company",
        )

    return await crud_assignment.create(db, assignment_in)


@router.get(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Get assignment by ID",
)
async def get_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    assignment = await crud_assignment.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment


@router.put(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Update assignment",
)
async def update_assignment(
    assignment_id: uuid.UUID,
    assignment_in: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    assignment = await crud_assignment.get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return await crud_assignment.update(db, assignment, assignment_in)


@router.delete(
    "/{assignment_id}",
    response_model=AssignmentResponse,
    summary="Delete assignment",
)
async def delete_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    assignment = await crud_assignment.delete(db, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return assignment
