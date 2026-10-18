import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require_roles
from app.crud.company import crud_company
from app.models.enums import UserRole
from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
)

router = APIRouter()


@router.get("", response_model=List[CompanyResponse], summary="List all companies")
async def list_companies(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    companies = await crud_company.get_multi(db, skip=skip, limit=limit)
    return companies


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
)
async def create_company(
    comp_in: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    if comp_in.cnpj:
        existing = await crud_company.get_by_cnpj(db, comp_in.cnpj)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this CNPJ already exists",
            )
    return await crud_company.create(db, comp_in)


@router.get("/{company_id}", response_model=CompanyResponse, summary="Get company by ID")
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_active_user),
) -> Any:
    company = await crud_company.get_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company


@router.put("/{company_id}", response_model=CompanyResponse, summary="Update company")
async def update_company(
    company_id: uuid.UUID,
    comp_in: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    company = await crud_company.get_by_id(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return await crud_company.update(db, company, comp_in)


@router.delete(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Delete company",
)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_roles([UserRole.ADMIN])),
) -> Any:
    company = await crud_company.delete(db, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company
