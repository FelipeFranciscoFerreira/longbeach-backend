import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import DayOfWeek, Shift

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.client import Client
    from app.models.company import Company


class DriverClientAssignment(Base):
    __tablename__ = "driver_client_assignments"
    __table_args__ = (
        UniqueConstraint(
            "driver_id",
            "client_id",
            "day_of_week",
            "shift",
            name="uq_driver_client_day_shift",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    day_of_week: Mapped[DayOfWeek] = mapped_column(
        SAEnum(DayOfWeek, name="day_of_week_enum", native_enum=False),
        default=DayOfWeek.ALL,
        nullable=False,
    )
    shift: Mapped[Shift] = mapped_column(
        SAEnum(Shift, name="shift_enum", native_enum=False),
        default=Shift.ALL,
        nullable=False,
    )

    # Optional order index and estimated pickup time
    pickup_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_pickup_time: Mapped[str | None] = mapped_column(String(10), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    company: Mapped["Company"] = relationship("Company", back_populates="assignments")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="assignments")
    client: Mapped["Client"] = relationship("Client", back_populates="assignments")
