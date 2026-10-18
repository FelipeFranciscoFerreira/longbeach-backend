import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate


class CRUDCompany:
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Company]:
        stmt = select(Company).where(Company.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_cnpj(self, db: AsyncSession, cnpj: str) -> Optional[Company]:
        stmt = select(Company).where(Company.cnpj == cnpj)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[Company]:
        stmt = (
            select(Company)
            .offset(skip)
            .limit(limit)
            .order_by(Company.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: CompanyCreate) -> Company:
        db_obj = Company(
            name=obj_in.name,
            cnpj=obj_in.cnpj,
            phone=obj_in.phone,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: Company, obj_in: CompanyUpdate
    ) -> Company:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> Optional[Company]:
        obj = await self.get_by_id(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


crud_company = CRUDCompany()
