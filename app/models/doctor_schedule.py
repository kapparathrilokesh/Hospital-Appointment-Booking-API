
from sqlalchemy import (
    Column,
    Integer,
    Time,
    Boolean,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "day_of_week",
            name="uq_doctor_schedule_day",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )

    # Monday = 0, Tuesday = 1, ..., Sunday = 6
    day_of_week = Column(Integer, nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    slot_duration_minutes = Column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    doctor = relationship("Doctor")
