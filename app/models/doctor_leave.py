
from sqlalchemy import (
    Column,
    Integer,
    Date,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class DoctorLeave(Base):
    __tablename__ = "doctor_leaves"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )

    leave_date = Column(Date, nullable=False, index=True)

    reason = Column(String(255), nullable=True)

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
