
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    # Booking reference and queue number.
    # Nullable initially so existing records remain compatible.
    appointment_number = Column(
        String(30), unique=True, nullable=True, index=True
    )
    token_number = Column(Integer, nullable=True)

    patient_id = Column(
        Integer, ForeignKey("patients.id"), nullable=False, index=True
    )
    doctor_id = Column(
        Integer, ForeignKey("doctors.id"), nullable=False, index=True
    )

    appointment_datetime = Column(
        DateTime, nullable=False, index=True
    )
    reason = Column(Text, nullable=True)

    status = Column(
        String(30),
        nullable=False,
        default="scheduled",
        server_default="scheduled",
    )
    notes = Column(Text, nullable=True)

    # Snapshot of the doctor's fee when the appointment is booked.
    consultation_fee = Column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Assignment tracking fields.
    reschedule_count = Column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reminder_sent = Column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    created_at = Column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    patient = relationship("Patient")
    doctor = relationship("Doctor")
