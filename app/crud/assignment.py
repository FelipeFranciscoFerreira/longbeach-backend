import uuid
from typing import Optional, Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import DriverClientAssignment
from app.models.enums import DayOfWeek, Shift
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate


class CRUDAssignment:
    async def get_by_id(
        self, db: AsyncSession, id: uuid.UUID
    ) -> Optional[DriverClientAssignment]:
        stmt = (
            select(DriverClientAssignment)
            .where(DriverClientAssignment.id == id)
            .options(
                selectinload(DriverClientAssignment.driver),
                selectinload(DriverClientAssignment.client),
                selectinload(DriverClientAssignment.company),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        company_id: Optional[uuid.UUID] = None,
        driver_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        day_of_week: Optional[DayOfWeek] = None,
        shift: Optional[Shift] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[DriverClientAssignment]:
        stmt = select(DriverClientAssignment).options(
            selectinload(DriverClientAssignment.driver),
            selectinload(DriverClientAssignment.client),
            selectinload(DriverClientAssignment.company),
        )

        conditions = []
        if company_id:
            conditions.append(DriverClientAssignment.company_id == company_id)
        if driver_id:
            conditions.append(DriverClientAssignment.driver_id == driver_id)
        if client_id:
            conditions.append(DriverClientAssignment.client_id == client_id)
        if day_of_week and day_of_week != DayOfWeek.ALL:
            conditions.append(
                (DriverClientAssignment.day_of_week == day_of_week)
                | (DriverClientAssignment.day_of_week == DayOfWeek.ALL)
            )
        if shift and shift != Shift.ALL:
            conditions.append(
                (DriverClientAssignment.shift == shift)
                | (DriverClientAssignment.shift == Shift.ALL)
            )
        if is_active is not None:
            conditions.append(DriverClientAssignment.is_active == is_active)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = (
            stmt.order_by(
                DriverClientAssignment.pickup_order.asc().nullslast(),
                DriverClientAssignment.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, obj_in: AssignmentCreate
    ) -> DriverClientAssignment:
        db_obj = DriverClientAssignment(
            company_id=obj_in.company_id,
            driver_id=obj_in.driver_id,
            client_id=obj_in.client_id,
            day_of_week=obj_in.day_of_week,
            shift=obj_in.shift,
            pickup_order=obj_in.pickup_order,
            estimated_pickup_time=obj_in.estimated_pickup_time,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def update(
        self,
        db: AsyncSession,
        db_obj: DriverClientAssignment,
        obj_in: AssignmentUpdate,
    ) -> DriverClientAssignment:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return await self.get_by_id(db, db_obj.id)  # type: ignore

    async def delete(
        self, db: AsyncSession, id: uuid.UUID
    ) -> Optional[DriverClientAssignment]:
        obj = await self.get_by_id(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj


crud_assignment = CRUDAssignment()
