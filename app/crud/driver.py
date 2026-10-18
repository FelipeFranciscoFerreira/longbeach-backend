import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.driver import Driver
from app.schemas.driver import DriverCreate, DriverUpdate, DriverLocationUpdate


class CRUDDriver:
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Driver]:
        stmt = (
            select(Driver)
            .where(Driver.id == id)
            .options(selectinload(Driver.user), selectinload(Driver.company))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Optional[Driver]:
        stmt = (
            select(Driver)
            .where(Driver.user_id == user_id)
            .options(selectinload(Driver.user), selectinload(Driver.company))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        company_id: Optional[uuid.UUID] = None,
        is_available: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Driver]:
        stmt = select(Driver).options(
            selectinload(Driver.user), selectinload(Driver.company)
        )
        if company_id:
            stmt = stmt.where(Driver.company_id == company_id)
        if is_available is not None:
            stmt = stmt.where(Driver.is_available == is_available)
        stmt = stmt.offset(skip).limit(limit).order_by(Driver.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: DriverCreate) -> Driver:
        db_obj = Driver(
            user_id=obj_in.user_id,
            company_id=obj_in.company_id,
            cnh=obj_in.cnh,
            vehicle_model=obj_in.vehicle_model,
            vehicle_plate=obj_in.vehicle_plate,
            vehicle_capacity=obj_in.vehicle_capacity,
            is_available=obj_in.is_available,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def update(
        self, db: AsyncSession, db_obj: Driver, obj_in: DriverUpdate
    ) -> Driver:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def update_location(
        self, db: AsyncSession, driver_id: uuid.UUID, loc_in: DriverLocationUpdate
    ) -> Optional[Driver]:
        driver = await self.get_by_id(db, driver_id)
        if not driver:
            return None
        driver.current_latitude = loc_in.latitude
        driver.current_longitude = loc_in.longitude
        driver.last_location_update = datetime.now(timezone.utc)
        db.add(driver)
        await db.commit()
        await db.refresh(driver)
        return driver

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> Optional[Driver]:
        obj = await self.get_by_id(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


crud_driver = CRUDDriver()
