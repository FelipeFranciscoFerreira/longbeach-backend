import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.company import Company
    from app.models.assignment import DriverClientAssignment


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    cnh: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vehicle_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True, default=15)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Real-time GPS location tracking fields
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="driver", lazy="selectin")
    company: Mapped["Company"] = relationship("Company", back_populates="drivers")
    assignments: Mapped[List["DriverClientAssignment"]] = relationship(
        "DriverClientAssignment", back_populates="driver", cascade="all, delete-orphan"
    )
