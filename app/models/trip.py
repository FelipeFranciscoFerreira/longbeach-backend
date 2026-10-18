import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, List
import enum
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Shift

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.driver import Driver
    from app.models.client import Client


class AttendanceStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ABSENT = "ABSENT"


class Trip(Base):
    """
    Recurring Trip created by a Driver with multiple final destinations
    (e.g., Morning Route: Faculdade A, Faculdade B, Faculdade C).
    """
    __tablename__ = "trips"

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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    shift: Mapped[Shift] = mapped_column(
        SAEnum(Shift, name="trip_shift_enum", native_enum=False),
        default=Shift.MORNING,
        nullable=False,
    )

    # Origin/Starting point of the van (usually driver's base or first garage point)
    origin_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origin_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

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
    driver: Mapped["Driver"] = relationship("Driver", lazy="selectin")
    company: Mapped["Company"] = relationship("Company", lazy="selectin")
    destinations: Mapped[List["TripDestination"]] = relationship(
        "TripDestination",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripDestination.drop_order",
        lazy="selectin",
    )
    trip_clients: Mapped[List["TripClient"]] = relationship(
        "TripClient",
        back_populates="trip",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    daily_attendances: Mapped[List["TripDailyAttendance"]] = relationship(
        "TripDailyAttendance",
        back_populates="trip",
        cascade="all, delete-orphan",
    )


class TripDestination(Base):
    """
    One of multiple final drop locations in a trip (e.g. Faculdade A, B, C).
    """
    __tablename__ = "trip_destinations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    drop_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    trip: Mapped["Trip"] = relationship("Trip", back_populates="destinations")


class TripClient(Base):
    """
    Associates a client to a recurring trip and defines which days of the week
    they ride (e.g. ["MONDAY", "WEDNESDAY", "FRIDAY"]).
    """
    __tablename__ = "trip_clients"
    __table_args__ = (
        UniqueConstraint("trip_id", "client_id", name="uq_trip_client"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Target destination within the trip (which college this student attends)
    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trip_destinations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Days of the week this client attends (stored as comma-separated or JSON list e.g. "MONDAY,WEDNESDAY,FRIDAY")
    days_of_week: Mapped[str] = mapped_column(
        String(255), default="MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="trip_clients")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
    destination: Mapped["TripDestination | None"] = relationship(
        "TripDestination", lazy="selectin"
    )


class TripDailyAttendance(Base):
    """
    Daily attendance check-in for recurring trips.
    The client decides and communicates whether they are going on a specific date.
    """
    __tablename__ = "trip_daily_attendance"
    __table_args__ = (
        UniqueConstraint("trip_id", "client_id", "trip_date", name="uq_trip_client_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    trip_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus, name="attendance_status_enum", native_enum=False),
        default=AttendanceStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
    trip: Mapped["Trip"] = relationship("Trip", back_populates="daily_attendances")
    client: Mapped["Client"] = relationship("Client", lazy="selectin")
