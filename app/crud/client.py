import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate


class CRUDClient:
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Client]:
        stmt = (
            select(Client)
            .where(Client.id == id)
            .options(selectinload(Client.user), selectinload(Client.company))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[Client]:
        stmt = (
            select(Client)
            .where(Client.user_id == user_id)
            .options(selectinload(Client.user), selectinload(Client.company))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        company_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Client]:
        stmt = select(Client).options(
            selectinload(Client.user), selectinload(Client.company)
        )
        if company_id:
            stmt = stmt.where(Client.company_id == company_id)
        if is_active is not None:
            stmt = stmt.where(Client.is_active == is_active)
        stmt = stmt.offset(skip).limit(limit).order_by(Client.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: ClientCreate) -> Client:
        db_obj = Client(
            user_id=obj_in.user_id,
            company_id=obj_in.company_id,
            pickup_address=obj_in.pickup_address,
            pickup_latitude=obj_in.pickup_latitude,
            pickup_longitude=obj_in.pickup_longitude,
            destination_address=obj_in.destination_address,
            destination_latitude=obj_in.destination_latitude,
            destination_longitude=obj_in.destination_longitude,
            notes=obj_in.notes,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def update(
        self, db: AsyncSession, db_obj: Client, obj_in: ClientUpdate
    ) -> Client:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> Optional[Client]:
        obj = await self.get_by_id(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


crud_client = CRUDClient()
